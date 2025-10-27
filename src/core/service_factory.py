"""
서비스 인스턴스 생성을 중앙화하는 Factory 패턴 구현.

이 모듈은 애플리케이션의 모든 서비스 인스턴스를 생성하고 관리하는
중앙화된 팩토리를 제공합니다. 의존성 주입과 서비스 생명주기 관리를
통해 코드의 유지보수성을 향상시킵니다.
"""
from typing import Optional, Dict, Any, Type, TypeVar, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
import importlib
import logging

from src.app.core.config import Config

T = TypeVar('T')

logger = logging.getLogger(__name__)


@dataclass
class ServiceDescriptor:
    """서비스 등록 정보를 담는 데이터 클래스"""
    service_class: Type
    module_path: str
    dependencies: list[str]
    is_optional: bool = False
    feature_flag: Optional[str] = None
    singleton: bool = True


class ServiceRegistry:
    """서비스 등록 및 관리를 위한 레지스트리"""
    
    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}
        self._instances: Dict[str, Any] = {}
        self._feature_flags: Dict[str, bool] = {}
    
    def register_service(
        self, 
        name: str, 
        service_class: Type,
        module_path: str,
        dependencies: list[str] = None,
        is_optional: bool = False,
        feature_flag: Optional[str] = None,
        singleton: bool = True
    ) -> None:
        """서비스를 레지스트리에 등록합니다."""
        self._services[name] = ServiceDescriptor(
            service_class=service_class,
            module_path=module_path,
            dependencies=dependencies or [],
            is_optional=is_optional,
            feature_flag=feature_flag,
            singleton=singleton
        )
        logger.debug(f"Service registered: {name}")
    
    def set_feature_flag(self, flag_name: str, enabled: bool) -> None:
        """Feature flag 상태를 설정합니다."""
        self._feature_flags[flag_name] = enabled
        logger.debug(f"Feature flag set: {flag_name}={enabled}")
    
    def is_feature_enabled(self, flag_name: Optional[str]) -> bool:
        """Feature flag 상태를 확인합니다."""
        if flag_name is None:
            return True
        return self._feature_flags.get(flag_name, False)
    
    def get_service_descriptor(self, name: str) -> Optional[ServiceDescriptor]:
        """서비스 등록 정보를 반환합니다."""
        return self._services.get(name)
    
    def list_services(self) -> Dict[str, ServiceDescriptor]:
        """등록된 모든 서비스 목록을 반환합니다."""
        return self._services.copy()


class ServiceFactory:
    """서비스 인스턴스 생성을 담당하는 팩토리 클래스"""
    
    def __init__(self, config: Config, registry: ServiceRegistry):
        self.config = config
        self.registry = registry
        self._dependency_resolver = DependencyResolver(self)
    
    def create_service(self, service_name: str) -> Optional[Any]:
        """서비스 인스턴스를 생성합니다."""
        descriptor = self.registry.get_service_descriptor(service_name)
        if not descriptor:
            logger.warning(f"Service not found in registry: {service_name}")
            return None
        
        # Feature flag 확인
        if not self.registry.is_feature_enabled(descriptor.feature_flag):
            logger.info(f"Service disabled by feature flag: {service_name}")
            if descriptor.is_optional:
                return None
            raise RuntimeError(f"Required service {service_name} is disabled")
        
        # Singleton 인스턴스 확인
        if descriptor.singleton and service_name in self.registry._instances:
            return self.registry._instances[service_name]
        
        try:
            # 의존성 해결
            dependencies = self._dependency_resolver.resolve_dependencies(descriptor.dependencies)
            
            # 모듈 동적 임포트 (Phase 0.5 이중 경로 지원)
            module = self._load_service_module(service_name, descriptor.module_path)
            service_class = getattr(module, descriptor.service_class.__name__)
            
            # 인스턴스 생성
            if dependencies:
                instance = self._create_service_instance(service_class, service_name, **dependencies)
            else:
                instance = self._create_service_instance(service_class, service_name)
            
            # Singleton 캐싱
            if descriptor.singleton:
                self.registry._instances[service_name] = instance
            
            logger.info(f"Service created successfully: {service_name}")
            return instance
            
        except ImportError as e:
            if descriptor.is_optional:
                logger.warning(f"Optional service import failed: {service_name} - {e}")
                return None
            logger.error(f"Required service import failed: {service_name} - {e}")
            raise RuntimeError(f"Failed to import service {service_name}: {e}")
        
        except Exception as e:
            logger.error(f"Service creation failed: {service_name} - {e}")
            if not descriptor.is_optional:
                raise
            return None
    
    def _load_service_module(self, service_name: str, fallback_module_path: str):
        """Phase 0.5 이중 경로 지원으로 서비스 모듈 로딩"""
        # Phase 1까지 복사된 서비스들의 새 경로 매핑
        domain_map = {
            # Analysis 도메인 (Phase 0.5)
            'vision_service': 'analysis',
            'openai_service': 'analysis',
            # Prompts 도메인 (Phase 0.5)
            'prompt_service': 'prompts',
            'prompt_manager': 'prompts',
            'prompt_renderer': 'prompts',
            'prompt_validator': 'prompts',
            # District 도메인 (Phase 1)
            'district_service': 'district',
            'district_api': 'district',
            'district_cache': 'district',
            'district_loader': 'district',
            'district_validator': 'district',
            'location_service': 'district',
            # Infrastructure 도메인 (Phase 1)
            'search_manager': 'infrastructure',
            'search_providers': 'infrastructure',
            'link_collector_service': 'infrastructure',
            'tunnel_service': 'infrastructure',
            'batch_service': 'infrastructure',
            'file_source_validator': 'infrastructure',
            # Monitoring 도메인 (Phase 1)
            'monitoring_service': 'monitoring',
            'monitoring_admin_integration': 'monitoring',
            'notification_service': 'monitoring',
            'notification_sender': 'monitoring',
            'notification_scheduler': 'monitoring',
            'notification_config': 'monitoring'
        }

        if service_name in domain_map:
            try:
                domain = domain_map[service_name]
                new_module_path = f"src.domains.{domain}.services.{service_name}"
                logger.info(f"Trying new path for {service_name}: {new_module_path}")
                return importlib.import_module(new_module_path)
            except ImportError as e:
                logger.warning(f"New path failed for {service_name}, falling back to legacy: {e}")

        # 기존 경로 fallback
        logger.info(f"Using legacy path for {service_name}: {fallback_module_path}")
        return importlib.import_module(fallback_module_path)

    def _create_service_instance(self, service_class, service_name: str, **dependencies):
        """서비스별 특수한 설정을 처리하여 인스턴스를 생성합니다."""
        if service_name == 'prompt_service':
            # PromptService는 PromptConfig를 필요로 함
            return service_class(config=self.config.prompts, **dependencies)
        elif service_name == 'vision_service':
            # VisionService는 VisionConfig를 필요로 함
            return service_class(config=self.config.vision, **dependencies)
        elif service_name == 'district_service':
            # DistrictService는 DistrictConfig를 필요로 함
            return service_class(config=self.config.district, **dependencies)
        elif service_name == 'location_service':
            # LocationService는 LocationConfig를 필요로 함
            return service_class(config=self.config.location, **dependencies)
        else:
            # 기본적으로 전체 Config 전달
            return service_class(config=self.config, **dependencies)


