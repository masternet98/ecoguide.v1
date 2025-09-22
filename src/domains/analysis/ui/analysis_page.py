"""
이미지 분석 페이지 컴포넌트입니다.
기존 app.py의 분석 기능을 모듈화하여 재사용 가능한 형태로 제공합니다.
"""
import streamlit as st
import json
from typing import Optional, Dict, Any

from src.components.base_ui import (
    BaseUIComponent, UIComponent, ImageInputComponent,
    AnalysisResultComponent, AnalysisControlComponent
)
from src.app.core.session_state import SessionStateManager
from src.app.core.error_handler import handle_errors, create_streamlit_error_ui, get_error_handler
from src.domains.analysis.services.openai_service import jpeg_bytes_from_image


class AnalysisPageComponent(BaseUIComponent):
    """이미지 분석 페이지의 메인 컴포넌트입니다."""
    
    def __init__(self):
        super().__init__(UIComponent(
            title="이미지 분석",
            description="LLM을 사용한 이미지 분석 기능을 제공합니다",
            icon="🔍"
        ))
        
        # 하위 컴포넌트 초기화
        self.image_input = ImageInputComponent()
        self.analysis_result = AnalysisResultComponent()
        self.analysis_control = AnalysisControlComponent()
    
    def render(self, app_context, config, model: str) -> None:
        """분석 페이지를 렌더링합니다."""
        st.title(f"✨ {self.info.title}")
        st.caption("Streamlit 카메라로 촬영한 이미지를 Vision LLM으로 분석합니다.")
        
        # 프롬프트 설정 섹션
        self._render_prompt_section()
        
        # 이미지 입력 섹션
        selected_bytes = self.image_input.render()
        
        # 이미지가 없으면 분석 결과 초기화
        if not selected_bytes:
            SessionStateManager.update_analysis_results(None, None)
            st.info("이미지를 선택하면 분석을 진행할 수 있습니다.")
            return
        
        # 이미지 표시
        st.image(selected_bytes, caption="선택된 이미지", use_container_width=True)
        
        # 분석 제어 섹션
        control_result = self.analysis_control.render(
            config=config,
            on_analyze=lambda: self._perform_analysis(
                app_context, selected_bytes, model, config
            )
        )
        
        # 분석 실행
        if control_result["should_analyze"]:
            self._perform_analysis(
                app_context, selected_bytes, model, config, 
                control_result["max_size"]
            )
        
        # 기존 분석 결과 표시
        self._display_existing_results()
    
    def _render_prompt_section(self) -> None:
        """프롬프트 설정 섹션을 렌더링합니다."""
        st.subheader("📝 프롬프트 설정")
        
        default_prompt = (
            "이미지 중앙에 있는 물체가 무엇인지 식별하고, 해당 물체를 가장 적절한 카테고리로 분류해 주세요."
            "분류 결과는 JSON 형식으로 제공해 주세요. 예시: {\\\"object\\\": \\\"의자\\\", \\\"category\\\": \\\"가구\\\"}"
        )
        
        prompt = st.text_area(
            label="입력 프롬프트",
            value=self.get_state("prompt", default_prompt),
            height=100,
            key=self.get_state_key("prompt_input")
        )
        
        # 프롬프트 상태 저장
        self.set_state("prompt", prompt)
    
    @handle_errors(show_user_message=True, reraise=False)
    def _perform_analysis(self, app_context, image_bytes: bytes, model: str, config, max_size: int = None) -> None:
        """이미지 분석을 수행합니다."""
        if max_size is None:
            max_size = config.max_image_size
        
        # OpenAI 서비스 확인
        openai_service = app_context.get_service('openai_service')
        if not openai_service or not openai_service.is_ready():
            st.error("OpenAI 서비스를 사용할 수 없습니다. 설정을 확인해주세요.")
            return
        
        if not openai_service.has_api_key():
            st.error("OpenAI API Key가 필요합니다. 환경변수 또는 Streamlit secrets에 설정해 주세요.")
            return
        
        try:
            # 프롬프트 가져오기
            prompt = self.get_state("prompt", "").strip()
            
            # 이미지 전처리
            with st.spinner("이미지 전처리 중..."):
                jpeg_bytes = jpeg_bytes_from_image(image_bytes, int(max_size), config.jpeg_quality)
            
            # LLM 분석
            with st.spinner("LLM 분석 중..."):
                output_text, raw = openai_service.analyze_image(jpeg_bytes, prompt, model)
                
                # 세션 상태에 결과 저장
                SessionStateManager.update_analysis_results(output_text, raw)
                self.set_state("last_analysis", {
                    "output_text": output_text,
                    "raw_response": raw,
                    "timestamp": st.session_state.get("timestamp", "")
                })
            
            st.success("✅ 분석이 완료되었습니다!")
            
        except Exception as e:
            error_info = get_error_handler().handle_error(e)
            create_streamlit_error_ui(error_info)
    
    def _display_existing_results(self) -> None:
        """기존 분석 결과를 표시합니다."""
        last_analysis = self.get_state("last_analysis")
        
        if last_analysis:
            self.analysis_result.render(last_analysis)


