"""
서비스 클래스들의 공통 인터페이스를 정의하는 추상 기반 클래스.

모든 서비스는 이 기반 클래스를 상속하여 일관된 인터페이스와
공통 기능을 제공받습니다.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass
import logging
from enum import Enum

from src.app.config import Config


class ServiceStatus(Enum):
    """서비스 상태를 나타내는 열거형"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing" 
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ServiceInfo:
    """서비스 정보를 담는 데이터 클래스"""
    name: str
    version: str
    description: str
    dependencies: list[str]
    optional_dependencies: list[str]
    status: ServiceStatus
    error_message: Optional[str] = None


class HealthCheckResult:
    """서비스 헬스체크 결과"""
    
    def __init__(self, is_healthy: bool, message: str = "", details: Dict[str, Any] = None):
        self.is_healthy = is_healthy
        self.message = message
        self.details = details or {}
        self.timestamp = None  # 실제 구현에서는 datetime.utcnow() 사용
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_healthy': self.is_healthy,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }


class BaseService(ABC):
    """모든 서비스의 기반이 되는 추상 클래스"""
    
    def __init__(self, config: Config, **kwargs):
        self.config = config
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._status = ServiceStatus.UNINITIALIZED
        self._error_message: Optional[str] = None
        self._dependencies = kwargs
        
        # 서비스 초기화 시도
        try:
            self._status = ServiceStatus.INITIALIZING
            self._initialize()
            self._status = ServiceStatus.READY
            self._logger.info(f"Service {self.get_service_name()} initialized successfully")
        except Exception as e:
            self._status = ServiceStatus.ERROR
            self._error_message = str(e)
            self._logger.error(f"Service {self.get_service_name()} initialization failed: {e}")
            if not self.is_optional():
                raise
    
    @abstractmethod
    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        pass
    
    @abstractmethod
    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        pass
    
    @abstractmethod
    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        pass
    
    def get_dependencies(self) -> list[str]:
        """서비스 의존성 목록을 반환합니다."""
        return []
    
    def get_optional_dependencies(self) -> list[str]:
        """선택적 의존성 목록을 반환합니다."""
        return []
    
    def is_optional(self) -> bool:
        """이 서비스가 선택적인지 여부를 반환합니다."""
        return False
    
    def _initialize(self) -> None:
        """
        서비스 초기화 로직을 구현합니다.
        하위 클래스에서 오버라이드하여 사용합니다.
        """
        pass
    
    def get_status(self) -> ServiceStatus:
        """현재 서비스 상태를 반환합니다."""
        return self._status
    
    def is_ready(self) -> bool:
        """서비스가 사용 가능한 상태인지 확인합니다."""
        return self._status == ServiceStatus.READY
    
    def get_service_info(self) -> ServiceInfo:
        """서비스 정보를 반환합니다."""
        return ServiceInfo(
            name=self.get_service_name(),
            version=self.get_service_version(),
            description=self.get_service_description(),
            dependencies=self.get_dependencies(),
            optional_dependencies=self.get_optional_dependencies(),
            status=self._status,
            error_message=self._error_message
        )
    
    def health_check(self) -> HealthCheckResult:
        """
        서비스 헬스체크를 수행합니다.
        하위 클래스에서 오버라이드하여 구체적인 체크 로직을 구현할 수 있습니다.
        """
        if not self.is_ready():
            return HealthCheckResult(
                is_healthy=False, 
                message=f"Service {self.get_service_name()} is not ready",
                details={'status': self._status.value, 'error': self._error_message}
            )
        
        try:
            # 하위 클래스에서 오버라이드할 수 있는 추가 체크
            additional_checks = self._perform_health_checks()
            
            return HealthCheckResult(
                is_healthy=True,
                message=f"Service {self.get_service_name()} is healthy",
                details=additional_checks
            )
            
        except Exception as e:
            return HealthCheckResult(
                is_healthy=False,
                message=f"Health check failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def _perform_health_checks(self) -> Dict[str, Any]:
        """
        서비스별 추가 헬스체크를 수행합니다.
        하위 클래스에서 오버라이드하여 사용합니다.
        
        Returns:
            Dict[str, Any]: 헬스체크 세부 정보
        """
        return {}
    
    def restart(self) -> bool:
        """
        서비스를 재시작합니다.
        
        Returns:
            bool: 재시작 성공 여부
        """
        try:
            self._logger.info(f"Restarting service {self.get_service_name()}")
            self._status = ServiceStatus.INITIALIZING
            self._error_message = None
            
            # 정리 작업
            self._cleanup()
            
            # 재초기화
            self._initialize()
            
            self._status = ServiceStatus.READY
            self._logger.info(f"Service {self.get_service_name()} restarted successfully")
            return True
            
        except Exception as e:
            self._status = ServiceStatus.ERROR
            self._error_message = str(e)
            self._logger.error(f"Service {self.get_service_name()} restart failed: {e}")
            return False
    
    def _cleanup(self) -> None:
        """
        서비스 정리 작업을 수행합니다.
        하위 클래스에서 오버라이드하여 사용합니다.
        """
        pass
    
    def disable(self) -> None:
        """서비스를 비활성화합니다."""
        self._status = ServiceStatus.DISABLED
        self._cleanup()
        self._logger.info(f"Service {self.get_service_name()} disabled")
    
    def __str__(self) -> str:
        return f"{self.get_service_name()}({self._status.value})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.get_service_name()}' status='{self._status.value}'>"


class ConfigurableService(BaseService):
    """설정 가능한 서비스를 위한 기반 클래스"""
    
    def __init__(self, config: Config, **kwargs):
        self._service_config: Dict[str, Any] = {}
        super().__init__(config, **kwargs)
    
    def get_service_config(self) -> Dict[str, Any]:
        """서비스별 설정을 반환합니다."""
        return self._service_config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        서비스 설정을 업데이트합니다.
        
        Args:
            new_config: 새로운 설정값
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # 설정 검증
            if not self._validate_config(new_config):
                return False
            
            old_config = self._service_config.copy()
            self._service_config.update(new_config)
            
            # 설정 변경 적용
            if not self._apply_config_changes(old_config, new_config):
                # 실패 시 롤백
                self._service_config = old_config
                return False
            
            self._logger.info(f"Config updated for service {self.get_service_name()}")
            return True
            
        except Exception as e:
            self._logger.error(f"Config update failed for {self.get_service_name()}: {e}")
            return False
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        설정값 유효성을 검사합니다.
        하위 클래스에서 오버라이드하여 사용합니다.
        """
        return True
    
    def _apply_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> bool:
        """
        설정 변경사항을 적용합니다.
        하위 클래스에서 오버라이드하여 사용합니다.
        """
        return True