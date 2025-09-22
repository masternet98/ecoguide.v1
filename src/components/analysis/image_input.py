"""
이미지 입력 처리 컴포넌트 - 카메라/갤러리 입력을 담당합니다.
"""
import streamlit as st
from typing import Optional
from src.components.base import BaseComponent
from src.app.core.session_state import SessionStateManager


class ImageInputComponent(BaseComponent):
    """이미지 입력을 처리하는 컴포넌트입니다."""
    
    def render(self, tab_selector: str) -> Optional[bytes]:
        """
        이미지 입력을 처리하고 바이트 데이터를 반환합니다.
        
        Args:
            tab_selector: 선택된 탭 ("📷 카메라" 또는 "🖼️ 갤러리")
            
        Returns:
            이미지 바이트 데이터 또는 None
        """
        if tab_selector == "📷 카메라":
            return self._handle_camera_input(tab_selector)
        elif tab_selector == "🖼️ 갤러리":
            return self._handle_gallery_input(tab_selector)
        
        # 세션 상태에서 이미지 가져오기
        return SessionStateManager.get_selected_image_bytes(tab_selector)
    
    def _handle_camera_input(self, tab_selector: str) -> Optional[bytes]:
        """카메라 입력을 처리합니다."""
        st.info("아래 카메라 버튼으로 사진을 촬영하세요.")
        camera_photo = st.camera_input("사진 촬영", key=f"camera_input_{tab_selector}")
        
        if camera_photo:
            SessionStateManager.update_image_bytes("camera", camera_photo.getvalue())
            return camera_photo.getvalue()
        
        return None
    
    def _handle_gallery_input(self, tab_selector: str) -> Optional[bytes]:
        """갤러리 입력을 처리합니다."""
        gallery_photo = st.file_uploader(
            "사진 파일을 업로드하세요", 
            type=["png", "jpg", "jpeg"], 
            key=f"gallery_uploader_{tab_selector}"
        )
        
        if gallery_photo:
            SessionStateManager.update_image_bytes("gallery", gallery_photo.getvalue())
            return gallery_photo.getvalue()
        
        return None