class PromptTemplateComponent(BaseUIComponent):
    """프롬프트 템플릿 관리 컴포넌트입니다."""
    
    def __init__(self):
        super().__init__(UIComponent(
            title="프롬프트 템플릿",
            description="사전 정의된 프롬프트 템플릿을 관리합니다",
            icon="📋"
        ))
        
        # 기본 템플릿들
        self.templates = {
            "기본 분석": (
                "이미지 중앙에 있는 물체가 무엇인지 식별하고, 해당 물체를 가장 적절한 카테고리로 분류해 주세요."
                "분류 결과는 JSON 형식으로 제공해 주세요. 예시: {\\\"object\\\": \\\"의자\\\", \\\"category\\\": \\\"가구\\\"}"
            ),
            "폐기물 분류": (
                "이 이미지의 물체를 대형폐기물 관점에서 분석해주세요. "
                "물체의 종류, 재질, 예상 크기, 폐기 방법을 JSON 형식으로 제공해주세요. "
                "예시: {\\\"object\\\": \\\"의자\\\", \\\"material\\\": \\\"목재\\\", \\\"category\\\": \\\"가구\\\", \\\"disposal_method\\\": \\\"대형폐기물 신고\\\"}"
            ),
            "상세 분석": (
                "이미지를 자세히 분석하여 다음 정보를 JSON 형식으로 제공해주세요:\\n"
                "1. 물체의 정확한 명칭\\n"
                "2. 주요 특징 (색상, 재질, 상태)\\n"
                "3. 용도 및 카테고리\\n"
                "4. 크기 추정 (작음/보통/큰/매우큰)\\n"
                "예시: {\\\"object\\\": \\\"소파\\\", \\\"features\\\": \\\"갈색 가죽, 3인용\\\", \\\"category\\\": \\\"가구\\\", \\\"size\\\": \\\"큰\\\"}"
            )
        }
    
    def render(self) -> str:
        """프롬프트 템플릿 선택기를 렌더링합니다."""
        with st.expander("📋 프롬프트 템플릿", expanded=False):
            selected_template = st.selectbox(
                "템플릿 선택",
                options=list(self.templates.keys()),
                key=self.get_state_key("template_selector")
            )
            
            if st.button("템플릿 적용", key=self.get_state_key("apply_template")):
                return self.templates[selected_template]
            
            # 선택된 템플릿 미리보기
            st.text_area(
                "선택된 템플릿 미리보기",
                value=self.templates[selected_template],
                height=100,
                disabled=True,
                key=self.get_state_key("template_preview")
            )
        
        return ""


class EnhancedAnalysisPageComponent(AnalysisPageComponent):
    """확장된 분석 페이지 컴포넌트입니다."""
    
    def __init__(self):
        super().__init__()
        self.prompt_template = PromptTemplateComponent()
    
    def _render_prompt_section(self) -> None:
        """확장된 프롬프트 설정 섹션을 렌더링합니다."""
        st.subheader("📝 프롬프트 설정")
        
        # 템플릿 적용
        applied_template = self.prompt_template.render()
        
        default_prompt = applied_template or (
            "이미지 중앙에 있는 물체가 무엇인지 식별하고, 해당 물체를 가장 적절한 카테고리로 분류해 주세요."
            "분류 결과는 JSON 형식으로 제공해 주세요. 예시: {\\\"object\\\": \\\"의자\\\", \\\"category\\\": \\\"가구\\\"}"
        )
        
        prompt = st.text_area(
            label="입력 프롬프트",
            value=applied_template or self.get_state("prompt", default_prompt),
            height=120,
            key=self.get_state_key("prompt_input"),
            help="분석에 사용할 프롬프트를 입력하거나 위의 템플릿을 활용하세요."
        )
        
        # 프롬프트 상태 저장
        self.set_state("prompt", prompt)