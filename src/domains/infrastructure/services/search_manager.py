"""
검색 Provider 관리 및 Fallback 메커니즘을 제공하는 모듈입니다.
여러 검색 Provider를 우선순위에 따라 관리하고, 실패 시 자동으로 다음 Provider로 전환합니다.
"""
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# 로깅 시스템 import
from src.app.core.logger import (
    logger, log_function, log_step, log_info, log_warning, log_error,
    LogLevel, LogCategory
)

from .search_providers import (
    SearchProviderInterface, SearchResult, SearchProviderError,
    GoogleCSEProvider, BingSearchProvider, HTMLParsingProvider, MockSearchProvider
)


@dataclass
class ProviderStatus:
    """Provider 상태 정보"""
    name: str
    is_healthy: bool = True
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    average_response_time: float = 0.0
    circuit_breaker_until: Optional[float] = None  # Circuit breaker 해제 시간


@dataclass 
class SearchManagerConfig:
    """SearchManager 설정"""
    max_consecutive_failures: int = 3  # 연속 실패 임계값
    circuit_breaker_duration: int = 300  # Circuit breaker 지속 시간 (초)
    fallback_enabled: bool = True  # Fallback 활성화
    combine_results: bool = False  # 여러 Provider 결과 결합 여부
    timeout_per_provider: int = 30  # Provider별 타임아웃
    retry_attempts: int = 1  # Provider별 재시도 횟수


