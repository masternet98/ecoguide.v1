"""
Streamlit 애플리케이션의 메인 파일입니다.

새로운 아키텍처를 적용한 버전으로, 컴포넌트 기반 구조를 사용하여
더 나은 확장성과 유지보수성을 제공합니다.
"""
import streamlit as st

from src.app.core.app_factory import get_application
from src.app.core.session_state import SessionStateManager
from src.app.core.error_handler import handle_errors, create_streamlit_error_ui, get_error_handler
from src.layouts.main_layout import MainLayoutComponent
from src.pages.camera_analysis import CameraAnalysisPage


@handle_errors(show_user_message=True, reraise=False)
def main():
    """애플리케이션의 메인 함수입니다."""
    # 페이지별 설정
    st.set_page_config(
        page_title="EcoGuide.AI", 
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
    SessionStateManager.init_location_state()
    
    # 레이아웃 및 페이지 컴포넌트 초기화
    layout = MainLayoutComponent(app_context)
    page = CameraAnalysisPage(app_context)
    
    # 레이아웃 렌더링 (사이드바 포함)
    selected_model = layout.render()
    
    # 메인 페이지 렌더링
    page.render(selected_model)


if __name__ == "__main__":
    main()