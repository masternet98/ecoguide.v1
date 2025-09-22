"""
비전 파이프라인에서 사용되는 데이터 클래스를 정의합니다.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
import numpy as np

@dataclass
class HandDetection:
    """MediaPipe에서 검출된 손 정보를 담습니다."""
    hand_px: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
    landmarks: Optional[List[Tuple[float, float]]] = None # 정규화된 랜드마크
    confidence: Optional[float] = None

@dataclass
class ObjectDetection:
    """YOLO에서 검출된 객체 정보를 담습니다."""
    label: str
    cls_id: int
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    width_px: int
    height_px: int
    confidence: float

@dataclass
class MeasurementResult:
    """이미지 분석 및 측정 파이프라인의 최종 결과를 담습니다."""
    object_detection: Optional[ObjectDetection] = None
    hand_detection: Optional[HandDetection] = None
    obj_width_cm: Optional[float] = None
    obj_height_cm: Optional[float] = None
    cm_per_px: Optional[float] = None
    perspective_scale: Optional[float] = None
    category: Optional[str] = None
    fee: Optional[int] = None
    notes: List[str] = field(default_factory=list)
    processed_image: Optional[np.ndarray] = field(default=None, repr=False) # 분석에 사용된 이미지 (numpy array)

@dataclass
class VisionConfig:
    """Vision Service의 설정을 관리합니다."""
    yolo_model_path: str = "yolov8n.pt"
    yolo_hand_model_path: str = "models/yolov8n-hand-pose.pt" # 손 감지용 YOLO 모델
    rembg_enabled: bool = True
    avg_hand_width_cm: Dict[str, float] = field(
        default_factory=lambda: {"남성": 8.4, "여성": 7.3, "기본값": 7.8}
    )
    default_hand_distance_cm: int = 50
    default_obj_distance_cm: int = 150
    use_gpu: bool = False
