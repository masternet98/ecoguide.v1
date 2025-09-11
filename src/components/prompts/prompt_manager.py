"""
프롬프트 관리 컴포넌트 - 관리되는 프롬프트를 가져오고 관리합니다.
"""
import streamlit as st
from typing import Optional
from src.components.base import BaseComponent


class PromptManagerComponent(BaseComponent):
    """프롬프트를 관리하는 컴포넌트입니다."""
    
    def render(self, **kwargs) -> None:
        """
        이 컴포넌트는 직접 렌더링하지 않고 다른 컴포넌트에서 사용됩니다.
        """
        pass
    
    def get_managed_prompt(self, feature_id: str, fallback_prompt: str) -> str:
        """
        관리되는 프롬프트를 가져옵니다.
        
        Args:
            feature_id: 기능 ID
            fallback_prompt: 폴백 프롬프트
            
        Returns:
            사용할 프롬프트 문자열
        """
        try:
            prompt_service = self.get_service('prompt_service')
            if not prompt_service:
                return fallback_prompt
            
            # 세션 상태에서 선택된 프롬프트 확인
            selected_prompt_key = f"selected_prompt_{feature_id}"
            if selected_prompt_key in st.session_state:
                prompt_id = st.session_state[selected_prompt_key]
                if prompt_id:
                    rendered_prompt = prompt_service.render_prompt(prompt_id)
                    if rendered_prompt:
                        return rendered_prompt
            
            # 기본 프롬프트 가져오기
            default_prompt = prompt_service.get_default_prompt_for_feature(feature_id)
            if default_prompt:
                return prompt_service.render_prompt(default_prompt.id) or fallback_prompt
            
            return fallback_prompt
            
        except Exception:
            # 오류 발생시 폴백 프롬프트 사용
            return fallback_prompt