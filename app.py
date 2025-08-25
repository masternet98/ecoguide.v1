"""
Streamlit 애플리케이션의 메인 파일입니다.

이 파일은 애플리케이션의 진입점 역할을 하며, 데모 페이지의 전체 UI와
핵심 로직을 포함합니다. 다른 페이지들은 `pages` 디렉터리에서 관리됩니다.
"""
import streamlit as st
import numpy as np
import json
from src.core.utils import resolve_api_key, get_app_state
from src.core.config import load_config
from src.services.openai_service import jpeg_bytes_from_image, analyze_image_with_openai
from src.core.ui import installation_guide_ui
from src.components.measure_ui import render_measure_ui
 
def main():
    """애플리케이션의 메인 함수입니다."""
    # 페이지별 설정
    st.set_page_config(page_title="카메라 - LLM 이미지 분석", page_icon="📷", layout="centered")

    # Initialize separate session state keys for camera and gallery images so they persist independently
    if 'camera_photo_bytes' not in st.session_state:
        st.session_state.camera_photo_bytes = None
    if 'gallery_photo_bytes' not in st.session_state:
        st.session_state.gallery_photo_bytes = None
    # last_photo_source tracks which source (camera/gallery) was most recently set by the user
    if 'last_photo_source' not in st.session_state:
        st.session_state.last_photo_source = None
    # prev_active_tab tracks the previously active tab so we can detect tab switches
    if 'prev_active_tab' not in st.session_state:
        st.session_state.prev_active_tab = None
    # analysis results persisted so they can be cleared on tab switch
    if 'analysis_output' not in st.session_state:
        st.session_state.analysis_output = None
    if 'analysis_raw' not in st.session_state:
        st.session_state.analysis_raw = None

    # 전역 설정 로드
    config = load_config()

    # 앱 상태 가져오기 (config 객체 전달)
    app_state = get_app_state(config=config)

    st.title("✨ 카메라 - LLM 이미지 분석")
    st.caption("Streamlit 카메라로 촬영한 이미지를 Vision LLM으로 분석합니다.")

    with st.sidebar:
        st.header("⚙️ 설정")
        model = st.selectbox("모델 선택", options=config.vision_models, index=0)
        api_key_input = st.text_input(
            "OpenAI API Key", type="password", value=resolve_api_key() or "",
            placeholder="sk-...", help="환경변수 또는 Streamlit secrets 사용을 권장합니다."
        )
        installation_guide_ui()

    # --- 데모 페이지 로직 시작 ---
    prompt = (
       "이미지 중앙에 있는 물체가 무엇인지 식별하고, 해당 물체를 가장 적절한 카테고리로 분류해 주세요."
       "분류 결과는 JSON 형식으로 제공해 주세요. 예시: {\"object\": \"의자\", \"category\": \"가구\"}"
    )
    
    st.subheader("📝 프롭프트 설정")
    st.text_area(label="입력 프롬프트", value=prompt, height=100, key="prompt_input")

    # Use a selectable control to detect active tab and allow clearing on switch
    tab_selector = st.radio("탭 선택", ["📷 카메라", "🖼️ 갤러리"], index=0)
    # Detect tab changes by comparing to prev_active_tab stored in session_state.
    prev_tab = st.session_state.get("prev_active_tab")
    if prev_tab is None:
        st.session_state.prev_active_tab = tab_selector
    elif prev_tab != tab_selector:
        # Clear images and analysis results on tab switch
        st.session_state.camera_photo_bytes = None
        st.session_state.gallery_photo_bytes = None
        st.session_state.last_photo_source = None
        st.session_state.analysis_output = None
        st.session_state.analysis_raw = None
        st.session_state.prev_active_tab = tab_selector
        # Try to force a UI rerun so widgets reset immediately. Use experimental_rerun if available,
        # otherwise toggle a session key to cause Streamlit to re-render.
        try:
            rerun_fn = getattr(st, "experimental_rerun", None)
            if callable(rerun_fn):
                rerun_fn()
            else:
                st.session_state["_tab_rerun_toggle"] = not st.session_state.get("_tab_rerun_toggle", False)
        except Exception:
            pass

    if tab_selector == "📷 카메라":
        # mark this tab as active (already set above)
        # 단순화된 카메라 UI: 활성화 토글 제거하고 항상 카메라 입력을 표시합니다.
        st.info("아래 카메라 버튼으로 사진을 촬영하세요.")
        # use a tab-scoped key so the camera widget does not preserve its value across tab switches
        camera_photo = st.camera_input("사진 촬영", key=f"camera_input_{tab_selector}")
        if camera_photo:
            # store raw bytes from camera input so it persists in session_state across reruns
            st.session_state.camera_photo_bytes = camera_photo.getvalue()
            # remember the last source so main UI shows the intended photo after tab switches
            st.session_state.last_photo_source = "camera"
        # If camera_photo is None, we don't overwrite st.session_state.camera_photo_bytes

    elif tab_selector == "🖼️ 갤러리":
        # use a tab-scoped key so the uploader widget does not preserve its value across tab switches
        gallery_photo = st.file_uploader("사진 파일을 업로드하세요", type=["png", "jpg", "jpeg"], key=f"gallery_uploader_{tab_selector}")
        if gallery_photo:
            # store raw bytes from uploader so it persists in session_state across reruns
            st.session_state.gallery_photo_bytes = gallery_photo.getvalue()
            # remember the last source so main UI shows the intended photo after tab switches
            st.session_state.last_photo_source = "gallery"
        # If gallery_photo is None, we don't overwrite st.session_state.gallery_photo_bytes

    # with tab_measure:
    #     # 측정 UI를 렌더링하고, 측정 탭을 선택한 경우 이후 기본 분석 흐름을 중단합니다.
    #     render_measure_ui()

    selected_bytes = None
    if tab_selector == "📷 카메라":
        selected_bytes = st.session_state.get("camera_photo_bytes")
    elif tab_selector == "🖼️ 갤러리":
        selected_bytes = st.session_state.get("gallery_photo_bytes")

    # Clear analysis results if no photo is selected for the current tab
    if not selected_bytes:
        st.session_state.analysis_output = None
        st.session_state.analysis_raw = None

    if selected_bytes:
        # placeholders so we can explicitly clear the image and results when needed
        image_ph = st.empty()
        result_ph = st.empty()
        image_ph.image(selected_bytes, caption="캡처된 이미지", use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            max_size = st.number_input(
                "최대 변환 크기 (긴 변, px)",
                min_value=480,
                max_value=1280,
                value=config.max_image_size,
                step=64,
                key="max_size_input"
            )
        with col2:
            analyze_now = st.button("🧠 이미지 분석", use_container_width=True, key="analyze_image_btn")

        if not analyze_now:
            st.info("사진 분석을 시작하려면 '🧠 이미지 분석' 버튼을 클릭하세요.")
            st.stop()

        # Prefer explicit sidebar input (api_key_input). If empty, fallback to resolve_api_key().
        api_key_value = api_key_input.strip() if (api_key_input and api_key_input.strip()) else (resolve_api_key() or "")
        if not api_key_value:
            st.error("OpenAI API Key가 필요합니다. 사이드바에 입력해 주세요.")
            st.stop()

        try:
            with st.spinner("이미지 전처리 중..."):
                jpeg_bytes = jpeg_bytes_from_image(selected_bytes, int(max_size), config.jpeg_quality)

            with st.spinner("LLM 분석 중..."):
                output_text, raw = analyze_image_with_openai(
                    jpeg_bytes, prompt.strip(), model, api_key_value.strip()
                )
                # persist analysis result to session so it can be cleared on tab switches
                st.session_state.analysis_output = output_text
                st.session_state.analysis_raw = raw

            # Render analysis results into a contained area so we can reliably clear it.
            result_container = result_ph.container()
            result_container.subheader("📝 분석 결과")
            if output_text:
                try:
                    parsed_output = json.loads(output_text)
                    object_name = parsed_output.get("object", "알 수 없음")
                    category = parsed_output.get("category", "알 수 없음")
                    result_container.write(f"**물체:** {object_name}")
                    result_container.write(f"**카테고리:** {category}")
                except json.JSONDecodeError:
                    result_container.error("LLM 응답이 유효한 JSON 형식이 아닙니다. 원시 응답을 확인해 주세요.")
                    result_container.write(output_text)  # Display raw text if JSON parsing fails
                except Exception as e:
                    result_container.error(f"LLM 응답 처리 중 오류 발생: {e}")
                    result_container.write(output_text)  # Display raw text on other errors
            else:
                result_container.info("모델에서 직접적인 텍스트 응답을 찾지 못했습니다. 아래 원시 응답을 확인해 주세요.")
    
            # Show raw response inside an expander attached to the same container.
            try:
                exp = result_container.expander("🔍 원시 응답(JSON) 보기")
                try:
                    exp.json(st.session_state.get("analysis_raw", raw))
                except Exception:
                    exp.code(str(st.session_state.get("analysis_raw", raw)))
            except Exception:
                # Fallback: write raw as text if expander/json fails
                result_container.write(str(st.session_state.get("analysis_raw", raw)))

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
    else:
        st.info("사진을 촬영하거나 업로드하면 LLM이 분석을 시작합니다.")
    # --- 데모 페이지 로직 끝 ---


if __name__ == "__main__":
    main()
