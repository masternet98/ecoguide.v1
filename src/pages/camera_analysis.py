"""
카메라 분석 페이지 - 메인 페이지의 비즈니스 로직을 담당합니다.
"""
import streamlit as st
from src.components.base import BaseComponent
from src.domains.analysis.ui.analysis_interface import AnalysisInterfaceComponent
from src.domains.prompts.ui.prompt_initializer import PromptInitializerComponent


class CameraAnalysisPage(BaseComponent):
    """카메라 분석 페이지를 관리하는 컴포넌트입니다."""
    
    def __init__(self, app_context):
        super().__init__(app_context)
        self.analysis_interface = AnalysisInterfaceComponent(app_context)
        self.prompt_initializer = PromptInitializerComponent(app_context)
    
    def render_main_content(self, model: str) -> None:
        """
        메인 콘텐츠를 렌더링합니다.
        
        Args:
            model: 선택된 모델명
        """
        # 프롬프트 서비스 초기화 (기본 프롬프트 생성)
        self._initialize_prompts()
        
        # 메인 분석 UI
        self.analysis_interface.render(model)
    
    def _initialize_prompts(self) -> None:
        """프롬프트 서비스를 초기화합니다."""
        prompt_service = self.get_service('prompt_service')
        if prompt_service:
            self.prompt_initializer.initialize_default_prompts(prompt_service)
    
    def render(self, model: str) -> None:
        """
        페이지를 렌더링합니다.
        
        Args:
            model: 선택된 모델명
        """
        self.render_main_content(model)