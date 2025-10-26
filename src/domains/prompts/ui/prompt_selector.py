"""
프롬프트 선택 UI 컴포넌트 - 사용자가 프롬프트를 선택할 수 있는 UI를 제공합니다.
"""
import streamlit as st
from src.components.base import BaseComponent


class PromptSelectorComponent(BaseComponent):
    """프롬프트 선택 UI를 제공하는 컴포넌트입니다."""

    def render(self, feature_id: str) -> str:
        """
        프롬프트 선택 UI를 렌더링합니다.

        Args:
            feature_id: 기능 ID

        Returns:
            선택된 프롬프트 텍스트 또는 빈 문자열
        """
        try:
            prompt_service = self.get_service('prompt_service')
            if not prompt_service:
                return ""

            # 기능에 매핑된 프롬프트들 가져오기
            available_prompts = prompt_service.get_prompts_for_feature(feature_id)

            if not available_prompts:
                st.info("이 기능에 등록된 관리 프롬프트가 없습니다. 기본 프롬프트를 사용합니다.")
                return ""

            # 프롬프트 선택 UI
            selected_prompt_text = self._render_prompt_selection_ui(feature_id, available_prompts, prompt_service)
            return selected_prompt_text or ""

        except Exception as e:
            st.warning(f"프롬프트 선택 UI 오류: {e}")
            return ""

    def _render_prompt_selection_ui(self, feature_id: str, available_prompts, prompt_service) -> str:
        """
        프롬프트 선택 UI를 렌더링합니다.

        Returns:
            선택된 프롬프트 텍스트
        """
        with st.expander("🎯 관리 프롬프트 선택", expanded=False):
            prompt_options = {"": "직접 입력"}
            enhanced_waste_analysis_id = None

            for prompt in available_prompts:
                prompt_options[prompt.id] = f"{prompt.name} ({prompt.category.value})"
                # enhanced_waste_analysis 프롬프트 ID 저장
                if prompt.name == "enhanced_waste_analysis":
                    enhanced_waste_analysis_id = prompt.id

            selected_prompt_key = f"selected_prompt_{feature_id}"

            # enhanced_waste_analysis가 있으면 기본값으로 설정
            default_index = 0
            if enhanced_waste_analysis_id and enhanced_waste_analysis_id in prompt_options:
                default_index = list(prompt_options.keys()).index(enhanced_waste_analysis_id)

            selected_prompt_id = st.selectbox(
                "프롬프트 선택",
                options=list(prompt_options.keys()),
                index=default_index,
                format_func=lambda x: prompt_options[x],
                key=selected_prompt_key,
                help="관리 프롬프트를 선택하거나 직접 입력을 선택하세요."
            )

            # 선택된 프롬프트 정보 표시 및 텍스트 반환
            if selected_prompt_id:
                selected_prompt_text = self._display_selected_prompt_info(selected_prompt_id, prompt_service)
                return selected_prompt_text

            return ""
    
    def _display_selected_prompt_info(self, selected_prompt_id: str, prompt_service) -> str:
        """
        선택된 프롬프트의 정보를 표시하고 프롬프트 텍스트를 반환합니다.

        Returns:
            선택된 프롬프트의 템플릿 텍스트
        """
        selected_prompt = prompt_service.get_prompt(selected_prompt_id)
        if selected_prompt:
            st.write(f"**설명:** {selected_prompt.description}")

            if selected_prompt.variables:
                st.write(f"**변수:** {', '.join(selected_prompt.variables)}")
                st.info("이 프롬프트는 변수를 포함하고 있습니다. 필요한 경우 하단에서 직접 수정하세요.")

            # 프롬프트 미리보기
            with st.expander("미리보기"):
                st.code(selected_prompt.template)

            # 선택된 프롬프트의 템플릿 텍스트 반환
            return selected_prompt.template

        return ""