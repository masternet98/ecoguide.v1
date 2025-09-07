"""
Streamlit 애플리케이션의 메인 파일입니다.

새로운 아키텍처를 적용한 버전으로, 서비스 팩토리와 기능 레지스트리를
사용하여 더 나은 확장성과 유지보수성을 제공합니다.
"""
import streamlit as st
import json
from typing import Optional

from src.core.app_factory import get_application
from src.core.session_state import SessionStateManager
from src.core.error_handler import handle_errors, create_streamlit_error_ui, get_error_handler
from src.services.openai_service import jpeg_bytes_from_image
from src.core.ui import installation_guide_ui


@handle_errors(show_user_message=True, reraise=False)
def main():
    """애플리케이션의 메인 함수입니다."""
    # 페이지별 설정
    st.set_page_config(
        page_title="카메라 - LLM 이미지 분석", 
        page_icon="📷", 
        layout="centered"
    )
    
    # 애플리케이션 컨텍스트 초기화
    try:
        app_context = get_application()
    except Exception as e:
        st.error("애플리케이션 초기화에 실패했습니다.")
        create_streamlit_error_ui(
            get_error_handler().handle_error(e)
        )
        st.stop()
    
    # 체계적인 세션 상태 관리
    SessionStateManager.init_image_state()
    SessionStateManager.init_ui_state()
    
    # 설정
    config = app_context.config
    
    st.title("✨ 카메라 - LLM 이미지 분석")
    st.caption("Streamlit 카메라로 촬영한 이미지를 Vision LLM으로 분석합니다.")
    
    with st.sidebar:
        st.header("⚙️ 설정")
        model = st.selectbox("모델 선택", options=config.vision_models, index=0)
        
        # OpenAI 서비스 상태 확인
        display_openai_service_status(app_context)
        
        # 기능 상태 표시
        display_feature_status(app_context)
        
        # 설치 가이드 표시
        installation_guide_ui()
    
    # 메인 분석 UI
    render_analysis_interface(app_context, config, model)


def display_openai_service_status(app_context):
    """OpenAI 서비스 상태를 표시합니다."""
    try:
        openai_service = app_context.get_service('openai_service')
        
        if openai_service and openai_service.is_ready():
            if openai_service.has_api_key():
                st.success("✅ OpenAI API 키가 설정되었습니다")
            else:
                st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다")
                st.info("환경변수 또는 Streamlit secrets에 OPENAI_API_KEY를 설정하세요")
        else:
            st.error("❌ OpenAI 서비스를 초기화할 수 없습니다")
            
    except Exception as e:
        st.error(f"OpenAI 서비스 상태 확인 실패: {e}")


def display_feature_status(app_context):
    """활성화된 기능들의 상태를 표시합니다."""
    with st.expander("🔧 기능 상태"):
        features = app_context.feature_registry.list_features()
        
        for feature in features:
            status_emoji = "✅" if feature.status.value == "enabled" else "⏸️"
            st.write(f"{status_emoji} {feature.display_name}: {feature.status.value}")
            
            if feature.error_message:
                st.error(f"오류: {feature.error_message}")


def render_analysis_interface(app_context, config, model):
    """이미지 분석 인터페이스를 렌더링합니다."""
    
    # 프롬프트 설정
    prompt = (
        "이미지 중앙에 있는 물체가 무엇인지 식별하고, 해당 물체를 가장 적절한 카테고리로 분류해 주세요."
        "분류 결과는 JSON 형식으로 제공해 주세요. 예시: {\"object\": \"의자\", \"category\": \"가구\"}"
    )
    
    st.subheader("📝 프롬프트 설정")
    prompt = st.text_area(label="입력 프롬프트", value=prompt, height=100, key="prompt_input")
    
    # 탭 선택 및 전환 감지
    tab_selector = st.radio("탭 선택", ["📷 카메라", "🖼️ 갤러리"], index=0)
    SessionStateManager.handle_tab_switch(tab_selector)
    
    # 이미지 입력 처리
    selected_bytes = handle_image_input(tab_selector)
    
    # 선택된 이미지가 없으면 분석 결과 초기화
    if not selected_bytes:
        SessionStateManager.update_analysis_results(None, None)
        return
    
    # 이미지 분석 처리
    handle_image_analysis(app_context, selected_bytes, prompt, model, config)


