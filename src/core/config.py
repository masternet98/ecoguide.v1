"""
애플리케이션의 설정을 정의하는 모듈입니다.

Config 데이터 클래스를 통해 타입 안전하고 확장 가능한 설정을 제공합니다.
Vision 관련 기본값은 src.services.vision_types.VisionConfig를 사용하여 관리합니다.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import os

from src.services.vision_types import VisionConfig


@dataclass
class DistrictConfig:
    """
    행정구역 데이터 처리 관련 설정을 포함하는 데이터 클래스입니다.
    """
    # 파일 경로 설정
    uploads_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "uploads\districts"))
    
    # data.go.kr URL 설정
    base_url: str = "https://www.data.go.kr"
    page_url: str = "https://www.data.go.kr/data/15063424/fileData.do"
    meta_url: str = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?publicDataDetailPk=uddi%3A5176efd5-da6e-42a0-b2cf-8512f74503ea&publicDataPk=15063424&atchFileId=&fileDetailSn=1"
    download_url: str = "https://www.data.go.kr/cmm/cmm/fileDownload.do"
    file_download_endpoint: str = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do"
    api_download_endpoint: str = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?publicDataPk=15063424"
    
    # 파일명 설정
    file_prefix: str = "districts"
    file_extension: str = "json"
    
    # CSV 처리 설정
    expected_columns: List[str] = field(default_factory=lambda: [
        '법정동코드', '시도명', '시군구명', '읍면동명', '리명', '순위', '생성일자', '삭제일자'
    ])
    required_columns: List[str] = field(default_factory=lambda: [
        '법정동코드', '시도명', '시군구명'
    ])
    
    # 홈페이지 관련 필드 추가
    homepage_columns: List[str] = field(default_factory=lambda: [
        '대표홈페이지', '홈페이지_확인일자'
    ])
    
    # 네트워크 설정
    request_timeout: int = 30
    download_timeout: int = 120
    
    # User-Agent 설정
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class SearchProviderConfig:
    """
    검색 Provider 관련 설정을 포함하는 데이터 클래스입니다.
    """
    # Provider 활성화 여부 및 우선순위
    google_cse_enabled: bool = field(default_factory=lambda: bool(os.environ.get('GOOGLE_CSE_API_KEY')))
    google_cse_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CSE_API_KEY'))
    google_cse_search_engine_id: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CSE_SEARCH_ENGINE_ID'))
    google_cse_priority: int = 1  # 최고 우선순위
    
    bing_enabled: bool = field(default_factory=lambda: bool(os.environ.get('BING_SEARCH_API_KEY')))
    bing_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('BING_SEARCH_API_KEY'))
    bing_priority: int = 2  # 2순위
    
    html_parsing_enabled: bool = True  # 항상 활성화 (Fallback용)
    html_parsing_priority: int = 3  # 3순위 (최후 수단)
    
    # Provider별 Rate Limit 설정 (분당 요청 수)
    google_cse_rate_limit: int = 90  # Google CSE는 하루 100회, 분당 최대 90회 정도 안전
    bing_rate_limit: int = 180  # Bing은 더 관대함
    html_parsing_rate_limit: int = 20  # HTML 파싱은 매우 보수적으로
    
    # SearchManager 설정
    max_consecutive_failures: int = 3  # 연속 실패 임계값
    circuit_breaker_duration: int = 300  # Circuit breaker 지속 시간 (초)
    fallback_enabled: bool = True  # Fallback 활성화
    timeout_per_provider: int = 30  # Provider별 타임아웃
    retry_attempts: int = 1  # Provider별 재시도 횟수
    
    # 기타 설정
    combine_results_mode: bool = False  # 여러 Provider 결과 결합 여부
    default_results_count: int = 10  # 기본 검색 결과 수


@dataclass
class Config:
    """
    애플리케이션의 모든 설정을 포함하는 데이터 클래스입니다.
    """
    page_title: str = "카메라 - LLM 이미지 분석"
    page_icon: str = "📷"
    default_model: str = "gpt-4o-mini"
    vision_models: List[str] = field(default_factory=lambda: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"])
    default_prompt: str = (
        "이 이미지에 있는 제품을 대형폐기물로 배출하려고 한다. 이 때 제품의 크기가 가격에 중요한 영향을 미친다."
        "해당 제품이 어떤 품목인지. 사진으로 유추하였을 때 대략적인 크기에 대해 분석해줘."
    )
    default_port: int = 8501
    max_image_size: int = 1024
    jpeg_quality: int = 90

    # Vision-specific configuration (uses VisionConfig from src.services.vision_types)
    vision: VisionConfig = field(default_factory=VisionConfig)
    
    # District-specific configuration
    district: DistrictConfig = field(default_factory=DistrictConfig)
    
    # Search Provider configuration
    search_providers: SearchProviderConfig = field(default_factory=SearchProviderConfig)


def load_config() -> Config:
    """
    애플리케이션 설정을 로드하고 Config 인스턴스를 반환합니다.
    향후 환경 변수나 다른 설정 파일에서 값을 오버라이드할 수 있도록 확장될 수 있습니다.
    """
    return Config()


def create_search_provider_manager(config: Config = None):
    """
    Config 설정을 기반으로 SearchProviderManager를 생성합니다.
    
    Args:
        config: 앱 설정 (None이면 기본 config 사용)
        
    Returns:
        설정된 SearchProviderManager 인스턴스
    """
    if config is None:
        config = load_config()
    
    # 순환 import 방지를 위해 함수 내부에서 import
    from src.services.search_manager import SearchProviderManager, SearchManagerConfig
    from src.services.search_providers import (
        ProviderConfig, GoogleCSEProvider, BingSearchProvider, 
        HTMLParsingProvider
    )
    
    search_config = config.search_providers
    
    # SearchManager 설정
    manager_config = SearchManagerConfig(
        max_consecutive_failures=search_config.max_consecutive_failures,
        circuit_breaker_duration=search_config.circuit_breaker_duration,
        fallback_enabled=search_config.fallback_enabled,
        timeout_per_provider=search_config.timeout_per_provider,
        retry_attempts=search_config.retry_attempts,
        combine_results=search_config.combine_results_mode
    )
    
    manager = SearchProviderManager(manager_config)
    
    # Google CSE Provider 추가
    if search_config.google_cse_enabled and search_config.google_cse_api_key:
        google_config = ProviderConfig(
            name="GoogleCSE",
            enabled=True,
            api_key=search_config.google_cse_api_key,
            rate_limit_per_minute=search_config.google_cse_rate_limit,
            timeout_seconds=search_config.timeout_per_provider,
            priority=search_config.google_cse_priority,
            custom_params={'search_engine_id': search_config.google_cse_search_engine_id}
        )
        manager.add_provider(GoogleCSEProvider(google_config))
    
    # Bing Search Provider 추가
    if search_config.bing_enabled and search_config.bing_api_key:
        bing_config = ProviderConfig(
            name="BingSearch",
            enabled=True,
            api_key=search_config.bing_api_key,
            rate_limit_per_minute=search_config.bing_rate_limit,
            timeout_seconds=search_config.timeout_per_provider,
            priority=search_config.bing_priority
        )
        manager.add_provider(BingSearchProvider(bing_config))
    
    # HTML Parsing Provider 추가 (Fallback용, 항상 추가)
    if search_config.html_parsing_enabled:
        html_config = ProviderConfig(
            name="HTMLParsing",
            enabled=True,
            rate_limit_per_minute=search_config.html_parsing_rate_limit,
            timeout_seconds=search_config.timeout_per_provider,
            priority=search_config.html_parsing_priority
        )
        manager.add_provider(HTMLParsingProvider(html_config))
    
    return manager
