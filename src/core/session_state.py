"""
Streamlit 세션 상태를 체계적으로 관리하는 모듈입니다.
복잡한 상태 로직을 중앙화하고 타입 안전성을 제공합니다.
"""
import streamlit as st
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ImageSessionState:
    """이미지 관련 세션 상태를 관리하는 데이터 클래스"""
    camera_photo_bytes: Optional[bytes] = None
    gallery_photo_bytes: Optional[bytes] = None
    last_photo_source: Optional[str] = None
    analysis_output: Optional[str] = None
    analysis_raw: Optional[Dict[str, Any]] = None


@dataclass
class UISessionState:
    """UI 상태를 관리하는 데이터 클래스"""
    prev_active_tab: Optional[str] = None
    current_tab: Optional[str] = None
    rerun_toggle: bool = False


class SessionStateManager:
    """세션 상태를 체계적으로 관리하는 매니저 클래스"""
    
    @staticmethod
    def init_image_state() -> ImageSessionState:
        """이미지 관련 세션 상태를 초기화하거나 가져옵니다"""
        keys = [
            'camera_photo_bytes', 'gallery_photo_bytes', 'last_photo_source',
            'analysis_output', 'analysis_raw'
        ]
        
        for key in keys:
            if key not in st.session_state:
                st.session_state[key] = None
        
        return ImageSessionState(
            camera_photo_bytes=st.session_state.camera_photo_bytes,
            gallery_photo_bytes=st.session_state.gallery_photo_bytes,
            last_photo_source=st.session_state.last_photo_source,
            analysis_output=st.session_state.analysis_output,
            analysis_raw=st.session_state.analysis_raw
        )
    
    @staticmethod
    def init_ui_state() -> UISessionState:
        """UI 관련 세션 상태를 초기화하거나 가져옵니다"""
        if 'prev_active_tab' not in st.session_state:
            st.session_state.prev_active_tab = None
        if '_tab_rerun_toggle' not in st.session_state:
            st.session_state._tab_rerun_toggle = False
            
        return UISessionState(
            prev_active_tab=st.session_state.prev_active_tab,
            rerun_toggle=st.session_state._tab_rerun_toggle
        )
    
    @staticmethod
    def clear_image_data() -> None:
        """이미지 데이터와 분석 결과를 지웁니다"""
        clear_keys = [
            'camera_photo_bytes', 'gallery_photo_bytes', 'last_photo_source',
            'analysis_output', 'analysis_raw'
        ]
        
        for key in clear_keys:
            st.session_state[key] = None
    
    @staticmethod
    def update_image_bytes(source: str, data: bytes) -> None:
        """이미지 바이트 데이터를 업데이트합니다"""
        if source == "camera":
            st.session_state.camera_photo_bytes = data
        elif source == "gallery":
            st.session_state.gallery_photo_bytes = data
        
        st.session_state.last_photo_source = source
    
    @staticmethod
    def update_analysis_results(output: str, raw: Dict[str, Any]) -> None:
        """분석 결과를 세션 상태에 저장합니다"""
        st.session_state.analysis_output = output
        st.session_state.analysis_raw = raw
    
    @staticmethod
    def get_selected_image_bytes(tab_selector: str) -> Optional[bytes]:
        """현재 선택된 탭의 이미지 바이트를 반환합니다"""
        if tab_selector == "📷 카메라":
            return st.session_state.get("camera_photo_bytes")
        elif tab_selector == "🖼️ 갤러리":
            return st.session_state.get("gallery_photo_bytes")
        return None
    
    @staticmethod
    def handle_tab_switch(current_tab: str) -> bool:
        """탭 전환을 감지하고 처리합니다. 전환이 발생하면 True를 반환합니다."""
        prev_tab = st.session_state.get("prev_active_tab")
        
        if prev_tab is None:
            st.session_state.prev_active_tab = current_tab
            return False
        elif prev_tab != current_tab:
            # 탭 전환 시 데이터 초기화
            SessionStateManager.clear_image_data()
            st.session_state.prev_active_tab = current_tab
            
            # UI 재렌더링 시도
            try:
                rerun_fn = getattr(st, "experimental_rerun", None)
                if callable(rerun_fn):
                    rerun_fn()
                else:
                    st.session_state["_tab_rerun_toggle"] = not st.session_state.get("_tab_rerun_toggle", False)
            except Exception:
                pass
            
            return True
        
        return False