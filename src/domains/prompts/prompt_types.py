"""
프롬프트 관리 시스템의 타입 정의 모듈입니다.

프롬프트 관리에 필요한 데이터 클래스와 열거형들을 정의합니다.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class PromptCategory(Enum):
    """프롬프트 카테고리를 정의하는 열거형입니다."""
    VISION_ANALYSIS = "vision_analysis"  # 이미지 분석용
    OBJECT_DETECTION = "object_detection"  # 객체 탐지용
    SIZE_ESTIMATION = "size_estimation"  # 크기 추정용
    WASTE_CLASSIFICATION = "waste_classification"  # 폐기물 분류용
    GENERAL_ANALYSIS = "general_analysis"  # 일반 분석용
    CUSTOM = "custom"  # 사용자 정의


class PromptStatus(Enum):
    """프롬프트 상태를 정의하는 열거형입니다."""
    ACTIVE = "active"  # 활성화됨
    INACTIVE = "inactive"  # 비활성화됨
    DRAFT = "draft"  # 초안
    DEPRECATED = "deprecated"  # 사용 중단


@dataclass
class PromptTemplate:
    """
    프롬프트 템플릿을 나타내는 데이터 클래스입니다.
    """
    id: str  # 고유 식별자
    name: str  # 프롬프트 이름
    description: str  # 프롬프트 설명
    category: PromptCategory  # 카테고리
    template: str  # 프롬프트 템플릿 내용
    variables: List[str] = field(default_factory=list)  # 템플릿 변수들
    status: PromptStatus = PromptStatus.ACTIVE  # 상태
    created_at: datetime = field(default_factory=datetime.now)  # 생성일시
    updated_at: datetime = field(default_factory=datetime.now)  # 수정일시
    created_by: str = "admin"  # 생성자
    version: str = "1.0"  # 버전
    tags: List[str] = field(default_factory=list)  # 태그들
    metadata: Dict[str, Any] = field(default_factory=dict)  # 메타데이터
    
    def __post_init__(self):
        """초기화 후 처리를 수행합니다."""
        self.updated_at = datetime.now()


@dataclass
class FeaturePromptMapping:
    """
    기능과 프롬프트의 매핑을 나타내는 데이터 클래스입니다.
    """
    feature_id: str  # 기능 식별자 (예: "camera_analysis", "gallery_upload")
    prompt_id: str  # 프롬프트 식별자
    is_default: bool = False  # 기본 프롬프트 여부
    priority: int = 0  # 우선순위 (낮은 숫자가 높은 우선순위)
    conditions: Dict[str, Any] = field(default_factory=dict)  # 적용 조건
    created_at: datetime = field(default_factory=datetime.now)  # 생성일시


@dataclass
class PromptUsageStats:
    """
    프롬프트 사용 통계를 나타내는 데이터 클래스입니다.
    """
    prompt_id: str  # 프롬프트 식별자
    usage_count: int = 0  # 사용 횟수
    last_used: Optional[datetime] = None  # 마지막 사용일시
    success_rate: float = 0.0  # 성공률
    average_response_time: float = 0.0  # 평균 응답 시간
    user_ratings: List[int] = field(default_factory=list)  # 사용자 평점들


@dataclass
class PromptConfig:
    """
    프롬프트 관리 시스템의 설정을 포함하는 데이터 클래스입니다.
    """
    storage_path: str = "data/prompts"  # 프롬프트 저장 경로
    backup_enabled: bool = True  # 백업 활성화 여부
    backup_interval_hours: int = 24  # 백업 주기 (시간)
    max_versions: int = 10  # 최대 버전 보관 수
    auto_backup_on_change: bool = True  # 변경시 자동 백업
    validation_enabled: bool = True  # 검증 활성화
    usage_tracking_enabled: bool = True  # 사용 통계 추적
    cache_enabled: bool = True  # 캐시 활성화
    cache_ttl_minutes: int = 60  # 캐시 유효시간 (분)