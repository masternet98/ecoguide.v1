"""
메인 레이아웃 컴포넌트 - 사이드바 및 전체 레이아웃을 관리합니다.
"""
import streamlit as st
from src.components.base import BaseComponent
from src.components.status.service_status import ServiceStatusComponent
from src.components.status.feature_status import FeatureStatusComponent
from src.app.core.ui import installation_guide_ui


class MainLayoutComponent(BaseComponent):
    """메인 레이아웃을 관리하는 컴포넌트입니다."""
    
    def __init__(self, app_context):
        super().__init__(app_context)
        self.service_status = ServiceStatusComponent(app_context)
        self.feature_status = FeatureStatusComponent(app_context)
    
    def render_sidebar(self) -> str:
        """
        사이드바를 렌더링하고 선택된 모델을 반환합니다.
        
        Returns:
            선택된 모델명
        """
        with st.sidebar:
            st.header("⚙️ 설정")
            
            # 모델 선택
            model_options = self.config.vision_models if self.config else ["gpt-4o", "gpt-4o-mini"]
            model = st.selectbox("모델 선택", options=model_options, index=0)
            
            # OpenAI 서비스 상태 확인
            self.service_status.render()
            
            # 기능 상태 표시
            self.feature_status.render()
            
            # 설치 가이드 표시
            installation_guide_ui()

            # 관리 페이지 링크
            st.markdown("---")
            st.markdown("### 🛠️ 관리")

            if st.button("🗂️ 폐기물 분류 관리", use_container_width=True):
                st.session_state.show_waste_management = True

            return model
    
    def render_main_header(self) -> None:
        """메인 헤더를 렌더링합니다."""
        st.title("✨ EcoGuide.AI")
        st.caption("버리려는 그 순간, 찰칵! AI가 최적의 방법을 알려드립니다!")
    
    def render(self) -> str:
        """
        전체 레이아웃을 렌더링합니다.
        
        Returns:
            선택된 모델명
        """
        # 메인 헤더
        self.render_main_header()
        
        # 사이드바 렌더링 및 모델 선택 반환
        return self.render_sidebar()