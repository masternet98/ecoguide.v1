"""
서비스 상태 표시 컴포넌트 - OpenAI 서비스 상태를 표시합니다.
"""
import streamlit as st
from src.components.base import BaseComponent


class ServiceStatusComponent(BaseComponent):
    """서비스 상태를 표시하는 컴포넌트입니다."""
    
    def display_openai_service_status(self) -> None:
        """OpenAI 서비스 상태를 표시합니다."""
        try:
            openai_service = self.get_service('openai_service')
            
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
    
    def render(self) -> None:
        """서비스 상태를 렌더링합니다."""
        self.display_openai_service_status()