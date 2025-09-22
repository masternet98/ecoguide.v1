"""
프롬프트 기능 자동 등록을 위한 데코레이터입니다.

컴포넌트나 함수에 @register_prompt_feature 데코레이터를 사용하면
자동으로 프롬프트 기능 레지스트리에 등록됩니다.
"""
from functools import wraps
from typing import List, Optional, Dict, Any, Callable
from src.app.core.prompt_feature_registry import get_prompt_feature_registry, register_prompt_feature
from src.app.core.logger import get_logger

logger = get_logger(__name__)


def register_prompt_feature_decorator(
    feature_id: str,
    name: str,
    description: str,
    category: str = "general",
    required_services: Optional[List[str]] = None,
    default_prompt_template: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    auto_register: bool = True
):
    """
    프롬프트 기능을 자동 등록하는 데코레이터입니다.
    
    Args:
        feature_id: 기능 고유 식별자
        name: 기능 표시 이름
        description: 기능 설명
        category: 기능 카테고리
        required_services: 필요한 서비스 목록
        default_prompt_template: 기본 프롬프트 템플릿
        metadata: 추가 메타데이터
        auto_register: 자동 등록 여부
    """
    def decorator(cls_or_func: Callable) -> Callable:
        if auto_register:
            try:
                # 기능 등록
                success = register_prompt_feature(
                    feature_id=feature_id,
                    name=name,
                    description=description,
                    category=category,
                    required_services=required_services,
                    default_prompt_template=default_prompt_template,
                    metadata=metadata or {}
                )
                
                if success:
                    logger.info(f"프롬프트 기능 자동 등록 완료: {feature_id}")
                else:
                    logger.warning(f"프롬프트 기능 자동 등록 실패: {feature_id}")
                
            except Exception as e:
                logger.error(f"프롬프트 기능 자동 등록 중 오류 발생 {feature_id}: {e}")
        
        # 클래스나 함수에 메타데이터 추가
        if hasattr(cls_or_func, '__dict__'):
            cls_or_func._prompt_feature_info = {
                'feature_id': feature_id,
                'name': name,
                'description': description,
                'category': category,
                'required_services': required_services or [],
                'default_prompt_template': default_prompt_template,
                'metadata': metadata or {}
            }
        
        return cls_or_func
    
    return decorator


def ensure_feature_registered(feature_id: str):
    """
    기능이 등록되어 있는지 확인하고, 없으면 로그를 남깁니다.
    
    Args:
        feature_id: 확인할 기능 ID
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            registry = get_prompt_feature_registry()
            feature = registry.get_feature(feature_id)
            
            if not feature:
                logger.warning(f"프롬프트 기능이 등록되지 않음: {feature_id}")
            elif not feature.is_active:
                logger.warning(f"프롬프트 기능이 비활성화됨: {feature_id}")
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def validate_feature_dependencies(feature_id: str):
    """
    기능의 의존성을 검증하는 데코레이터입니다.
    
    Args:
        feature_id: 검증할 기능 ID
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 의존성 검증 로직은 실제 서비스 가용성에 따라 구현
            # 현재는 로깅만 수행
            logger.debug(f"프롬프트 기능 의존성 검증: {feature_id}")
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class PromptFeatureRegistry:
    """
    클래스 기반 프롬프트 기능 등록을 위한 유틸리티입니다.
    """
    
    @staticmethod
    def register_from_class(cls: type, feature_id: str = None) -> bool:
        """
        클래스에서 프롬프트 기능 정보를 추출하여 등록합니다.
        
        Args:
            cls: 등록할 클래스
            feature_id: 기능 ID (없으면 클래스명 사용)
            
        Returns:
            등록 성공 여부
        """
        try:
            # 클래스에서 기능 정보 추출
            feature_info = getattr(cls, '_prompt_feature_info', None)
            if not feature_info:
                # 기본 정보 생성
                class_name = cls.__name__
                feature_id = feature_id or class_name.lower().replace('component', '').replace('service', '')
                
                feature_info = {
                    'feature_id': feature_id,
                    'name': class_name,
                    'description': cls.__doc__ or f"{class_name} 기능",
                    'category': 'general',
                    'required_services': [],
                    'default_prompt_template': "",
                    'metadata': {'auto_generated': True}
                }
            
            # 기능 등록
            success = register_prompt_feature(**feature_info)
            
            if success:
                logger.info(f"클래스 기반 프롬프트 기능 등록 완료: {feature_info['feature_id']}")
            
            return success
            
        except Exception as e:
            logger.error(f"클래스 기반 프롬프트 기능 등록 실패 {cls.__name__}: {e}")
            return False
    
    @staticmethod
    def register_from_module(module, prefix: str = "") -> List[str]:
        """
        모듈의 모든 클래스에서 프롬프트 기능을 등록합니다.
        
        Args:
            module: 등록할 모듈
            prefix: 기능 ID 접두사
            
        Returns:
            등록된 기능 ID 목록
        """
        registered_features = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            # 클래스이고 프롬프트 기능 정보가 있는 경우
            if isinstance(obj, type) and hasattr(obj, '_prompt_feature_info'):
                feature_id = f"{prefix}{obj._prompt_feature_info['feature_id']}" if prefix else obj._prompt_feature_info['feature_id']
                
                if PromptFeatureRegistry.register_from_class(obj, feature_id):
                    registered_features.append(feature_id)
        
        logger.info(f"모듈 기반 프롬프트 기능 등록 완료: {len(registered_features)}개")
        return registered_features


# 편의를 위한 별칭
prompt_feature = register_prompt_feature_decorator