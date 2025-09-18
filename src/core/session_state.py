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


@dataclass
class LocationSessionState:
    """위치 관련 세션 상태를 관리하는 데이터 클래스"""
    current_location: Optional[Dict[str, Any]] = None  # GPS 좌표나 수동 선택 위치 정보
    selected_sido: Optional[str] = None                # 선택된 시/도
    selected_sigungu: Optional[str] = None             # 선택된 시/군/구
    location_method: str = "manual"                    # "gps" | "manual"
    last_update: Optional[str] = None                  # 마지막 업데이트 시간
    coordinates: Optional[Dict[str, float]] = None     # GPS 좌표 {'lat': float, 'lng': float}

    # 신규: 동 단위 정보 필드
    selected_dong: Optional[str] = None                # 선택된 동 (대표 동)
    selected_legal_dong: Optional[str] = None          # 법정동
    selected_admin_dong: Optional[str] = None          # 행정동
    dong_type: Optional[str] = None                    # 동 타입 ("법정동" | "행정동")


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
                # 최신 Streamlit에서는 st.rerun() 사용
                if hasattr(st, "rerun"):
                    st.rerun()
                elif hasattr(st, "experimental_rerun"):
                    st.experimental_rerun()
                else:
                    st.session_state["_tab_rerun_toggle"] = not st.session_state.get("_tab_rerun_toggle", False)
            except Exception:
                pass
            
            return True

        return False

    @staticmethod
    def init_location_state() -> LocationSessionState:
        """위치 관련 세션 상태를 초기화하거나 가져옵니다"""
        location_keys = [
            'current_location', 'selected_sido', 'selected_sigungu',
            'location_method', 'location_last_update', 'location_coordinates'
        ]

        for key in location_keys:
            if key not in st.session_state:
                if key == 'location_method':
                    st.session_state[key] = "manual"
                else:
                    st.session_state[key] = None

        return LocationSessionState(
            current_location=st.session_state.current_location,
            selected_sido=st.session_state.selected_sido,
            selected_sigungu=st.session_state.selected_sigungu,
            location_method=st.session_state.location_method,
            last_update=st.session_state.location_last_update,
            coordinates=st.session_state.location_coordinates
        )

    @staticmethod
    def get_location_state() -> LocationSessionState:
        """현재 위치 세션 상태를 가져옵니다"""
        return SessionStateManager.init_location_state()

    @staticmethod
    def update_location_info(location_data: Dict[str, Any], method: str) -> None:
        """위치 정보를 세션 상태에 저장합니다"""
        from datetime import datetime

        st.session_state.current_location = location_data
        st.session_state.selected_sido = location_data.get('sido')
        st.session_state.selected_sigungu = location_data.get('sigungu')
        st.session_state.location_method = method
        st.session_state.location_last_update = datetime.now().isoformat()

        # 신규: 동 정보 저장
        st.session_state.selected_dong = location_data.get('dong')
        st.session_state.selected_legal_dong = location_data.get('legal_dong')
        st.session_state.selected_admin_dong = location_data.get('admin_dong')
        st.session_state.dong_type = location_data.get('dong_type')

        # 좌표 정보가 있으면 별도 저장
        coords = location_data.get('coords')
        if coords:
            st.session_state.location_coordinates = {
                'lat': coords.get('lat'),
                'lng': coords.get('lng')
            }
        else:
            st.session_state.location_coordinates = None

    @staticmethod
    def clear_location_info() -> None:
        """위치 정보를 모두 지웁니다"""
        location_keys = [
            'current_location', 'selected_sido', 'selected_sigungu',
            'location_last_update', 'location_coordinates',
            # 신규: 동 정보 필드들
            'selected_dong', 'selected_legal_dong', 'selected_admin_dong', 'dong_type'
        ]

        for key in location_keys:
            st.session_state[key] = None

        st.session_state.location_method = "manual"

    @staticmethod
    def save_user_location(location_data: Dict[str, Any], method: str) -> None:
        """사용자 위치를 브라우저 로컬 스토리지에 저장합니다"""
        try:
            import json

            # 저장할 위치 데이터 구성
            saved_location = {
                'location_data': location_data,
                'method': method,
                'saved_at': location_data.get('last_update'),
                'version': '1.0'
            }

            # 세션 스토리지에 저장 (브라우저 세션 유지)
            st.session_state.saved_user_location = saved_location

            # 추가적으로 Streamlit secrets에도 저장 가능 (선택사항)

        except Exception as e:
            st.warning(f"⚠️ 사용자 위치 저장 실패: {str(e)}")

    @staticmethod
    def load_user_location() -> Optional[Dict[str, Any]]:
        """저장된 사용자 위치를 로드합니다"""
        try:
            saved_location = st.session_state.get('saved_user_location')
            if saved_location:
                return saved_location
            return None
        except Exception as e:
            st.warning(f"⚠️ 사용자 위치 로드 실패: {str(e)}")
            return None

    @staticmethod
    def has_saved_user_location() -> bool:
        """저장된 사용자 위치가 있는지 확인합니다"""
        return st.session_state.get('saved_user_location') is not None

    @staticmethod
    def get_current_location_summary() -> Optional[str]:
        """현재 선택된 위치를 요약한 문자열을 반환합니다"""
        location_state = SessionStateManager.get_location_state()

        if not location_state.current_location:
            return None

        sido = location_state.selected_sido or "알 수 없음"
        sigungu = location_state.selected_sigungu or "알 수 없음"
        method_display = {
            'gps': '📍 GPS 자동 감지',
            'manual': '🗺️ 수동 선택'
        }.get(location_state.location_method, location_state.location_method)

        return f"{sido} {sigungu} ({method_display})"

    @staticmethod
    def is_location_selected() -> bool:
        """위치가 선택되었는지 확인합니다"""
        location_state = SessionStateManager.get_location_state()
        return bool(location_state.current_location)