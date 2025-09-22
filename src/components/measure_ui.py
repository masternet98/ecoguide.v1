"""
Streamlit UI component for measurement pipeline.

Provides:
- 이미지 업로드 / 카메라 업로드 지원
- rembg 토글, GPU 토글
- 성별 셀렉터 및 사용자 손 폭(cm) 입력
- 손/객체 거리 입력 (cm)
- 실행 버튼으로 VisionService.analyze_image_pipeline 호출
- 중간 결과(배경 제거 이미지), 오버레이 이미지 및 수치 출력
"""
import io
from typing import Optional
import cv2
import numpy as np

import streamlit as st
from PIL import Image, ImageDraw

from src.services.vision_service import VisionService
from src.domains.analysis.vision_types import (
    VisionConfig,
    HandDetection,
    ObjectDetection,
)

def _draw_detections(
    image: Image.Image, hand: Optional[HandDetection], obj: Optional[ObjectDetection]
) -> Image.Image:
    """검출된 손과 객체의 경계 상자를 이미지 위에 그립니다."""
    img = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(img)

    # 손 경계 상자 (파란색)
    if hand and hand.bbox:
        draw.rectangle(hand.bbox, outline="blue", width=3)
        draw.text((hand.bbox[0], max(hand.bbox[1] - 18, 0)), "주먹", fill="blue")

    # 객체 경계 상자 (빨간색)
    if obj and obj.bbox:
        draw.rectangle(obj.bbox, outline="red", width=3)
        label = obj.label or "object"
        draw.text(
            (obj.bbox[0], max(obj.bbox[1] - 18, 0)),
            f"{label} ({obj.confidence:.2f})",
            fill="red",
        )
    return img

def render_measure_ui():
    """측정 파이프라인을 위한 Streamlit UI를 렌더링합니다."""
    st.header("물체 크기 측정 (주먹 너비 기준)")

    col1, col2 = st.columns([2, 1])
    image = None

    with col1:
        uploaded = st.file_uploader("이미지 업로드", type=["jpg", "jpeg", "png"])
        if uploaded:
            image = Image.open(uploaded)
        else:
            st.info("측정할 이미지를 업로드하세요.")
            if st.button("샘플 이미지 사용"):
                # Placeholder for sample image logic
                img = Image.new("RGB", (640, 480), color=(200, 200, 200))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                image = Image.open(buf)

        if image:
            st.image(image, caption="원본 이미지", use_container_width=True)

    with col2:
        st.subheader("설정")
        cfg = VisionConfig() # 기본 설정 로드

        rembg_enabled = st.checkbox("배경 제거 사용 (rembg)", value=cfg.rembg_enabled)
        use_gpu = st.checkbox("GPU 사용 (가능한 경우)", value=cfg.use_gpu)

        st.markdown("**주먹 폭 기준:**")
        gender_options = list(cfg.avg_hand_width_cm.keys()) + ["사용자 정의"]
        gender = st.selectbox("성별 (평균 주먹 폭 추정)", gender_options)

        user_hand_width_cm = None
        if gender == "사용자 정의":
            user_hand_width_cm = st.number_input(
                "주먹 폭 (cm) 입력", value=8.0, min_value=5.0, max_value=12.0, format="%.1f"
            )
        else:
            user_hand_width_cm = cfg.avg_hand_width_cm[gender]
            st.info(f"선택된 평균 주먹 폭: {user_hand_width_cm} cm")

        st.markdown("**거리 (선택 사항):**")
        hand_dist_cm = st.number_input(
            "주먹까지 거리 (cm)", value=cfg.default_hand_distance_cm, format="%d"
        )
        obj_dist_cm = st.number_input(
            "물체까지 거리 (cm)", value=cfg.default_obj_distance_cm, format="%d"
        )

        run = st.button("측정 실행", use_container_width=True)

    if not image or not run:
        st.stop()

    # --- 실행 로직 ---
    vcfg = VisionConfig(
        rembg_enabled=rembg_enabled,
        use_gpu=use_gpu,
        # 나머지 설정은 기본값 사용
    )
    svc = VisionService(config=vcfg)

    with st.spinner("모델 로드 및 분석 중..."):
        svc.load_models()
        result = svc.analyze_image_pipeline(
            pil_img=image,
            user_hand_width_cm=user_hand_width_cm,
            user_hand_distance_cm=hand_dist_cm,
            user_object_distance_cm=obj_dist_cm,
        )

    st.subheader("측정 결과")

    if result.notes:
        for note in result.notes:
            st.warning(note)

    if result.obj_width_cm and result.obj_height_cm:
        c1, c2 = st.columns(2)
        c1.metric(label="가로 길이 (cm)", value=f"{result.obj_width_cm:.1f}")
        c2.metric(label="세로 길이 (cm)", value=f"{result.obj_height_cm:.1f}")

        if result.category and result.fee:
            st.success(f"**품목:** {result.category} | **예상 수수료:** {result.fee:,}원")
        else:
            st.info("이 품목은 수수료 정보가 없거나 별도 문의가 필요합니다.")
    else:
        st.error("객체 크기를 측정하지 못했습니다. 이미지나 설정을 확인해주세요.")

    # --- 중간 결과 이미지 표시 ---
    st.subheader("분석 과정 시각화")
    if result.processed_image is not None:
        # BGR (cv2) -> RGB (PIL) 변환
        img_rgb = cv2.cvtColor(result.processed_image, cv2.COLOR_BGR2RGB)
        pil_to_draw = Image.fromarray(img_rgb)
        
        overlay_img = _draw_detections(pil_to_draw, result.hand_detection, result.object_detection)
        st.image(overlay_img, caption="객체 검출 오버레이", use_container_width=True)
    else:
        st.info("오버레이를 표시할 처리된 이미지가 없습니다.")