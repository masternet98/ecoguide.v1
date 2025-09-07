"""
Vision Service: 이미지 배경 제거, 손/객체 검출, 크기 추정을 위한 서비스.

- `VisionService` 클래스는 모델과 설정을 관리합니다.
- `analyze_image_pipeline` 함수가 핵심적인 end-to-end 분석 로직을 수행합니다.
"""
import numpy as np
import cv2
from PIL import Image
from typing import Optional, List, Tuple, Dict

# 의존성 라이브러리 (설치 필요)
import torch
from ultralytics import YOLO
from rembg import remove
import streamlit as st

from src.services.vision_types import (
    VisionConfig,
    HandDetection,
    ObjectDetection,
    MeasurementResult,
)


@st.cache_resource
def load_yolo_models(config: VisionConfig) -> Tuple[Optional[object], Optional[object]]:
    """
    YOLO 모델들을 로드하고 캐시합니다. 성능 최적화를 위해 한 번만 로드됩니다.
    
    Returns:
        Tuple[object_model, hand_model]: 객체 검출 모델과 손 검출 모델
    """
    try:
        device = 'cuda' if config.use_gpu and torch.cuda.is_available() else 'cpu'
        print(f"Loading cached models on device: {device}")
        
        # 객체 검출 YOLO 모델 로딩
        object_model = YOLO(config.yolo_model_path)
        object_model.to(device)
        print(f"Object detection model cached: {config.yolo_model_path}")
        
        # 손 감지 YOLO 모델 로딩
        hand_model = YOLO(config.yolo_hand_model_path)
        hand_model.to(device)
        print(f"Hand detection model cached: {config.yolo_hand_model_path}")
        
        return object_model, hand_model
    except Exception as e:
        print(f"모델 로딩 실패: {e}")
        return None, None