class DependencyResolver:
    """서비스 간 의존성을 해결하는 클래스"""
    
    def __init__(self, factory: 'ServiceFactory'):
        self.factory = factory
        self._resolving: set[str] = set()
    
    def resolve_dependencies(self, dependency_names: list[str]) -> Dict[str, Any]:
        """의존성 목록을 해결하여 인스턴스 딕셔너리를 반환합니다."""
        dependencies = {}
        
        for dep_name in dependency_names:
            if dep_name in self._resolving:
                raise RuntimeError(f"Circular dependency detected: {dep_name}")
            
            self._resolving.add(dep_name)
            try:
                dep_instance = self.factory.create_service(dep_name)
                if dep_instance is not None:
                    dependencies[dep_name] = dep_instance
            finally:
                self._resolving.discard(dep_name)
        
        return dependencies


def create_default_service_registry(config: Config) -> ServiceRegistry:
    """기본 서비스 레지스트리를 생성합니다."""
    registry = ServiceRegistry()
    
    # Feature flags 설정
    registry.set_feature_flag('vision_enabled', True)  # 기본적으로 비전 기능 활성화
    registry.set_feature_flag('tunnel_enabled', True)   # 터널 기능 활성화
    registry.set_feature_flag('district_enabled', True) # 행정구역 기능 활성화
    registry.set_feature_flag('prompt_enabled', True)   # 프롬프트 관리 기능 활성화
    registry.set_feature_flag('location_enabled', True) # 위치 서비스 기능 활성화
    
    # OpenAI Service 등록
    registry.register_service(
        name='openai_service',
        service_class=type('OpenAIService', (), {}),  # 실제 클래스는 동적 로드
        module_path='src.services.openai_service',
        dependencies=[],
        is_optional=False,
        singleton=True
    )
    
    # Vision Service 등록 (무거운 의존성으로 인해 optional)
    registry.register_service(
        name='vision_service',
        service_class=type('VisionService', (), {}),
        module_path='src.services.vision_service',
        dependencies=[],
        is_optional=True,
        feature_flag='vision_enabled',
        singleton=True
    )
    
    # Tunnel Service 등록 (이 module_path는 동적 로드에 의해 무시됨)
    registry.register_service(
        name='tunnel_service',
        service_class=type('TunnelService', (), {}),
        module_path='src.domains.infrastructure.services.tunnel_service',
        dependencies=[],
        is_optional=True,
        feature_flag='tunnel_enabled',
        singleton=True
    )
    
    # District Service 등록
    registry.register_service(
        name='district_service',
        service_class=type('DistrictService', (), {}),
        module_path='src.services.district_service',
        dependencies=[],
        is_optional=True,
        feature_flag='district_enabled',
        singleton=True
    )
    
    # Prompt Service 등록
    registry.register_service(
        name='prompt_service',
        service_class=type('PromptService', (), {}),
        module_path='src.services.prompt_service',
        dependencies=[],
        is_optional=False,
        feature_flag='prompt_enabled',
        singleton=True
    )

    # Location Service 등록
    registry.register_service(
        name='location_service',
        service_class=type('LocationService', (), {}),
        module_path='src.services.location_service',
        dependencies=[],
        is_optional=True,
        feature_flag='location_enabled',
        singleton=True
    )

    return registry


def get_service_factory(config: Config) -> ServiceFactory:
    """전역 서비스 팩토리 인스턴스를 반환합니다."""
    registry = create_default_service_registry(config)
    return ServiceFactory(config, registry)