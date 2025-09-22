"""
검색 Provider 추상화 모듈입니다.
다양한 검색 API/방식을 통일된 인터페이스로 제공하며, Fallback 메커니즘을 지원합니다.
"""
import re
import time
import requests
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import random

# 로깅 시스템 import
from src.core.logger import (
    logger, log_function, log_step, log_info, log_warning, log_error,
    LogLevel, LogCategory
)


@dataclass
class SearchResult:
    """통일된 검색 결과 데이터 클래스"""
    title: str
    url: str
    snippet: str
    search_query: str
    provider_name: str
    raw_data: Optional[Dict[str, Any]] = None  # Provider별 원본 데이터


@dataclass
class ProviderConfig:
    """Provider별 설정을 담는 데이터 클래스"""
    name: str
    enabled: bool
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    max_retries: int = 3
    priority: int = 1  # 낮을수록 우선순위 높음
    custom_params: Optional[Dict[str, Any]] = None


class SearchProviderInterface(ABC):
    """검색 Provider의 추상 인터페이스"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self._last_request_time = 0
        self._request_count = 0
        self._request_window_start = 0
        
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """
        검색을 수행하고 결과를 반환합니다.
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            
        Returns:
            SearchResult 리스트
            
        Raises:
            SearchProviderError: 검색 실패 시
        """
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Provider가 사용 가능한지 확인합니다."""
        pass
        
    def _check_rate_limit(self) -> bool:
        """Rate limit 체크"""
        current_time = time.time()
        
        # 1분 윈도우 초기화
        if current_time - self._request_window_start > 60:
            self._request_count = 0
            self._request_window_start = current_time
        
        # Rate limit 체크
        if self._request_count >= self.config.rate_limit_per_minute:
            return False
            
        # 요청 간 최소 간격 체크 (DDoS 방지)
        time_since_last = current_time - self._last_request_time
        min_interval = 60 / self.config.rate_limit_per_minute
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            log_info(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "rate_limit_wait", f"Rate limit 대기: {sleep_time:.2f}초"
            )
            time.sleep(sleep_time)
        
        self._request_count += 1
        self._last_request_time = time.time()
        return True
        
    def _log_search_attempt(self, query: str, num_results: int):
        """검색 시도 로깅"""
        log_info(
            LogCategory.WEB_SCRAPING, "search_providers", self.name,
            "search_attempt", f"검색 시도: '{query}' (결과 {num_results}개 요청)"
        )


class SearchProviderError(Exception):
    """검색 Provider 에러"""
    def __init__(self, message: str, provider_name: str, original_error: Exception = None):
        super().__init__(message)
        self.provider_name = provider_name
        self.original_error = original_error


class GoogleCSEProvider(SearchProviderInterface):
    """Google Custom Search Engine API Provider"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.search_engine_id = config.custom_params.get('search_engine_id') if config.custom_params else None
        
    def is_available(self) -> bool:
        """CSE API 사용 가능 여부 확인"""
        return (
            self.config.enabled and 
            self.config.api_key is not None and 
            self.search_engine_id is not None
        )
    
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Google CSE API로 검색 수행"""
        if not self.is_available():
            raise SearchProviderError(
                "Google CSE가 사용 불가능합니다. API 키와 Search Engine ID를 확인하세요.",
                self.name
            )
            
        if not self._check_rate_limit():
            raise SearchProviderError(
                f"Rate limit 초과: {self.config.rate_limit_per_minute}/분",
                self.name
            )
            
        self._log_search_attempt(query, num_results)
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.config.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': min(num_results, 10),  # CSE는 한 번에 최대 10개
            'hl': 'ko',
            'gl': 'kr'
        }
        
        try:
            response = requests.get(
                url, 
                params=params, 
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                result = SearchResult(
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    search_query=query,
                    provider_name=self.name,
                    raw_data=item
                )
                results.append(result)
            
            log_info(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "search_success", f"검색 성공: {len(results)}개 결과 반환"
            )
            
            return results
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Google CSE API 요청 실패: {str(e)}"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "api_request_failed", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)
            
        except json.JSONDecodeError as e:
            error_msg = "Google CSE API 응답 파싱 실패"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "json_parse_failed", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)
            
        except Exception as e:
            error_msg = f"Google CSE 검색 중 예상치 못한 오류: {str(e)}"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "unexpected_error", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)


