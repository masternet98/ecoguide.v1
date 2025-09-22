"""
프롬프트 기능 관리자 - 기능의 생명주기를 관리합니다.

기능 등록, 활성화/비활성화, 설정 관리, 의존성 검증 등을 담당합니다.
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from datetime import datetime

from src.core.prompt_feature_registry import (
    get_prompt_feature_registry, 
    PromptFeatureRegistry, 
    PromptFeatureInfo
)
from src.core.logger import get_logger


class PromptFeatureManager:
    """프롬프트 기능의 전체 생명주기를 관리하는 클래스입니다."""
    
    def __init__(self, config_path: str = "data/prompts/features"):
        """
        프롬프트 기능 관리자를 초기화합니다.
        
        Args:
            config_path: 설정 파일 경로
        """
        self.logger = get_logger(__name__)
        self.config_path = Path(config_path)
        self.registry = get_prompt_feature_registry()
        
        # 설정 파일 경로들
        self.feature_config_file = self.config_path / "feature_config.json"
        self.dependency_config_file = self.config_path / "dependency_config.json"
        
        # 설정 디렉토리 생성
        self.config_path.mkdir(parents=True, exist_ok=True)
        
        # 기능별 설정 로드
        self._feature_configs: Dict[str, Dict[str, Any]] = {}
        self._dependency_map: Dict[str, Set[str]] = {}
        
        self._load_configurations()
    
    def initialize_default_features(self) -> bool:
        """
        기본 프롬프트 기능들을 초기화합니다.
        
        Returns:
            초기화 성공 여부
        """
        try:
            # 기본 기능 설정들
            default_configs = {
                "camera_analysis": {
                    "enabled": True,
                    "auto_activate": True,
                    "prompt_template_vars": ["object_type", "analysis_detail"],
                    "ui_settings": {
                        "show_confidence": True,
                        "enable_batch_mode": False,
                        "max_image_size": 1024
                    }
                },
                "gallery_upload": {
                    "enabled": True,
                    "auto_activate": True,
                    "accepted_formats": [".jpg", ".jpeg", ".png", ".webp"],
                    "ui_settings": {
                        "show_file_info": True,
                        "enable_multi_select": False,
                        "max_file_size": "10MB"
                    }
                },
                "object_detection": {
                    "enabled": False,  # 무거운 의존성으로 기본 비활성화
                    "auto_activate": False,
                    "model_settings": {
                        "yolo_model": "yolov8n.pt",
                        "confidence_threshold": 0.5,
                        "nms_threshold": 0.4
                    }
                },
                "size_estimation": {
                    "enabled": False,  # 무거운 의존성으로 기본 비활성화
                    "auto_activate": False,
                    "measurement_settings": {
                        "reference_object": "hand",
                        "default_hand_size": 18.0,  # cm
                        "distance_estimation": True
                    }
                },
                "waste_classification": {
                    "enabled": True,
                    "auto_activate": True,
                    "classification_settings": {
                        "include_disposal_cost": True,
                        "suggest_alternatives": True,
                        "location_based": True
                    }
                }
            }
            
            # 설정 저장
            for feature_id, config in default_configs.items():
                self._feature_configs[feature_id] = config
            
            self._save_feature_configs()
            
            # 자동 활성화 기능들 활성화
            for feature_id, config in default_configs.items():
                if config.get("auto_activate", False):
                    self.activate_feature(feature_id)
            
            self.logger.info("기본 프롬프트 기능 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"기본 프롬프트 기능 초기화 실패: {e}")
            return False
    
    def activate_feature(self, feature_id: str, custom_config: Optional[Dict] = None) -> bool:
        """
        프롬프트 기능을 활성화합니다.
        
        Args:
            feature_id: 기능 ID
            custom_config: 사용자 정의 설정
            
        Returns:
            활성화 성공 여부
        """
        try:
            # 기능 존재 확인
            feature = self.registry.get_feature(feature_id)
            if not feature:
                self.logger.error(f"존재하지 않는 기능: {feature_id}")
                return False
            
            # 의존성 검증
            if not self._validate_dependencies(feature_id):
                self.logger.error(f"기능 의존성 불만족: {feature_id}")
                return False
            
            # 기능별 설정 적용
            if custom_config:
                self._feature_configs[feature_id].update(custom_config)
            
            # 레지스트리에서 활성화
            success = self.registry.update_feature_status(feature_id, True)
            
            if success:
                self.logger.info(f"프롬프트 기능 활성화 완료: {feature_id}")
                
                # 설정 저장
                self._save_feature_configs()
            
            return success
            
        except Exception as e:
            self.logger.error(f"프롬프트 기능 활성화 실패 {feature_id}: {e}")
            return False
    
    def deactivate_feature(self, feature_id: str) -> bool:
        """
        프롬프트 기능을 비활성화합니다.
        
        Args:
            feature_id: 기능 ID
            
        Returns:
            비활성화 성공 여부
        """
        try:
            # 의존하는 다른 기능들 확인
            dependent_features = self._get_dependent_features(feature_id)
            if dependent_features:
                self.logger.warning(f"다른 기능들이 {feature_id}에 의존함: {dependent_features}")
                # 의존 기능들도 자동으로 비활성화할지는 정책에 따라 결정
            
            # 레지스트리에서 비활성화
            success = self.registry.update_feature_status(feature_id, False)
            
            if success:
                self.logger.info(f"프롬프트 기능 비활성화 완료: {feature_id}")
                
                # 설정 저장
                self._save_feature_configs()
            
            return success
            
        except Exception as e:
            self.logger.error(f"프롬프트 기능 비활성화 실패 {feature_id}: {e}")
            return False
    
    def get_feature_config(self, feature_id: str) -> Dict[str, Any]:
        """
        기능별 설정을 조회합니다.
        
        Args:
            feature_id: 기능 ID
            
        Returns:
            기능 설정
        """
        return self._feature_configs.get(feature_id, {}).copy()
    
    def update_feature_config(self, feature_id: str, config_updates: Dict[str, Any]) -> bool:
        """
        기능별 설정을 업데이트합니다.
        
        Args:
            feature_id: 기능 ID
            config_updates: 업데이트할 설정
            
        Returns:
            업데이트 성공 여부
        """
        try:
            if feature_id not in self._feature_configs:
                self._feature_configs[feature_id] = {}
            
            self._feature_configs[feature_id].update(config_updates)
            self._save_feature_configs()
            
            self.logger.info(f"프롬프트 기능 설정 업데이트 완료: {feature_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"프롬프트 기능 설정 업데이트 실패 {feature_id}: {e}")
            return False
    
    def validate_all_features(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 기능의 상태를 검증합니다.
        
        Returns:
            검증 결과 딕셔너리
        """
        validation_results = {}
        
        for feature_id in self.registry.get_feature_ids(active_only=False):
            feature = self.registry.get_feature(feature_id)
            if not feature:
                continue
            
            result = {
                'feature_id': feature_id,
                'is_active': feature.is_active,
                'dependencies_satisfied': self._validate_dependencies(feature_id),
                'config_valid': self._validate_feature_config(feature_id),
                'issues': []
            }
            
            # 문제점 수집
            if feature.is_active and not result['dependencies_satisfied']:
                result['issues'].append("의존성 불만족")
            
            if not result['config_valid']:
                result['issues'].append("설정 오류")
            
            validation_results[feature_id] = result
        
        return validation_results
    
    def get_health_report(self) -> Dict[str, Any]:
        """
        프롬프트 기능 시스템의 건강 상태 보고서를 생성합니다.
        
        Returns:
            건강 상태 보고서
        """
        validation_results = self.validate_all_features()
        stats = self.registry.get_statistics()
        
        # 문제가 있는 기능들 수집
        problematic_features = []
        for feature_id, result in validation_results.items():
            if result['issues']:
                problematic_features.append({
                    'feature_id': feature_id,
                    'issues': result['issues']
                })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'healthy' if not problematic_features else 'issues_detected',
            'statistics': stats,
            'problematic_features': problematic_features,
            'total_issues': len(problematic_features),
            'active_features_healthy': len([r for r in validation_results.values() 
                                          if r['is_active'] and not r['issues']])
        }
    
    def _validate_dependencies(self, feature_id: str) -> bool:
        """기능의 의존성을 검증합니다."""
        # 실제 구현에서는 서비스 팩토리나 앱 컨텍스트와 연동
        # 현재는 기본적인 검증만 수행
        feature = self.registry.get_feature(feature_id)
        if not feature or not feature.required_services:
            return True
        
        # 여기서는 간단히 True 반환 (실제로는 서비스 가용성 체크)
        return True
    
    def _validate_feature_config(self, feature_id: str) -> bool:
        """기능 설정의 유효성을 검증합니다."""
        config = self._feature_configs.get(feature_id, {})
        
        # 기본적인 설정 검증
        if not isinstance(config, dict):
            return False
        
        # enabled 필드가 있으면 boolean이어야 함
        if 'enabled' in config and not isinstance(config['enabled'], bool):
            return False
        
        return True
    
    def _get_dependent_features(self, feature_id: str) -> List[str]:
        """특정 기능에 의존하는 다른 기능들을 찾습니다."""
        dependent_features = []
        
        for other_feature_id in self.registry.get_feature_ids(active_only=False):
            other_feature = self.registry.get_feature(other_feature_id)
            if other_feature and feature_id in other_feature.required_services:
                dependent_features.append(other_feature_id)
        
        return dependent_features
    
    def _load_configurations(self):
        """설정 파일들을 로드합니다."""
        # 기능별 설정 로드
        if self.feature_config_file.exists():
            try:
                with open(self.feature_config_file, 'r', encoding='utf-8') as f:
                    self._feature_configs = json.load(f)
                self.logger.info("기능 설정 로드 완료")
            except Exception as e:
                self.logger.error(f"기능 설정 로드 실패: {e}")
        
        # 의존성 맵 로드
        if self.dependency_config_file.exists():
            try:
                with open(self.dependency_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._dependency_map = {k: set(v) for k, v in data.items()}
                self.logger.info("의존성 설정 로드 완료")
            except Exception as e:
                self.logger.error(f"의존성 설정 로드 실패: {e}")
    
    def _save_feature_configs(self):
        """기능 설정을 파일에 저장합니다."""
        try:
            with open(self.feature_config_file, 'w', encoding='utf-8') as f:
                json.dump(self._feature_configs, f, ensure_ascii=False, indent=2)
            self.logger.debug("기능 설정 저장 완료")
        except Exception as e:
            self.logger.error(f"기능 설정 저장 실패: {e}")
    
    def _save_dependency_configs(self):
        """의존성 설정을 파일에 저장합니다."""
        try:
            # set을 list로 변환하여 JSON 직렬화 가능하게 함
            data = {k: list(v) for k, v in self._dependency_map.items()}
            
            with open(self.dependency_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.debug("의존성 설정 저장 완료")
        except Exception as e:
            self.logger.error(f"의존성 설정 저장 실패: {e}")


# 전역 인스턴스
_prompt_feature_manager: Optional[PromptFeatureManager] = None


def get_prompt_feature_manager() -> PromptFeatureManager:
    """전역 프롬프트 기능 관리자 인스턴스를 반환합니다."""
    global _prompt_feature_manager
    if _prompt_feature_manager is None:
        _prompt_feature_manager = PromptFeatureManager()
    return _prompt_feature_manager