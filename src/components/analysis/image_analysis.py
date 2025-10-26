"""
이미지 분석 처리 컴포넌트 - OpenAI 서비스를 통한 이미지 분석을 담당합니다.

Refactored to be a pure logic component without any direct UI rendering.
The calling UI component is responsible for spinners, buttons, and options.
"""
import streamlit as st
from typing import Optional, Tuple
from src.components.base import BaseComponent
from src.app.core.session_state import SessionStateManager
from src.app.core.error_handler import get_error_handler, create_streamlit_error_ui
from src.domains.analysis.services.openai_service import jpeg_bytes_from_image


class ImageAnalysisComponent(BaseComponent):
    """이미지 분석 로직을 처리하는 컴포넌트입니다."""

    def execute_analysis(self, image_bytes: bytes, prompt: str, model: str, max_size: int) -> Tuple[Optional[str], Optional[any]]:
        """
        이미지 분석의 전체 로직을 실행합니다.
        
        Args:
            image_bytes: 분석할 이미지 바이트 데이터
            prompt: 분석에 사용할 프롬프트
            model: 사용할 모델명
            max_size: 이미지 최대 변환 크기
            
        Returns:
            Tuple[분석 결과 텍스트, 원시 응답]
        """
        # 1. OpenAI 서비스 유효성 검사
        if not self._validate_openai_service():
            return None, None
        
        # 2. 실제 분석 수행
        try:
            # 이미지 전처리
            jpeg_quality = self.config.jpeg_quality if self.config else 85
            jpeg_bytes = jpeg_bytes_from_image(image_bytes, int(max_size), jpeg_quality)
            
            # LLM 분석
            openai_service = self.get_service('openai_service')
            output_text, raw = openai_service.analyze_image(jpeg_bytes, prompt.strip(), model)
            SessionStateManager.update_analysis_results(output_text, raw)
            
            return output_text, raw
            
        except Exception as e:
            error_info = get_error_handler().handle_error(e)
            create_streamlit_error_ui(error_info)
            return None, None

    def _validate_openai_service(self) -> bool:
        """OpenAI 서비스의 유효성을 검사하고, 실패 시 UI에 오류를 표시합니다."""
        openai_service = self.get_service('openai_service')
        
        if not openai_service or not openai_service.is_ready():
            st.error("OpenAI 서비스를 사용할 수 없습니다. 설정을 확인해주세요.")
            return False
        
        if not openai_service.has_api_key():
            st.error("OpenAI API Key가 필요합니다. 환경변수 또는 Streamlit secrets에 설정해 주세요.")
            return False
        
        return True