class BingSearchProvider(SearchProviderInterface):
    """Bing Web Search API Provider"""
    
    def is_available(self) -> bool:
        """Bing Search API 사용 가능 여부 확인"""
        return self.config.enabled and self.config.api_key is not None
    
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Bing Web Search API로 검색 수행"""
        if not self.is_available():
            raise SearchProviderError(
                "Bing Search API가 사용 불가능합니다. API 키를 확인하세요.",
                self.name
            )
            
        if not self._check_rate_limit():
            raise SearchProviderError(
                f"Rate limit 초과: {self.config.rate_limit_per_minute}/분",
                self.name
            )
            
        self._log_search_attempt(query, num_results)
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            'Ocp-Apim-Subscription-Key': self.config.api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        params = {
            'q': query,
            'count': min(num_results, 50),  # Bing은 최대 50개
            'mkt': 'ko-KR',
            'safesearch': 'Off'
        }
        
        try:
            response = requests.get(
                url, 
                headers=headers,
                params=params, 
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get('webPages', {}).get('value', []):
                result = SearchResult(
                    title=item.get('name', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    search_query=query,
                    provider_name=self.name,
                    raw_data=item
                )
                results.append(result)
            
            log_info(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "search_success", f"검색 성공: {len(results)}개 결과 반환"
            )
            
            return results
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Bing Search API 요청 실패: {str(e)}"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "api_request_failed", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)
            
        except json.JSONDecodeError as e:
            error_msg = "Bing Search API 응답 파싱 실패"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "json_parse_failed", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)
            
        except Exception as e:
            error_msg = f"Bing Search 검색 중 예상치 못한 오류: {str(e)}"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "unexpected_error", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)


class HTMLParsingProvider(SearchProviderInterface):
    """HTML 파싱 기반 검색 Provider (기존 방식 개선)"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15'
        ]
    
    def is_available(self) -> bool:
        """HTML 파싱 Provider는 항상 사용 가능 (Fallback용)"""
        return self.config.enabled
    
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """HTML 파싱으로 Google 검색 수행 (개선된 버전)"""
        if not self.is_available():
            raise SearchProviderError("HTML Parsing Provider가 비활성화되었습니다.", self.name)
            
        if not self._check_rate_limit():
            raise SearchProviderError(
                f"Rate limit 초과: {self.config.rate_limit_per_minute}/분",
                self.name
            )
            
        self._log_search_attempt(query, num_results)
        
        # User-Agent 랜덤 선택
        user_agent = random.choice(self.user_agents)
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Google 검색 URL 구성
        search_url = 'https://www.google.com/search'
        params = {
            'q': query,
            'num': min(num_results, 20),  # Google 제한
            'hl': 'ko',
            'gl': 'kr',
            'start': 0
        }
        
        try:
            session = requests.Session()
            session.headers.update(headers)
            
            # 요청 전 랜덤 지연
            delay = random.uniform(1, 3)
            time.sleep(delay)
            
            response = session.get(
                search_url, 
                params=params, 
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            
            # 차단 여부 확인
            if self._is_blocked_response(response):
                raise SearchProviderError(
                    "Google에서 요청을 차단했습니다. CAPTCHA 또는 비정상 트래픽으로 감지됨",
                    self.name
                )
            
            # BeautifulSoup으로 검색 결과 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_search_results(soup, query)
            
            log_info(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "search_success", f"HTML 파싱 성공: {len(results)}개 결과 반환"
            )
            
            return results[:num_results]
            
        except requests.exceptions.RequestException as e:
            error_msg = f"HTML 파싱 요청 실패: {str(e)}"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "http_request_failed", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)
            
        except Exception as e:
            error_msg = f"HTML 파싱 검색 중 예상치 못한 오류: {str(e)}"
            log_error(
                LogCategory.WEB_SCRAPING, "search_providers", self.name,
                "unexpected_error", error_msg, error=e
            )
            raise SearchProviderError(error_msg, self.name, e)
    
    def _is_blocked_response(self, response: requests.Response) -> bool:
        """Google 차단 응답인지 확인"""
        content_lower = response.text.lower()
        
        # 차단 관련 키워드 확인
        blocked_keywords = [
            'our systems have detected unusual traffic',
            'unusual traffic from your computer network',
            'captcha',
            'verify you are a human',
            'robot',
            '비정상적인 트래픽',
            '자동화된 쿼리'
        ]
        
        return any(keyword in content_lower for keyword in blocked_keywords)
    
    def _parse_search_results(self, soup: BeautifulSoup, query: str) -> List[SearchResult]:
        """BeautifulSoup으로 검색 결과 파싱 (개선된 버전)"""
        results = []
        
        # Google 검색 결과 선택자들 (여러 패턴 시도)
        result_selectors = [
            'div[data-ved]',  # 가장 일반적인 패턴
            '.g',             # 클래식 패턴
            '.tF2Cxc',        # 새로운 패턴
            'div.yuRUbf',     # 또 다른 패턴
        ]
        
        search_results = []
        for selector in result_selectors:
            search_results = soup.select(selector)
            if search_results:
                break
        
        for result_div in search_results:
            try:
                # 제목과 URL 추출
                title_elem = result_div.select_one('h3, .DKV0Md')
                link_elem = result_div.select_one('a[href]')
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = link_elem.get('href', '')
                
                # Google 리다이렉트 URL 정리
                if url.startswith('/url?q='):
                    url = url.split('&')[0].replace('/url?q=', '')
                elif url.startswith('/search?'):
                    continue  # 관련 검색어는 제외
                
                # 스니펫 추출
                snippet = ""
                snippet_selectors = [
                    '.VwiC3b',
                    '.s3v9rd', 
                    '.st',
                    '.aCOpRe'
                ]
                
                for selector in snippet_selectors:
                    snippet_elem = result_div.select_one(selector)
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                        break
                
                # 유효한 URL 확인
                if not url or not url.startswith(('http://', 'https://')):
                    continue
                
                if title and url:
                    result = SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        search_query=query,
                        provider_name=self.name
                    )
                    results.append(result)
                
            except Exception as e:
                log_warning(
                    LogCategory.WEB_SCRAPING, "search_providers", self.name,
                    "result_parse_error", f"검색 결과 파싱 중 오류: {str(e)}"
                )
                continue
        
        return results


class MockSearchProvider(SearchProviderInterface):
    """테스트용 Mock Provider"""
    
    def __init__(self, config: ProviderConfig, mock_results: List[SearchResult] = None):
        super().__init__(config)
        self.mock_results = mock_results or []
    
    def is_available(self) -> bool:
        return self.config.enabled
    
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Mock 결과 반환"""
        if not self.is_available():
            raise SearchProviderError("Mock Provider가 비활성화되었습니다.", self.name)
        
        self._log_search_attempt(query, num_results)
        
        # Mock 결과에 쿼리 정보 업데이트
        results = []
        for i, result in enumerate(self.mock_results[:num_results]):
            mock_result = SearchResult(
                title=result.title,
                url=result.url,
                snippet=result.snippet,
                search_query=query,
                provider_name=self.name,
                raw_data={'mock': True, 'index': i}
            )
            results.append(mock_result)
        
        return results