"""
애플리케이션 기능의 동적 활성화/비활성화를 관리하는 Feature Registry 시스템.

이 모듈은 기능별로 활성화 여부를 제어하고, 런타임에 기능의 가용성을 
확인할 수 있는 중앙화된 관리 시스템을 제공합니다.
"""
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class FeatureStatus(Enum):
    """기능 상태를 나타내는 열거형"""
    ENABLED = "enabled"
    DISABLED = "disabled" 
    UNAVAILABLE = "unavailable"  # 의존성 부족 등으로 사용 불가
    ERROR = "error"  # 오류 상태


@dataclass
class FeatureDescriptor:
    """기능 정보를 담는 데이터 클래스"""
    name: str
    display_name: str
    description: str
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    status: FeatureStatus = FeatureStatus.DISABLED
    error_message: Optional[str] = None
    config_schema: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)


class FeatureValidator(ABC):
    """기능 유효성 검사를 위한 추상 클래스"""
    
    @abstractmethod
    def validate_feature(self, feature_name: str, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        기능의 유효성을 검사합니다.
        
        Args:
            feature_name: 검사할 기능명
            config: 기능 설정
            
        Returns:
            tuple[bool, str]: (유효성 여부, 오류 메시지)
        """
        pass


class DependencyChecker:
    """기능 의존성을 체크하는 클래스"""
    
    def __init__(self):
        self._import_checkers: Dict[str, Callable] = {}
        self._setup_default_checkers()
    
    def _setup_default_checkers(self) -> None:
        """기본 의존성 체커들을 설정합니다."""
        
        def check_vision_deps():
            """비전 관련 의존성 체크"""
            try:
                import torch
                import ultralytics
                import rembg
                import cv2
                import mediapipe
                return True, "Vision dependencies available"
            except ImportError as e:
                return False, f"Missing vision dependencies: {e}"
        
        def check_openai_deps():
            """OpenAI 관련 의존성 체크"""
            try:
                import openai
                return True, "OpenAI dependencies available"
            except ImportError:
                return False, "Missing openai package"
        
        def check_web_deps():
            """웹 관련 의존성 체크"""
            try:
                import requests
                import bs4
                from bs4 import BeautifulSoup
                return True, "Web dependencies available"
            except ImportError as e:
                return False, f"Missing web dependencies: {e}"
        
        self._import_checkers = {
            'vision': check_vision_deps,
            'openai': check_openai_deps,
            'web': check_web_deps
        }
    
    def check_dependencies(self, dependencies: List[str]) -> tuple[bool, List[str]]:
        """
        의존성 목록을 체크합니다.
        
        Returns:
            tuple[bool, List[str]]: (모든 의존성 만족 여부, 오류 메시지 목록)
        """
        errors = []
        
        for dep in dependencies:
            if dep in self._import_checkers:
                is_available, message = self._import_checkers[dep]()
                if not is_available:
                    errors.append(message)
            else:
                # 일반적인 import 체크
                try:
                    # 특수한 경우 처리: beautifulsoup4는 bs4로 import
                    if dep == 'beautifulsoup4':
                        __import__('bs4')
                    else:
                        __import__(dep)
                except ImportError:
                    errors.append(f"Missing dependency: {dep}")
        
        return len(errors) == 0, errors


class FeatureRegistry:
    """기능 등록 및 관리를 위한 중앙 레지스트리"""
    
    def __init__(self):
        self._features: Dict[str, FeatureDescriptor] = {}
        self._validators: Dict[str, FeatureValidator] = {}
        self._dependency_checker = DependencyChecker()
        self._feature_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_feature(
        self,
        name: str,
        display_name: str,
        description: str,
        version: str = "1.0.0",
        dependencies: List[str] = None,
        optional_dependencies: List[str] = None,
        config_schema: Dict[str, Any] = None,
        tags: List[str] = None,
        auto_enable: bool = False
    ) -> None:
        """기능을 레지스트리에 등록합니다."""
        
        feature = FeatureDescriptor(
            name=name,
            display_name=display_name,
            description=description,
            version=version,
            dependencies=dependencies or [],
            optional_dependencies=optional_dependencies or [],
            config_schema=config_schema,
            tags=tags or []
        )
        
        self._features[name] = feature
        self._feature_configs[name] = {}
        
        # 의존성 체크 및 상태 설정
        self._check_and_update_feature_status(name)
        
        # 자동 활성화 요청 시 시도
        if auto_enable and feature.status != FeatureStatus.UNAVAILABLE:
            self.enable_feature(name)
        
        logger.info(f"Feature registered: {name} (status: {feature.status.value})")
    
    def _check_and_update_feature_status(self, feature_name: str) -> None:
        """기능의 의존성을 체크하고 상태를 업데이트합니다."""
        feature = self._features[feature_name]
        
        # 필수 의존성 체크
        deps_ok, errors = self._dependency_checker.check_dependencies(feature.dependencies)
        
        if not deps_ok:
            feature.status = FeatureStatus.UNAVAILABLE
            feature.error_message = "; ".join(errors)
            logger.warning(f"Feature {feature_name} unavailable: {feature.error_message}")
        else:
            # 필수 의존성은 만족, 선택적 의존성은 로그만
            opt_deps_ok, opt_errors = self._dependency_checker.check_dependencies(
                feature.optional_dependencies
            )
            if not opt_deps_ok:
                logger.info(f"Feature {feature_name} missing optional dependencies: {'; '.join(opt_errors)}")
            
            if feature.status == FeatureStatus.UNAVAILABLE:
                feature.status = FeatureStatus.DISABLED
                feature.error_message = None
    
    def enable_feature(self, feature_name: str, config: Dict[str, Any] = None) -> bool:
        """기능을 활성화합니다."""
        if feature_name not in self._features:
            logger.error(f"Unknown feature: {feature_name}")
            return False
        
        feature = self._features[feature_name]
        
        # 사용 불가능한 기능은 활성화할 수 없음
        if feature.status == FeatureStatus.UNAVAILABLE:
            logger.warning(f"Cannot enable unavailable feature: {feature_name}")
            return False
        
        # 설정 검증
        if config:
            if not self._validate_feature_config(feature_name, config):
                return False
            self._feature_configs[feature_name] = config.copy()
        
        try:
            feature.status = FeatureStatus.ENABLED
            feature.error_message = None
            logger.info(f"Feature enabled: {feature_name}")
            return True
            
        except Exception as e:
            feature.status = FeatureStatus.ERROR
            feature.error_message = str(e)
            logger.error(f"Failed to enable feature {feature_name}: {e}")
            return False
    
    def disable_feature(self, feature_name: str) -> bool:
        """기능을 비활성화합니다."""
        if feature_name not in self._features:
            logger.error(f"Unknown feature: {feature_name}")
            return False
        
        feature = self._features[feature_name]
        
        try:
            if feature.status == FeatureStatus.UNAVAILABLE:
                return True  # 이미 사용 불가능한 상태
            
            feature.status = FeatureStatus.DISABLED
            feature.error_message = None
            logger.info(f"Feature disabled: {feature_name}")
            return True
            
        except Exception as e:
            feature.status = FeatureStatus.ERROR
            feature.error_message = str(e)
            logger.error(f"Failed to disable feature {feature_name}: {e}")
            return False
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """기능이 활성화되어 있는지 확인합니다."""
        if feature_name not in self._features:
            return False
        return self._features[feature_name].status == FeatureStatus.ENABLED
    
    def is_feature_available(self, feature_name: str) -> bool:
        """기능이 사용 가능한지 확인합니다 (의존성 충족)."""
        if feature_name not in self._features:
            return False
        status = self._features[feature_name].status
        return status in [FeatureStatus.ENABLED, FeatureStatus.DISABLED]
    
    def get_feature_info(self, feature_name: str) -> Optional[FeatureDescriptor]:
        """기능 정보를 반환합니다."""
        return self._features.get(feature_name)
    
    def list_features(self, tag_filter: Optional[str] = None, status_filter: Optional[FeatureStatus] = None) -> List[FeatureDescriptor]:
        """등록된 기능 목록을 반환합니다."""
        features = list(self._features.values())
        
        if tag_filter:
            features = [f for f in features if tag_filter in f.tags]
        
        if status_filter:
            features = [f for f in features if f.status == status_filter]
        
        return features
    
    def get_feature_config(self, feature_name: str) -> Dict[str, Any]:
        """기능 설정을 반환합니다."""
        return self._feature_configs.get(feature_name, {}).copy()
    
    def update_feature_config(self, feature_name: str, config: Dict[str, Any]) -> bool:
        """기능 설정을 업데이트합니다."""
        if feature_name not in self._features:
            return False
        
        if not self._validate_feature_config(feature_name, config):
            return False
        
        self._feature_configs[feature_name].update(config)
        logger.info(f"Feature config updated: {feature_name}")
        return True
    
    def _validate_feature_config(self, feature_name: str, config: Dict[str, Any]) -> bool:
        """기능 설정의 유효성을 검사합니다."""
        feature = self._features[feature_name]
        
        # 스키마 검증 (간단한 형태)
        if feature.config_schema:
            for key, expected_type in feature.config_schema.items():
                if key in config:
                    if not isinstance(config[key], expected_type):
                        logger.error(f"Invalid config for {feature_name}.{key}: expected {expected_type}")
                        return False
        
        # 커스텀 검증기가 있는 경우
        if feature_name in self._validators:
            is_valid, error_msg = self._validators[feature_name].validate_feature(feature_name, config)
            if not is_valid:
                logger.error(f"Feature config validation failed for {feature_name}: {error_msg}")
                return False
        
        return True
    
    def register_validator(self, feature_name: str, validator: FeatureValidator) -> None:
        """기능별 커스텀 검증기를 등록합니다."""
        self._validators[feature_name] = validator
        logger.debug(f"Validator registered for feature: {feature_name}")
    
    def refresh_feature_status(self, feature_name: Optional[str] = None) -> None:
        """기능 상태를 새로고침합니다 (의존성 재체크)."""
        if feature_name:
            if feature_name in self._features:
                self._check_and_update_feature_status(feature_name)
        else:
            for name in self._features:
                self._check_and_update_feature_status(name)
        
        logger.info("Feature status refreshed")


def create_default_feature_registry() -> FeatureRegistry:
    """기본 기능들이 등록된 레지스트리를 생성합니다."""
    registry = FeatureRegistry()
    
    # Vision 기능 등록
    registry.register_feature(
        name="vision_analysis",
        display_name="비전 분석",
        description="이미지 객체 검출, 배경 제거, 손 추적 등 컴퓨터 비전 기능",
        dependencies=["torch", "ultralytics", "rembg", "cv2", "mediapipe"],
        tags=["vision", "ai", "core"],
        auto_enable=False  # 무거운 의존성으로 인해 수동 활성화
    )
    
    # OpenAI 기능 등록
    registry.register_feature(
        name="openai_vision",
        display_name="OpenAI 비전 API",
        description="OpenAI Vision API를 통한 이미지 분석",
        dependencies=["openai"],
        tags=["vision", "api", "core"],
        auto_enable=True
    )
    
    # 터널 관리 기능
    registry.register_feature(
        name="tunnel_management",
        display_name="터널 관리",
        description="Cloudflared 터널 관리 및 모니터링",
        dependencies=[],
        tags=["admin", "network"],
        auto_enable=True
    )
    
    # 행정구역 관리 기능
    registry.register_feature(
        name="district_management", 
        display_name="행정구역 관리",
        description="대한민국 행정구역 데이터 다운로드 및 관리",
        dependencies=["requests", "beautifulsoup4", "pandas"],
        tags=["admin", "data"],
        auto_enable=True
    )
    
    # 링크 수집 기능
    registry.register_feature(
        name="link_collector",
        display_name="링크 수집기",
        description="시군구별 대형폐기물 배출 신고 링크 자동 수집",
        dependencies=["requests", "beautifulsoup4"],
        tags=["admin", "data"],
        auto_enable=True
    )
    
    logger.info("Default feature registry created")
    return registry