class SearchProviderManager:
    """
    검색 Provider들을 관리하고 Fallback 메커니즘을 제공하는 클래스
    """
    
    def __init__(self, config: SearchManagerConfig = None):
        self.config = config or SearchManagerConfig()
        self.providers: List[SearchProviderInterface] = []
        self.provider_status: Dict[str, ProviderStatus] = {}
        
    def add_provider(self, provider: SearchProviderInterface) -> None:
        """Provider 추가"""
        self.providers.append(provider)
        self.provider_status[provider.name] = ProviderStatus(name=provider.name)
        
        # 우선순위에 따라 정렬
        self.providers.sort(key=lambda p: p.config.priority)
        
        log_info(
            LogCategory.WEB_SCRAPING, "search_manager", "add_provider",
            "provider_added", f"Provider 추가: {provider.name} (우선순위: {provider.config.priority})"
        )
    
    def get_available_providers(self) -> List[SearchProviderInterface]:
        """사용 가능한 Provider 목록 반환 (Circuit breaker 고려)"""
        available = []
        current_time = time.time()
        
        for provider in self.providers:
            status = self.provider_status[provider.name]
            
            # Circuit breaker 체크
            if status.circuit_breaker_until and current_time < status.circuit_breaker_until:
                continue
                
            # Provider 사용 가능 여부 체크
            if provider.is_available():
                available.append(provider)
        
        return available
    
    def _activate_circuit_breaker(self, provider_name: str) -> None:
        """Circuit breaker 활성화"""
        status = self.provider_status[provider_name]
        status.circuit_breaker_until = time.time() + self.config.circuit_breaker_duration
        status.is_healthy = False
        
        log_warning(
            LogCategory.WEB_SCRAPING, "search_manager", "_activate_circuit_breaker",
            "circuit_breaker_activated", 
            f"Circuit breaker 활성화: {provider_name} ({self.config.circuit_breaker_duration}초간)"
        )
    
    def _record_success(self, provider_name: str, response_time: float) -> None:
        """성공 기록"""
        status = self.provider_status[provider_name]
        status.last_success_time = time.time()
        status.consecutive_failures = 0
        status.total_requests += 1
        status.successful_requests += 1
        status.is_healthy = True
        status.circuit_breaker_until = None
        
        # 평균 응답 시간 업데이트 (지수 이동 평균)
        if status.average_response_time == 0:
            status.average_response_time = response_time
        else:
            alpha = 0.3  # 가중치
            status.average_response_time = (
                alpha * response_time + (1 - alpha) * status.average_response_time
            )
    
    def _record_failure(self, provider_name: str, error: Exception) -> None:
        """실패 기록"""
        status = self.provider_status[provider_name]
        status.last_failure_time = time.time()
        status.consecutive_failures += 1
        status.total_requests += 1
        
        log_warning(
            LogCategory.WEB_SCRAPING, "search_manager", "_record_failure",
            "provider_failure", 
            f"Provider 실패: {provider_name} (연속 실패: {status.consecutive_failures}회) - {str(error)}"
        )
        
        # Circuit breaker 활성화 여부 결정
        if status.consecutive_failures >= self.config.max_consecutive_failures:
            self._activate_circuit_breaker(provider_name)
    
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """
        검색 수행 (Fallback 메커니즘 포함)
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
            
        Raises:
            SearchProviderError: 모든 Provider가 실패했을 때
        """
        available_providers = self.get_available_providers()
        
        if not available_providers:
            error_msg = "사용 가능한 검색 Provider가 없습니다."
            log_error(
                LogCategory.WEB_SCRAPING, "search_manager", "search",
                "no_available_providers", error_msg
            )
            raise SearchProviderError(error_msg, "SearchManager")
        
        last_error = None
        all_results = []
        
        log_info(
            LogCategory.WEB_SCRAPING, "search_manager", "search",
            "search_start", 
            f"검색 시작: '{query}' - 사용 가능한 Provider: {[p.name for p in available_providers]}"
        )
        
        for provider in available_providers:
            try:
                start_time = time.time()
                
                # Provider별 재시도 메커니즘
                results = None
                for attempt in range(self.config.retry_attempts + 1):
                    try:
                        log_info(
                            LogCategory.WEB_SCRAPING, "search_manager", "search",
                            f"provider_attempt", 
                            f"{provider.name} 시도 {attempt + 1}/{self.config.retry_attempts + 1}"
                        )
                        
                        results = provider.search(query, num_results)
                        break  # 성공하면 재시도 루프 종료
                        
                    except SearchProviderError as e:
                        if attempt == self.config.retry_attempts:  # 마지막 시도
                            raise e
                        
                        # 재시도 대기
                        wait_time = 2 ** attempt  # 지수 백오프
                        log_warning(
                            LogCategory.WEB_SCRAPING, "search_manager", "search",
                            "retry_wait", 
                            f"{provider.name} 재시도 대기: {wait_time}초"
                        )
                        time.sleep(wait_time)
                
                if results:
                    response_time = time.time() - start_time
                    self._record_success(provider.name, response_time)
                    
                    log_info(
                        LogCategory.WEB_SCRAPING, "search_manager", "search",
                        "provider_success", 
                        f"{provider.name} 성공: {len(results)}개 결과 (응답시간: {response_time:.2f}초)"
                    )
                    
                    if self.config.combine_results:
                        all_results.extend(results)
                        # 결과 합치기 모드라면 계속
                        continue
                    else:
                        # 첫 번째 성공한 Provider 결과 반환
                        return results
                
            except SearchProviderError as e:
                self._record_failure(provider.name, e)
                last_error = e
                
                if not self.config.fallback_enabled:
                    # Fallback 비활성화면 즉시 예외 발생
                    raise e
                
                log_warning(
                    LogCategory.WEB_SCRAPING, "search_manager", "search",
                    "provider_failed_fallback", 
                    f"{provider.name} 실패, 다음 Provider로 Fallback: {str(e)}"
                )
                continue
                
            except Exception as e:
                # 예상치 못한 오류
                error_msg = f"{provider.name}에서 예상치 못한 오류: {str(e)}"
                provider_error = SearchProviderError(error_msg, provider.name, e)
                self._record_failure(provider.name, provider_error)
                last_error = provider_error
                
                log_error(
                    LogCategory.WEB_SCRAPING, "search_manager", "search",
                    "unexpected_error", error_msg, error=e
                )
                continue
        
        # 결과 합치기 모드에서 결과가 있으면 반환
        if self.config.combine_results and all_results:
            log_info(
                LogCategory.WEB_SCRAPING, "search_manager", "search",
                "combined_results", f"결합된 결과: {len(all_results)}개"
            )
            return all_results[:num_results]
        
        # 모든 Provider 실패
        error_msg = f"모든 검색 Provider가 실패했습니다. 마지막 오류: {str(last_error) if last_error else 'Unknown'}"
        log_error(
            LogCategory.WEB_SCRAPING, "search_manager", "search",
            "all_providers_failed", error_msg
        )
        
        if last_error:
            raise last_error
        else:
            raise SearchProviderError(error_msg, "SearchManager")
    
    def get_provider_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Provider별 통계 정보 반환"""
        stats = {}
        current_time = time.time()
        
        for name, status in self.provider_status.items():
            success_rate = 0
            if status.total_requests > 0:
                success_rate = (status.successful_requests / status.total_requests) * 100
            
            circuit_breaker_remaining = 0
            if status.circuit_breaker_until and current_time < status.circuit_breaker_until:
                circuit_breaker_remaining = int(status.circuit_breaker_until - current_time)
            
            stats[name] = {
                'is_healthy': status.is_healthy,
                'total_requests': status.total_requests,
                'successful_requests': status.successful_requests,
                'success_rate': round(success_rate, 2),
                'consecutive_failures': status.consecutive_failures,
                'average_response_time': round(status.average_response_time, 2),
                'circuit_breaker_active': circuit_breaker_remaining > 0,
                'circuit_breaker_remaining_seconds': circuit_breaker_remaining,
                'last_success_time': status.last_success_time,
                'last_failure_time': status.last_failure_time
            }
        
        return stats
    
    def reset_provider_status(self, provider_name: str = None) -> None:
        """Provider 상태 초기화"""
        if provider_name:
            if provider_name in self.provider_status:
                self.provider_status[provider_name] = ProviderStatus(name=provider_name)
                log_info(
                    LogCategory.WEB_SCRAPING, "search_manager", "reset_provider_status",
                    "provider_reset", f"Provider 상태 초기화: {provider_name}"
                )
        else:
            for name in self.provider_status:
                self.provider_status[name] = ProviderStatus(name=name)
            log_info(
                LogCategory.WEB_SCRAPING, "search_manager", "reset_provider_status",
                "all_providers_reset", "모든 Provider 상태 초기화"
            )


def create_default_search_manager() -> SearchProviderManager:
    """기본 설정으로 SearchManager 생성"""
    config = SearchManagerConfig(
        max_consecutive_failures=3,
        circuit_breaker_duration=300,  # 5분
        fallback_enabled=True,
        timeout_per_provider=30
    )
    
    manager = SearchProviderManager(config)
    return manager