"""
기능 상태 표시 컴포넌트 - 활성화된 기능들의 상태를 표시합니다.
"""
import streamlit as st
from src.components.base import BaseComponent


class FeatureStatusComponent(BaseComponent):
    """기능 상태를 표시하는 컴포넌트입니다."""
    
    def display_feature_status(self) -> None:
        """활성화된 기능들의 상태를 표시합니다."""
        with st.expander("🔧 기능 상태"):
            if not self.app_context or not hasattr(self.app_context, 'feature_registry'):
                st.info("기능 레지스트리를 사용할 수 없습니다.")
                return
            
            features = self.app_context.feature_registry.list_features()
            
            for feature in features:
                status_emoji = "✅" if feature.status.value == "enabled" else "⏸️"
                st.write(f"{status_emoji} {feature.display_name}: {feature.status.value}")
                
                if feature.error_message:
                    st.error(f"오류: {feature.error_message}")
    
    def render(self) -> None:
        """기능 상태를 렌더링합니다."""
        self.display_feature_status()