def handle_image_input(tab_selector: str) -> Optional[bytes]:
    """이미지 입력을 처리하고 바이트 데이터를 반환합니다."""
    
    if tab_selector == "📷 카메라":
        st.info("아래 카메라 버튼으로 사진을 촬영하세요.")
        camera_photo = st.camera_input("사진 촬영", key=f"camera_input_{tab_selector}")
        
        if camera_photo:
            SessionStateManager.update_image_bytes("camera", camera_photo.getvalue())
            return camera_photo.getvalue()
    
    elif tab_selector == "🖼️ 갤러리":
        gallery_photo = st.file_uploader(
            "사진 파일을 업로드하세요", 
            type=["png", "jpg", "jpeg"], 
            key=f"gallery_uploader_{tab_selector}"
        )
        
        if gallery_photo:
            SessionStateManager.update_image_bytes("gallery", gallery_photo.getvalue())
            return gallery_photo.getvalue()
    
    # 세션 상태에서 이미지 가져오기
    return SessionStateManager.get_selected_image_bytes(tab_selector)


@handle_errors(show_user_message=True, reraise=False)
def handle_image_analysis(app_context, image_bytes: bytes, prompt: str, model: str, config):
    """이미지 분석을 처리합니다."""
    
    # 이미지 표시
    image_ph = st.empty()
    result_ph = st.empty()
    image_ph.image(image_bytes, caption="캡처된 이미지", use_container_width=True)
    
    # 분석 옵션
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
        return
    
    # OpenAI 서비스 가져오기
    openai_service = app_context.get_service('openai_service')
    if not openai_service or not openai_service.is_ready():
        st.error("OpenAI 서비스를 사용할 수 없습니다. 설정을 확인해주세요.")
        return
    
    if not openai_service.has_api_key():
        st.error("OpenAI API Key가 필요합니다. 환경변수 또는 Streamlit secrets에 설정해 주세요.")
        return
    
    try:
        # 이미지 전처리
        with st.spinner("이미지 전처리 중..."):
            jpeg_bytes = jpeg_bytes_from_image(image_bytes, int(max_size), config.jpeg_quality)
        
        # LLM 분석
        with st.spinner("LLM 분석 중..."):
            output_text, raw = openai_service.analyze_image(jpeg_bytes, prompt.strip(), model)
            SessionStateManager.update_analysis_results(output_text, raw)
        
        # 분석 결과 표시
        display_analysis_results(result_ph, output_text, raw)
        
    except Exception as e:
        error_info = get_error_handler().handle_error(e)
        create_streamlit_error_ui(error_info)


def display_analysis_results(result_container, output_text: Optional[str], raw_response):
    """분석 결과를 표시합니다."""
    
    with result_container.container():
        st.subheader("📝 분석 결과")
        
        if output_text:
            try:
                # JSON 파싱 시도
                parsed_output = json.loads(output_text)
                object_name = parsed_output.get("object", "알 수 없음")
                category = parsed_output.get("category", "알 수 없음")
                st.write(f"**물체:** {object_name}")
                st.write(f"**카테고리:** {category}")
                
            except json.JSONDecodeError:
                st.warning("⚠️ JSON 형식이 아닌 응답입니다.")
                st.write(output_text)
                
            except Exception as e:
                st.error(f"응답 처리 중 오류 발생: {e}")
                st.write(output_text)
        else:
            st.info("모델에서 직접적인 텍스트 응답을 찾지 못했습니다.")
        
        # 원시 응답 표시
        with st.expander("🔍 원시 응답(JSON) 보기"):
            try:
                st.json(raw_response)
            except Exception:
                st.code(str(raw_response))


if __name__ == "__main__":
    main()