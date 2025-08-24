import io
from PIL import Image
import pytest

from src.services.vision_service import VisionService, analyze_image, get_default_service
from src.services.vision_types import HandDetection, ObjectDetection, VisionConfig


def make_image(width=400, height=300, color=(200, 200, 200)):
    img = Image.new("RGB", (width, height), color=color)
    return img


def test_estimate_size_with_mocked_detections(monkeypatch):
    """
    손 폭 100px, 객체 폭 200px 으로 모킹.
    기본 손 실측(cm)=8.0 사용 -> cm_per_px = 8/100 = 0.08
    예상 object_cm = 200 * 0.08 = 16.0
    """
    img = make_image(800, 600)

    svc = VisionService(config=VisionConfig(rembg_enabled=False))
    # avoid real model loading
    monkeypatch.setattr(svc, "load_models", lambda *a, **k: None)

    # mock hand detection
    mocked_hand = HandDetection(
        landmarks=[(10, 10), (110, 10)], bbox=(10, 10, 100, 120), hand_width_px=100.0, confidence=1.0
    )
    monkeypatch.setattr(svc, "detect_hand_mediapipe", lambda image: mocked_hand)

    # mock object detection: label 'chair', width 200px
    mocked_obj = ObjectDetection(label="chair", class_id=1, bbox=(50, 50, 200, 150), confidence=0.9)
    monkeypatch.setattr(svc, "detect_objects_yolo", lambda image, conf_threshold=None: [mocked_obj])

    # use service directly
    result = svc.analyze_image_pipeline(image=img)

    assert result.success is True
    assert result.object_label == "chair"
    assert result.object_bbox == (50, 50, 200, 150)
    # expected ~16.0 cm
    assert result.object_cm is not None
    assert abs(result.object_cm - 16.0) < 1e-6
    assert result.cm_per_px == pytest.approx(8.0 / 100.0)


def test_no_objects_detected_returns_failure(monkeypatch):
    img = make_image(400, 300)
    svc = VisionService(config=VisionConfig(rembg_enabled=False))
    monkeypatch.setattr(svc, "load_models", lambda *a, **k: None)

    # mock hand detection valid
    mocked_hand = HandDetection(landmarks=[], bbox=(0, 0, 80, 90), hand_width_px=80.0, confidence=1.0)
    monkeypatch.setattr(svc, "detect_hand_mediapipe", lambda image: mocked_hand)

    # mock no object detections
    monkeypatch.setattr(svc, "detect_objects_yolo", lambda image, conf_threshold=None: [])

    result = svc.analyze_image_pipeline(image=img)
    assert result.success is False
    assert any("객체" in note for note in result.notes)