class VisionService:
    """모델과 설정을 관리하며, 이미지 분석 파이프라인을 제공하는 서비스 클래스."""

    def __init__(self, config: VisionConfig):
        """서비스를 초기화하고 설정을 저장합니다."""
        self.config = config
        # 캐시된 모델 사용으로 성능 최적화
        self.yolo_model, self.yolo_hand_model = load_yolo_models(config)
        print(f"VisionService initialized with cached models")

    def remove_background(self, pil_img: Image.Image) -> Image.Image:
        """rembg를 사용하여 이미지 배경을 제거합니다."""
        return remove(pil_img)

    def detect_hand(self, image_cv: np.ndarray) -> Optional[HandDetection]:
        """YOLO를 사용하여 손을 검출하고 가장 신뢰도 높은 결과를 반환합니다."""
        if not self.yolo_hand_model:
            print("Hand detection model is not initialized.")
            return None

        results = self.yolo_hand_model(image_cv, conf=0.1)
        
        detections = []
        for res in results:
            if res.boxes:
                for box in res.boxes:
                    x1, y1, x2, y2 = [int(i) for i in box.xyxy[0]]
                    detections.append(
                        {
                            "bbox": (x1, y1, x2, y2),
                            "confidence": float(box.conf[0]),
                            "hand_px": float(x2 - x1),
                        }
                    )

        if not detections:
            return None

        # 가장 신뢰도 높은 손 하나만 선택
        best_hand = max(detections, key=lambda x: x["confidence"])

        return HandDetection(
            hand_px=best_hand["hand_px"],
            bbox=best_hand["bbox"],
            confidence=best_hand["confidence"],
            landmarks=None,  # YOLO does not provide landmarks
        )

    def detect_objects(self, image_cv: np.ndarray) -> List[ObjectDetection]:
        """YOLOv8을 사용하여 객체를 검출하고 ObjectDetection 리스트를 반환합니다."""
        if not self.yolo_model:
            print("YOLO model is not initialized.")
            return []

        results = self.yolo_model(image_cv)
        detections = []

        for res in results:
            boxes = res.boxes
            for box in boxes:
                x1, y1, x2, y2 = [int(i) for i in box.xyxy[0]]
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = self.yolo_model.names[cls_id]

                detections.append(
                    ObjectDetection(
                        label=label,
                        cls_id=cls_id,
                        bbox=(x1, y1, x2, y2),
                        width_px=x2 - x1,
                        height_px=y2 - y1,
                        confidence=conf,
                    )
                )
        return detections

    def estimate_size(self, hand: HandDetection, obj: ObjectDetection, user_hand_width_cm: float, hand_dist_cm: float, obj_dist_cm: float) -> Tuple[float, float, float, float]:
        """손과 객체의 픽셀 정보, 거리를 바탕으로 실제 크기를 추정합니다."""
        # 1. 기준이 되는 cm/px 계산 (손 기준)
        if hand.hand_px == 0:
            return 0.0, 0.0, 0.0, 1.0
        cm_per_px_hand = user_hand_width_cm / hand.hand_px

        # 2. 원근 보정 계수 계산
        # 거리가 0이 되는 것을 방지
        hand_dist_cm = max(hand_dist_cm, 1)
        obj_dist_cm = max(obj_dist_cm, 1)
        perspective_scale = obj_dist_cm / hand_dist_cm

        # 3. 원근 보정된 cm/px 계산
        final_cm_per_px = cm_per_px_hand * perspective_scale

        # 4. 객체 크기 계산
        obj_width_cm = obj.width_px * final_cm_per_px
        obj_height_cm = obj.height_px * final_cm_per_px

        return obj_width_cm, obj_height_cm, final_cm_per_px, perspective_scale

    def map_label_to_category_and_fee(self, label: str) -> Tuple[Optional[str], Optional[int]]:
        """YOLO 라벨을 기반으로 폐기물 품목과 수수료를 매핑합니다."""
        print(f"Mapping label '{label}'... (stub)")
        # 여기에 실제 요금표 로직 구현
        if "chair" in label:
            return "의자류", 2000
        return "기타", 1000 # Placeholder

    def analyze_image_pipeline(
        self, 
        pil_img: Image.Image, 
        user_hand_width_cm: Optional[float] = None, 
        user_hand_distance_cm: Optional[int] = None,
        user_object_distance_cm: Optional[int] = None
    ) -> MeasurementResult:
        """
        전체 이미지 분석 파이프라인을 실행합니다.
        1. 배경 제거 (활성화 시)
        2. 이미지 리사이즈 (성능 및 정확도 향상)
        3. 손 검출
        4. 객체 검출
        5. 크기 추정
        6. 품목 및 요금 매핑
        """
        result = MeasurementResult(notes=[])

        if self.config.rembg_enabled:
            pil_img = self.remove_background(pil_img)

        image_cv = np.array(pil_img.convert("RGB"))[:, :, ::-1]

        # --- 이미지 전처리: 리사이즈 ---
        PREPROCESS_MAX_SIZE = 640
        h, w, _ = image_cv.shape
        if max(h, w) > PREPROCESS_MAX_SIZE:
            scale = PREPROCESS_MAX_SIZE / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            image_cv = cv2.resize(image_cv, (new_w, new_h))
            result.notes.append(f"입력 이미지가 너무 커서 {new_w}x{new_h}로 리사이즈되었습니다.")
        
        result.processed_image = image_cv # 오버레이 표시를 위해 처리된 이미지 저장
        # --------------------------------

        hand_detection = self.detect_hand(image_cv)
        if not hand_detection:
            result.notes.append("손을 찾지 못했습니다. 손과 측정할 객체가 명확하게 나오도록 촬영해주세요.")
        result.hand_detection = hand_detection

        object_detections = self.detect_objects(image_cv)
        if not object_detections:
            result.notes.append("측정할 객체를 찾지 못했습니다.")
            return result

        main_object = max(object_detections, key=lambda x: x.confidence, default=None)
        result.object_detection = main_object

        if hand_detection and main_object:
            hand_width_to_use = user_hand_width_cm or self.config.avg_hand_width_cm.get("기본값", 7.8)
            result.notes.append(f"기준 손 너비: {hand_width_to_use:.1f} cm")

            hand_dist = user_hand_distance_cm or self.config.default_hand_distance_cm
            obj_dist = user_object_distance_cm or self.config.default_obj_distance_cm

            width_cm, height_cm, cm_px, p_scale = self.estimate_size(
                hand_detection, main_object, hand_width_to_use, hand_dist, obj_dist
            )
            result.obj_width_cm = width_cm
            result.obj_height_cm = height_cm
            result.cm_per_px = cm_px
            result.perspective_scale = p_scale

            category, fee = self.map_label_to_category_and_fee(main_object.label)
            result.category = category
            result.fee = fee
        elif not hand_detection:
             result.notes.append("크기를 측정하려면 이미지에 손과 객체가 모두 명확해야 합니다.")

        if not result.obj_width_cm:
            result.notes.append("크기 측정에 실패했습니다.")

        return result
