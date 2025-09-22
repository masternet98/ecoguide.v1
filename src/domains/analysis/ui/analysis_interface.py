"""
분석 인터페이스 컴포넌트 - 전체 이미지 분석 인터페이스를 통합 관리합니다.
"""
import streamlit as st
from src.components.base import BaseComponent
from src.app.core.prompt_feature_decorators import prompt_feature
from src.domains.analysis.ui.image_input import ImageInputComponent
from src.domains.analysis.ui.image_analysis import ImageAnalysisComponent
from src.domains.analysis.ui.results_display import ResultsDisplayComponent
from src.domains.prompts.ui.prompt_manager import PromptManagerComponent
from src.domains.prompts.ui.prompt_selector import PromptSelectorComponent
from src.domains.district.ui.location_selector import LocationSelectorComponent
from src.app.core.session_state import SessionStateManager


@prompt_feature(
    feature_id="analysis_interface",
    name="분석 인터페이스",
    description="이미지 분석을 위한 통합 인터페이스 컴포넌트",
    category="interface",
    required_services=["openai_service", "prompt_service"],
    default_prompt_template="이미지를 분석하여 다음 정보를 JSON 형식으로 제공해주세요: 1) 물체의 이름 2) 물체의 카테고리 3) 주요 특징 4) 크기 추정",
    metadata={"component_type": "interface", "ui_type": "streamlit"}
)
class AnalysisInterfaceComponent(BaseComponent):
    """이미지 분석 인터페이스를 통합 관리하는 컴포넌트입니다."""
    
    def __init__(self, app_context):
        super().__init__(app_context)
        self.image_input = ImageInputComponent(app_context)
        self.image_analysis = ImageAnalysisComponent(app_context)
        self.results_display = ResultsDisplayComponent(app_context)
        self.prompt_manager = PromptManagerComponent(app_context)
        self.prompt_selector = PromptSelectorComponent(app_context)
        self.location_selector = LocationSelectorComponent(app_context)
    
    def render(self, model: str) -> None:
        """
        이미지 분석 인터페이스를 렌더링합니다.

        Args:
            model: 사용할 모델명
        """
        # 위치 선택 UI 먼저 렌더링
        location_selected = self.location_selector.render()

        # # 위치 정보 요약 표시 (위치가 선택된 경우)
        # location_summary = SessionStateManager.get_current_location_summary()
        # if location_summary:
        #     st.info(f"📍 **선택된 위치**: {location_summary}")

        st.markdown("---")  # 구분선 추가

        # 프롬프트 관리 시스템 사용
        default_prompt = self.config.default_prompt if self.config else ""
        prompt = self.prompt_manager.get_managed_prompt("camera_analysis", default_prompt)

        # 위치 정보가 있으면 프롬프트에 위치 컨텍스트 추가
        if location_selected and location_selected.get('success'):
            location_data = location_selected['data']
            sido = location_data.get('sido', '')
            sigungu = location_data.get('sigungu', '')
            if sido and sigungu:
                location_context = f"\n\n[위치 정보: {sido} {sigungu} 지역]"
                prompt = prompt + location_context

        st.subheader("📝 프롬프트 설정")

        # 관리되는 프롬프트 선택 UI
        self.prompt_selector.render("camera_analysis")

        # 프롬프트 입력/편집 UI
        prompt = st.text_area(label="입력 프롬프트", value=prompt, height=100, key="prompt_input")
        
        # 탭 선택 및 전환 감지
        tab_selector = st.radio("탭 선택", ["📷 카메라", "🖼️ 갤러리"], index=0)
        SessionStateManager.handle_tab_switch(tab_selector)
        
        # 이미지 입력 처리
        selected_bytes = self.image_input.render(tab_selector)
        
        # 선택된 이미지가 없으면 분석 결과 초기화
        if not selected_bytes:
            SessionStateManager.update_analysis_results(None, None)
            return
        
        # 이미지 분석 처리 (버튼 포함)
        output_text, raw_response = self.image_analysis.render(selected_bytes, prompt, model)
        
        # 분석 결과 표시 (분석 버튼 아래에 확장형으로 표시)
        if output_text is not None or raw_response is not None:
            st.markdown("---")  # 구분선 추가
            self.results_display.render(st, output_text, raw_response)