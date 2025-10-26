"""
카메라 분석 페이지 - 메인 페이지의 비즈니스 로직을 담당합니다.
"""
import streamlit as st
from src.components.base import BaseComponent
from src.domains.analysis.ui.analysis_interface import AnalysisInterfaceComponent
from src.domains.analysis.ui.waste_types_management import WasteTypesManagementComponent


class CameraAnalysisPage(BaseComponent):
    """카메라 분석 페이지를 관리하는 컴포넌트입니다."""
    
    def __init__(self, app_context):
        super().__init__(app_context)
        self.analysis_interface = AnalysisInterfaceComponent(app_context)
        self.waste_management = WasteTypesManagementComponent(app_context)
    
    def render_main_content(self, model: str) -> None:
        """
        메인 콘텐츠를 렌더링합니다.

        Args:
            model: 선택된 모델명
        """
        # 메인 분석 UI
        self.analysis_interface.render(model)

    def render(self, model: str) -> None:
        """
        페이지를 렌더링합니다.

        Args:
            model: 선택된 모델명
        """
        # 관리 페이지 표시 여부 확인
        if getattr(st.session_state, 'show_waste_management', False):
            st.button("◀️ 메인으로 돌아가기", key="back_to_main", on_click=lambda: setattr(st.session_state, 'show_waste_management', False))
            st.markdown("---")
            self.waste_management.render()
        else:
            self.render_main_content(model)