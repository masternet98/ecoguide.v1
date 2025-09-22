"""
이미지 분석 처리 컴포넌트 - OpenAI 서비스를 통한 이미지 분석을 담당합니다.
"""
import streamlit as st
from typing import Optional, Tuple
from src.components.base import BaseComponent
from src.app.core.session_state import SessionStateManager
from src.app.core.error_handler import get_error_handler, create_streamlit_error_ui
from src.domains.analysis.services.openai_service import jpeg_bytes_from_image


class ImageAnalysisComponent(BaseComponent):
    """이미지 분석을 처리하는 컴포넌트입니다."""
    
    def render(self, image_bytes: bytes, prompt: str, model: str) -> Tuple[Optional[str], Optional[any]]:
        """
        이미지 분석을 처리합니다.
        
        Args:
            image_bytes: 분석할 이미지 바이트 데이터
            prompt: 분석에 사용할 프롬프트
            model: 사용할 모델명
            
        Returns:
            Tuple[분석 결과 텍스트, 원시 응답]
        """
        # 이미지 표시
        st.image(image_bytes, caption="캡처된 이미지", use_container_width=True)
        
        # 분석 옵션 UI
        max_size = self._render_analysis_options()
        
        # 분석 버튼 및 실행
        if not self._render_analysis_button():
            st.info("사진 분석을 시작하려면 '🧠 이미지 분석' 버튼을 클릭하세요.")
            return None, None
        
        # OpenAI 서비스 유효성 검사
        if not self._validate_openai_service():
            return None, None
        
        # 실제 분석 수행
        return self._perform_analysis(image_bytes, prompt, model, max_size)
    
    def _render_analysis_options(self) -> int:
        """분석 옵션 UI를 렌더링합니다."""
        col1, col2 = st.columns(2)
        with col1:
            max_size = st.number_input(
                "최대 변환 크기 (긴 변, px)",
                min_value=480,
                max_value=1280,
                value=self.config.max_image_size if self.config else 1024,
                step=64,
                key="max_size_input"
            )
        return max_size
    
    def _render_analysis_button(self) -> bool:
        """분석 버튼을 렌더링하고 클릭 상태를 반환합니다."""
        col1, col2 = st.columns(2)
        with col2:
            return st.button("🧠 이미지 분석", use_container_width=True, key="analyze_image_btn")
    
    def _validate_openai_service(self) -> bool:
        """OpenAI 서비스의 유효성을 검사합니다."""
        openai_service = self.get_service('openai_service')
        
        if not openai_service or not openai_service.is_ready():
            st.error("OpenAI 서비스를 사용할 수 없습니다. 설정을 확인해주세요.")
            return False
        
        if not openai_service.has_api_key():
            st.error("OpenAI API Key가 필요합니다. 환경변수 또는 Streamlit secrets에 설정해 주세요.")
            return False
        
        return True
    
    def _perform_analysis(self, image_bytes: bytes, prompt: str, model: str, max_size: int) -> Tuple[Optional[str], Optional[any]]:
        """실제 이미지 분석을 수행합니다."""
        openai_service = self.get_service('openai_service')
        
        try:
            # 이미지 전처리
            with st.spinner("이미지 전처리 중..."):
                jpeg_quality = self.config.jpeg_quality if self.config else 85
                jpeg_bytes = jpeg_bytes_from_image(image_bytes, int(max_size), jpeg_quality)
            
            # LLM 분석
            with st.spinner("LLM 분석 중..."):
                output_text, raw = openai_service.analyze_image(jpeg_bytes, prompt.strip(), model)
                SessionStateManager.update_analysis_results(output_text, raw)
            
            return output_text, raw
            
        except Exception as e:
            error_info = get_error_handler().handle_error(e)
            create_streamlit_error_ui(error_info)
            return None, None