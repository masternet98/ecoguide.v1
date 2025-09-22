"""
프롬프트-기능 매핑을 위한 레지스트리 시스템입니다.

하드코딩된 기능 목록을 제거하고 동적 기능 관리를 통해
확장성과 유지보수성을 향상시킵니다.
"""
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime

from src.core.logger import get_logger


@dataclass
class PromptFeatureInfo:
    """프롬프트 기능 정보를 담는 데이터클래스입니다."""
    
    feature_id: str  # 기능 고유 식별자
    name: str  # 기능 표시 이름
    description: str  # 기능 설명
    category: str  # 기능 카테고리 (analysis, input, management 등)
    is_active: bool = True  # 기능 활성화 상태
    required_services: List[str] = None  # 필요한 서비스 목록
    default_prompt_template: str = ""  # 기본 프롬프트 템플릿
    metadata: Dict = None  # 추가 메타데이터
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.required_services is None:
            self.required_services = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class PromptFeatureRegistry:
    """프롬프트 기능 레지스트리 클래스입니다."""
    
    def __init__(self, config_path: str = "data/prompts/features"):
        """
        프롬프트 기능 레지스트리를 초기화합니다.
        
        Args:
            config_path: 기능 설정 파일 경로
        """
        self.logger = get_logger(__name__)
        self.config_path = Path(config_path)
        self.config_file = self.config_path / "prompt_feature_registry.json"
        self._features: Dict[str, PromptFeatureInfo] = {}
        self._registered_at_runtime: Set[str] = set()
        
        # 설정 디렉토리 생성
        self.config_path.mkdir(parents=True, exist_ok=True)
        
        # 데이터 로드
        self._load_features()
        
        # 기본 기능들 등록
        self._register_default_features()
    
    def register_feature(self, 
                        feature_id: str,
                        name: str,
                        description: str,
                        category: str = "general",
                        is_active: bool = True,
                        required_services: List[str] = None,
                        default_prompt_template: str = "",
                        metadata: Dict = None,
                        auto_save: bool = True) -> bool:
        """
        새 프롬프트 기능을 등록합니다.
        
        Args:
            feature_id: 기능 ID
            name: 기능 이름
            description: 기능 설명
            category: 기능 카테고리
            is_active: 활성화 상태
            required_services: 필요한 서비스 목록
            default_prompt_template: 기본 프롬프트 템플릿
            metadata: 추가 메타데이터
            auto_save: 자동 저장 여부
            
        Returns:
            등록 성공 여부
        """
        try:
            feature_info = PromptFeatureInfo(
                feature_id=feature_id,
                name=name,
                description=description,
                category=category,
                is_active=is_active,
                required_services=required_services or [],
                default_prompt_template=default_prompt_template,
                metadata=metadata or {}
            )
            
            # 기존 기능 업데이트인 경우 생성일 유지
            if feature_id in self._features:
                feature_info.created_at = self._features[feature_id].created_at
                feature_info.updated_at = datetime.now()
            
            self._features[feature_id] = feature_info
            self._registered_at_runtime.add(feature_id)
            
            if auto_save:
                self._save_features()
            
            self.logger.info(f"프롬프트 기능 등록 완료: {feature_id} - {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"프롬프트 기능 등록 실패 {feature_id}: {e}")
            return False
    
    def unregister_feature(self, feature_id: str, auto_save: bool = True) -> bool:
        """
        프롬프트 기능 등록을 해제합니다.
        
        Args:
            feature_id: 기능 ID
            auto_save: 자동 저장 여부
            
        Returns:
            해제 성공 여부
        """
        if feature_id not in self._features:
            self.logger.warning(f"존재하지 않는 기능 ID: {feature_id}")
            return False
        
        try:
            del self._features[feature_id]
            self._registered_at_runtime.discard(feature_id)
            
            if auto_save:
                self._save_features()
            
            self.logger.info(f"프롬프트 기능 등록 해제 완료: {feature_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"프롬프트 기능 등록 해제 실패 {feature_id}: {e}")
            return False
    
    def get_feature(self, feature_id: str) -> Optional[PromptFeatureInfo]:
        """
        프롬프트 기능 정보를 조회합니다.
        
        Args:
            feature_id: 기능 ID
            
        Returns:
            기능 정보 또는 None
        """
        return self._features.get(feature_id)
    
    def list_features(self, 
                     category: Optional[str] = None,
                     active_only: bool = True) -> List[PromptFeatureInfo]:
        """
        프롬프트 기능 목록을 조회합니다.
        
        Args:
            category: 필터링할 카테고리
            active_only: 활성 기능만 조회 여부
            
        Returns:
            기능 정보 목록
        """
        features = list(self._features.values())
        
        if active_only:
            features = [f for f in features if f.is_active]
        
        if category:
            features = [f for f in features if f.category == category]
        
        # feature_id로 정렬
        return sorted(features, key=lambda f: f.feature_id)
    
    def get_feature_ids(self, 
                       category: Optional[str] = None,
                       active_only: bool = True) -> List[str]:
        """
        프롬프트 기능 ID 목록을 조회합니다.
        
        Args:
            category: 필터링할 카테고리
            active_only: 활성 기능만 조회 여부
            
        Returns:
            기능 ID 목록
        """
        features = self.list_features(category=category, active_only=active_only)
        return [f.feature_id for f in features]
    
    def get_categories(self) -> List[str]:
        """
        사용 중인 카테고리 목록을 조회합니다.
        
        Returns:
            카테고리 목록
        """
        categories = {f.category for f in self._features.values()}
        return sorted(categories)
    
    def update_feature_status(self, feature_id: str, is_active: bool, auto_save: bool = True) -> bool:
        """
        기능 활성화 상태를 업데이트합니다.
        
        Args:
            feature_id: 기능 ID
            is_active: 활성화 상태
            auto_save: 자동 저장 여부
            
        Returns:
            업데이트 성공 여부
        """
        if feature_id not in self._features:
            return False
        
        self._features[feature_id].is_active = is_active
        self._features[feature_id].updated_at = datetime.now()
        
        if auto_save:
            self._save_features()
        
        return True
    
    def validate_feature_dependencies(self, feature_id: str, available_services: Set[str]) -> tuple[bool, List[str]]:
        """
        기능의 의존성을 검증합니다.
        
        Args:
            feature_id: 기능 ID
            available_services: 사용 가능한 서비스 목록
            
        Returns:
            (검증 성공 여부, 누락된 서비스 목록)
        """
        feature = self.get_feature(feature_id)
        if not feature:
            return False, []
        
        missing_services = []
        for required_service in feature.required_services:
            if required_service not in available_services:
                missing_services.append(required_service)
        
        return len(missing_services) == 0, missing_services
    
    def get_feature_display_info(self, feature_id: str) -> Dict[str, str]:
        """
        UI 표시용 기능 정보를 반환합니다.
        
        Args:
            feature_id: 기능 ID
            
        Returns:
            표시용 정보 딕셔너리
        """
        feature = self.get_feature(feature_id)
        if not feature:
            return {
                "name": feature_id,
                "description": "알 수 없는 기능",
                "category": "unknown"
            }
        
        return {
            "name": feature.name,
            "description": feature.description,
            "category": feature.category,
            "status": "활성" if feature.is_active else "비활성",
            "required_services": ", ".join(feature.required_services) if feature.required_services else "없음"
        }
    
    def _register_default_features(self):
        """기본 프롬프트 기능들을 등록합니다."""
        default_features = [
            {
                "feature_id": "camera_analysis",
                "name": "카메라 이미지 분석",
                "description": "카메라로 촬영한 이미지를 AI로 분석합니다.",
                "category": "analysis",
                "required_services": ["openai_service"],
                "default_prompt_template": "이 이미지를 분석해서 다음 정보를 JSON 형식으로 제공해주세요: 1) 물체의 이름 2) 물체의 카테고리 3) 주요 특징",
                "metadata": {"input_type": "camera", "analysis_type": "vision"}
            },
            {
                "feature_id": "gallery_upload",
                "name": "갤러리 이미지 업로드",
                "description": "갤러리에서 이미지를 선택하여 분석합니다.",
                "category": "input",
                "required_services": ["openai_service"],
                "default_prompt_template": "업로드된 이미지를 분석해서 다음 정보를 JSON 형식으로 제공해주세요: 1) 물체의 이름 2) 물체의 카테고리 3) 주요 특징",
                "metadata": {"input_type": "file", "analysis_type": "vision"}
            },
            {
                "feature_id": "object_detection",
                "name": "객체 탐지",
                "description": "이미지에서 객체를 탐지하고 분류합니다.",
                "category": "analysis",
                "required_services": ["vision_service"],
                "default_prompt_template": "이미지에서 객체를 탐지하여 각 객체의 위치, 크기, 분류 정보를 제공해주세요.",
                "metadata": {"analysis_type": "detection", "models": ["yolo"]}
            },
            {
                "feature_id": "size_estimation",
                "name": "크기 추정",
                "description": "탐지된 객체의 크기를 추정합니다.",
                "category": "analysis",
                "required_services": ["vision_service"],
                "default_prompt_template": "이미지에서 손을 기준으로 물체의 크기를 추정해주세요. 가로, 세로, 높이 정보를 cm 단위로 제공해주세요.",
                "metadata": {"analysis_type": "measurement", "reference": "hand_scale"}
            },
            {
                "feature_id": "waste_classification",
                "name": "폐기물 분류",
                "description": "대형폐기물을 분류하고 처리방법을 제안합니다.",
                "category": "classification",
                "required_services": ["openai_service"],
                "default_prompt_template": "이 물체가 대형폐기물인지 판단하고, 맞다면 처리 방법과 예상 수수료를 제안해주세요.",
                "metadata": {"domain": "waste_management", "output": "disposal_guide"}
            }
        ]
        
        for feature_data in default_features:
            if feature_data["feature_id"] not in self._features:
                self.register_feature(auto_save=False, **feature_data)
        
        # 기본 기능 등록 후 저장
        self._save_features()
    
    def _load_features(self):
        """기능 설정을 파일에서 로드합니다."""
        if not self.config_file.exists():
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for feature_data in data.get('features', []):
                # 날짜 문자열을 datetime 객체로 변환
                if 'created_at' in feature_data:
                    feature_data['created_at'] = datetime.fromisoformat(feature_data['created_at'])
                if 'updated_at' in feature_data:
                    feature_data['updated_at'] = datetime.fromisoformat(feature_data['updated_at'])
                
                feature_info = PromptFeatureInfo(**feature_data)
                self._features[feature_info.feature_id] = feature_info
            
            self.logger.info(f"프롬프트 기능 설정 로드 완료: {len(self._features)}개")
            
        except Exception as e:
            self.logger.error(f"프롬프트 기능 설정 로드 실패: {e}")
    
    def _save_features(self):
        """기능 설정을 파일에 저장합니다."""
        try:
            data = {
                'version': '1.0',
                'updated_at': datetime.now().isoformat(),
                'features': []
            }
            
            for feature in self._features.values():
                feature_data = asdict(feature)
                
                # datetime 객체를 ISO 형식 문자열로 변환
                if feature_data['created_at']:
                    feature_data['created_at'] = feature.created_at.isoformat()
                if feature_data['updated_at']:
                    feature_data['updated_at'] = feature.updated_at.isoformat()
                
                data['features'].append(feature_data)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"프롬프트 기능 설정 저장 완료: {len(self._features)}개")
            
        except Exception as e:
            self.logger.error(f"프롬프트 기능 설정 저장 실패: {e}")
    
    def get_statistics(self) -> Dict:
        """프롬프트 기능 레지스트리 통계를 조회합니다."""
        all_features = list(self._features.values())
        active_features = [f for f in all_features if f.is_active]
        categories = self.get_categories()
        
        category_counts = {}
        for category in categories:
            category_counts[category] = len([f for f in all_features if f.category == category])
        
        return {
            'total_features': len(all_features),
            'active_features': len(active_features),
            'inactive_features': len(all_features) - len(active_features),
            'total_categories': len(categories),
            'category_distribution': category_counts,
            'runtime_registered': len(self._registered_at_runtime)
        }


# 전역 인스턴스
_prompt_feature_registry: Optional[PromptFeatureRegistry] = None


def get_prompt_feature_registry() -> PromptFeatureRegistry:
    """전역 프롬프트 기능 레지스트리 인스턴스를 반환합니다."""
    global _prompt_feature_registry
    if _prompt_feature_registry is None:
        _prompt_feature_registry = PromptFeatureRegistry()
    return _prompt_feature_registry


def register_prompt_feature(feature_id: str, name: str, description: str, **kwargs):
    """프롬프트 기능을 등록하는 편의 함수입니다."""
    return get_prompt_feature_registry().register_feature(feature_id, name, description, **kwargs)


def get_available_prompt_features(category: Optional[str] = None, active_only: bool = True) -> List[str]:
    """사용 가능한 프롬프트 기능 ID 목록을 반환하는 편의 함수입니다."""
    return get_prompt_feature_registry().get_feature_ids(category=category, active_only=active_only)