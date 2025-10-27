"""
애플리케이션 초기화 및 설정을 담당하는 팩토리 모듈.

이 모듈은 애플리케이션의 전체 초기화 과정을 관리하고,
의존성 주입, 서비스 등록, 설정 검증 등을 수행합니다.
"""
from typing import Optional
import logging
from dotenv import load_dotenv

from src.app.core.config import Config, load_config
from src.app.core.config_validator import ensure_valid_config
from src.app.core.service_factory import ServiceFactory, create_default_service_registry
from src.app.core.feature_registry import FeatureRegistry, create_default_feature_registry
from src.app.core.error_handler import get_error_handler, setup_streamlit_context_provider

logger = logging.getLogger(__name__)


class ApplicationContext:
    """애플리케이션 전체 컨텍스트를 관리하는 클래스"""
    
    def __init__(self, config: Config, service_factory: ServiceFactory, feature_registry: FeatureRegistry):
        self.config = config
        self.service_factory = service_factory
        self.feature_registry = feature_registry
        self._initialized = False
    
    def get_service(self, service_name: str):
        """서비스 인스턴스를 가져옵니다."""
        return self.service_factory.create_service(service_name)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """기능이 활성화되어 있는지 확인합니다."""
        return self.feature_registry.is_feature_enabled(feature_name)
    
    def is_initialized(self) -> bool:
        """애플리케이션이 초기화되었는지 확인합니다."""
        return self._initialized
    
    def mark_initialized(self):
        """애플리케이션 초기화 완료를 표시합니다."""
        self._initialized = True


class ApplicationFactory:
    """애플리케이션을 생성하고 초기화하는 팩토리 클래스"""
    
    @staticmethod
    def create_application(config_override: Optional[Config] = None) -> ApplicationContext:
        """
        애플리케이션 컨텍스트를 생성하고 초기화합니다.
        
        Args:
            config_override: 설정 오버라이드 (테스트용)
            
        Returns:
            ApplicationContext: 초기화된 애플리케이션 컨텍스트
        """
        logger.info("Creating application context...")
        
        # Load environment variables from .env (if present), without overriding existing env
        try:
            load_dotenv(override=False)
            logger.info(".env loaded (if present)")
        except Exception as e:
            logger.warning(f"Failed to load .env: {e}")
        
        try:
            # 1. 설정 로드 및 검증
            config = config_override or load_config()
            config = ensure_valid_config(config)
            logger.info("Configuration loaded and validated")
            
            # 2. 오류 처리기 설정
            setup_streamlit_context_provider()
            logger.info("Error handler configured")
            
            # 3. 기능 레지스트리 생성
            feature_registry = create_default_feature_registry()
            logger.info(f"Feature registry created with {len(feature_registry.list_features())} features")
            
            # 4. 서비스 팩토리 생성
            service_registry = create_default_service_registry(config)
            service_factory = ServiceFactory(config, service_registry)
            logger.info("Service factory created")
            
            # 5. 기능별 서비스 등록 및 활성화
            ApplicationFactory._setup_feature_services(feature_registry, service_registry)

            # 6. 애플리케이션 컨텍스트 생성
            app_context = ApplicationContext(config, service_factory, feature_registry)
            app_context.mark_initialized()

            # 7. 도메인 특화 초기화 (프롬프트 등록 등)
            ApplicationFactory._initialize_domain_services(app_context)

            logger.info("Application context created successfully")
            return app_context
            
        except Exception as e:
            logger.error(f"Failed to create application: {e}")
            # 오류 처리기를 통해 사용자 친화적 오류 표시
            get_error_handler().handle_error(e)
            raise
    
    @staticmethod
    def _setup_feature_services(feature_registry: FeatureRegistry, service_registry) -> None:
        """기능과 서비스를 연결하고 설정합니다."""

        # OpenAI Vision 기능과 서비스 연결
        if feature_registry.is_feature_available("openai_vision"):
            feature_registry.enable_feature("openai_vision")
            service_registry.set_feature_flag('openai_enabled', True)

        # Vision 분석 기능 확인 (무거운 의존성)
        if feature_registry.is_feature_available("vision_analysis"):
            # 자동 활성화하지 않음 - 사용자가 필요할 때 활성화
            logger.info("Vision analysis feature available but not auto-enabled")

        # 관리 기능들 활성화
        management_features = ["tunnel_management", "district_management", "link_collector"]
        for feature_name in management_features:
            if feature_registry.is_feature_available(feature_name):
                feature_registry.enable_feature(feature_name)
                logger.info(f"Management feature enabled: {feature_name}")

    @staticmethod
    def _initialize_domain_services(app_context: 'ApplicationContext') -> None:
        """도메인별 서비스 초기화 및 프롬프트 등록"""
        # 세부내역 프롬프트는 로컬 파일(data/prompts/templates/)에서 직접 로드되므로
        # 초기화 로직 비활성화 (로컬 파일의 프롬프트를 덮어씌우는 문제 방지)
        #
        # 이전 로직 (비활성화됨):
        # try:
        #     from src.domains.infrastructure.services.detail_content_initialization import (
        #         initialize_detail_content_service
        #     )
        #     prompt_ids = initialize_detail_content_service(app_context)
        #     if prompt_ids:
        #         logger.info(f"Detail content prompts registered: {prompt_ids}")
        #     else:
        #         logger.info("Detail content prompts registration skipped or not available")
        # except ImportError:
        #     logger.debug("Detail content initialization not available")
        # except Exception as e:
        #     logger.warning(f"Domain service initialization failed: {e}")

        logger.info("Domain service initialization skipped - prompts loaded from local files")


# 전역 애플리케이션 컨텍스트
_app_context: Optional[ApplicationContext] = None


def get_application() -> ApplicationContext:
    """전역 애플리케이션 컨텍스트를 반환합니다."""
    global _app_context
    if _app_context is None:
        _app_context = ApplicationFactory.create_application()
    return _app_context


def initialize_application(config_override: Optional[Config] = None) -> ApplicationContext:
    """애플리케이션을 초기화합니다."""
    global _app_context
    _app_context = ApplicationFactory.create_application(config_override)
    return _app_context


def reset_application() -> None:
    """애플리케이션 컨텍스트를 리셋합니다 (테스트용)."""
    global _app_context
    _app_context = None


def create_minimal_application(config: Config) -> ApplicationContext:
    """최소한의 애플리케이션 컨텍스트를 생성합니다 (테스트용)."""
    from src.core.service_factory import ServiceRegistry
    
    # 빈 레지스트리들 생성
    service_registry = ServiceRegistry()
    feature_registry = FeatureRegistry()
    
    service_factory = ServiceFactory(config, service_registry)
    
    app_context = ApplicationContext(config, service_factory, feature_registry)
    app_context.mark_initialized()
    
    return app_context
