"""
위치 선택 UI 컴포넌트입니다.
사용자의 GPS 위치 자동 감지 또는 수동 시/도 및 시/군/구 선택을 제공합니다.
"""
import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime

from src.components.base import BaseComponent
from src.app.core.session_state import SessionStateManager

# GPS 자동 감지 기능 추가
try:
    from streamlit_geolocation import streamlit_geolocation
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False


class LocationSelectorComponent(BaseComponent):
    """위치 선택 UI를 관리하는 컴포넌트입니다."""

    def __init__(self, app_context):
        super().__init__(app_context)
        self.location_service = self.get_service('location_service')

    def render(self) -> Optional[Dict[str, Any]]:
        """
        위치 선택 UI를 렌더링하고 선택된 위치 정보를 반환합니다.

        Returns:
            선택된 위치 정보 딕셔너리 또는 None
        """
        # st.subheader("📍 위치 선택")

        # 저장된 위치 확인 및 표시
        saved_location = self._check_saved_location()
        if saved_location:
            return saved_location

        # 위치 서비스 상태 확인
        if not self.location_service:
            st.error("위치 서비스를 사용할 수 없습니다.")
            return None

        # 선택 방법 탭
        tab1, tab2 = st.tabs(["🗺️ 지역 선택", "📍 GPS 자동 감지"])

        with tab1:
            # 기본 프로세스: 수동 선택 (캐시에 의존하지 않음)
            manual_result = self._render_manual_selection()
            if manual_result:
                return self._process_location_result(manual_result, "manual")

        with tab2:
            # 옵션 프로세스: GPS 자동 감지
            gps_result = self._render_gps_selection()
            if gps_result:
                return self._process_location_result(gps_result, "gps")

        return None

    def _check_saved_location(self) -> Optional[Dict[str, Any]]:
        """저장된 사용자 위치 확인 및 관리"""
        # 위치 변경 모드인 경우 저장된 위치 무시
        if st.session_state.get('location_change_mode', False):
            return None

        # 방금 저장한 경우 처리
        if st.session_state.get('location_just_saved', False):
            # 플래그 제거하고 저장된 위치 로드
            st.session_state.location_just_saved = False

        saved_location = SessionStateManager.load_user_location()
        if not saved_location:
            return None

        location_data = saved_location.get('location_data', {})
        method = saved_location.get('method', 'manual')
        saved_at = saved_location.get('saved_at', 'N/A')        

        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                # 저장된 위치 정보를 간단하게 표시
                dong_info = ""
                if location_data.get('dong'):
                    dong_type = location_data.get('dong_type', '')
                    type_display = f"({dong_type})" if dong_type else ""
                    dong_info = f" {location_data['dong']}{type_display}"

                st.markdown(f"""
                #### 📍 선택 위치 : {location_data.get('sido', 'N/A')} {location_data.get('sigungu', 'N/A')}{dong_info}
                - 저장 시간: {saved_at}
                - 선택 방법: {self._get_method_display(location_data.get('method', 'unknown'))}
                """)

            with col2:
                if st.button("🔄 다시 선택", key="change_location"):
                    st.session_state.location_change_mode = True
                    # st.rerun() 제거

                if st.button("🗑️ 삭제", key="delete_location"):
                    SessionStateManager.delete_saved_user_location()
                    st.session_state.location_change_mode = True  # 삭제 후 선택 모드로

        # 세션 상태 업데이트
        SessionStateManager.update_location_info(location_data, method)

        return {
            'success': True,
            'message': f'저장된 위치를 로드했습니다. ({method})',
            'data': location_data
        }

    def _render_manual_selection(self) -> Optional[Dict[str, Any]]:
        """수동 선택 UI - 정적 데이터 기반, 캐시 의존성 없음"""

        # 시도 목록 가져오기
        sido_list = self.location_service.get_sido_list()
        if not sido_list:
            st.error("행정구역 데이터를 불러올 수 없습니다.")
            return None

        # 3열 레이아웃
        col1, col2, col3 = st.columns(3)

        # 시도 선택
        with col1:
            selected_sido = st.selectbox(
                "시/도 선택",
                options=sido_list,
                key="manual_sido"
            )

        # 시군구 선택
        with col2:
            if selected_sido:
                sigungu_list = self.location_service.get_sigungu_list_by_sido(selected_sido)
                if sigungu_list:
                    selected_sigungu = st.selectbox(
                        "시/군/구 선택",
                        options=sigungu_list,
                        key="manual_sigungu"
                    )
                else:
                    st.warning("시/군/구 데이터가 없습니다.")
                    return None
            else:
                st.info("시/도를 먼저 선택하세요")
                return None

        # 동 선택 (JSON 데이터 기반)
        selected_dong = None
        with col3:
            if selected_sido and selected_sigungu:
                dong_list = self.location_service.get_dong_list_by_sigungu_from_json(selected_sido, selected_sigungu)

                if dong_list:
                    dong_options = ["동 선택 안함"] + [dong['dong'] for dong in dong_list if dong.get('dong')]

                    selected_dong_option = st.selectbox(
                        "동 선택 (선택사항)",
                        options=dong_options,
                        key="manual_dong"
                    )

                    if selected_dong_option != "동 선택 안함":
                        selected_dong = selected_dong_option
                else:
                    st.info("동 정보가 없습니다")

        # 선택 완료
        if selected_sido and selected_sigungu:
            preview = f"{selected_sido} {selected_sigungu}"
            if selected_dong:
                preview += f" {selected_dong}"

            st.info(f"**선택된 위치**: {preview}")

            if st.button("✅ 위치 선택 완료", key="manual_complete", type="primary"):
                if selected_dong:
                    return self.location_service.get_location_info_with_dong(selected_sido, selected_sigungu, selected_dong)
                else:
                    return self.location_service.get_location_info(selected_sido, selected_sigungu)

        return None

    def _render_gps_selection(self) -> Optional[Dict[str, Any]]:
        """GPS 자동 감지 UI"""
        if not GPS_AVAILABLE:
            st.error("❌ GPS 기능을 사용할 수 없습니다. streamlit-geolocation 패키지가 필요합니다.")
            return None

        st.markdown("""
        **📱 GPS 위치 확인**
        - 브라우저에서 위치 접근 권한을 허용해주세요
        - 실외에서 더 정확한 결과를 얻을 수 있습니다
        - 아래 버튼을 클릭하여 위치 정보를 가져오세요
        """)

        try:
            # streamlit_geolocation 자체가 버튼 역할을 함
            location_data = streamlit_geolocation()

            st.write(f"🐛 Debug - 받은 데이터: {location_data}")  # 디버그 출력

            if location_data and isinstance(location_data, dict):
                lat = location_data.get('latitude')
                lng = location_data.get('longitude')

                st.write(f"🐛 Debug - 좌표: lat={lat}, lng={lng}")  # 디버그 출력

                if lat is not None and lng is not None:
                    st.success(f"✅ GPS 좌표: {lat:.6f}, {lng:.6f}")

                    # 주소 변환
                    with st.spinner("주소 변환 중..."):
                        location_result = self.location_service.get_location_from_coords(lat, lng)
                        if location_result.get('success'):
                            st.success("✅ 주소 변환 완료!")
                            return location_result
                        else:
                            st.error(f"❌ 주소 변환 실패: {location_result.get('message', '알 수 없는 오류')}")
                else:
                    if location_data != "No Location Info":
                        st.warning("⚠️ GPS 좌표를 받지 못했습니다.")
            else:
                if location_data and location_data != "No Location Info":
                    st.warning(f"⚠️ GPS 데이터 형식 오류: {type(location_data)}")
        except Exception as e:
            st.error(f"❌ GPS 감지 실패: {str(e)}")
            import traceback
            st.error(f"상세 오류: {traceback.format_exc()}")

        return None

    def _process_location_result(self, location_result: Dict[str, Any], method: str) -> Dict[str, Any]:
        """위치 선택 결과 처리 및 자동 저장"""
        if not location_result.get('success'):
            st.error(f"❌ 위치 처리 실패: {location_result.get('message', '알 수 없는 오류')}")
            return None

        location_data = location_result['data']

        # 자동 저장 처리
        try:
            SessionStateManager.save_user_location(location_data, method)
            st.success("✅ 위치가 선택되고 저장되었습니다!")
            st.balloons()
        except Exception as e:
            st.error(f"❌ 위치 저장 실패: {str(e)}")
            return None

        # 위치 정보 표시
        self._render_selected_location_info(location_data)

        # 세션 상태 업데이트
        SessionStateManager.update_location_info(location_data, method)

        return location_result

    def _render_selected_location_info(self, location_data: Dict[str, Any]) -> None:
        """선택되고 저장된 위치 정보를 표시합니다."""
        st.markdown("---")

        # 동 정보 표시 준비
        dong_info = ""
        if location_data.get('dong'):
            dong_type = location_data.get('dong_type', '')
            type_display = f"({dong_type})" if dong_type else ""
            dong_info = f" {location_data['dong']}{type_display}"

        # 위치 정보 카드
        st.info(f"""
        **📍 선택된 내 위치**

        🏢 **{location_data.get('sido', 'N/A')} {location_data.get('sigungu', 'N/A')}{dong_info}**

        📋 전체 주소: {location_data.get('full_address', 'N/A')}

        🔧 선택 방법: {self._get_method_display(location_data.get('method', 'unknown'))}

        💾 다음번 사용 시 자동으로 불러옵니다.
        """)

        # 좌표 정보 (GPS인 경우)
        coords = location_data.get('coords')
        if coords:
            st.caption(f"📐 좌표: {coords.get('lat', 'N/A')}, {coords.get('lng', 'N/A')}")

        # 위치 변경 버튼
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 다른 위치 선택", key="change_location_new", use_container_width=True):
                st.session_state.location_change_mode = True


    def _get_method_display(self, method: str) -> str:
        """위치 선택 방법을 사용자 친화적으로 표시합니다."""
        method_map = {
            'gps': '📍 GPS 자동 감지',
            'manual': '🗺️ 수동 선택',
            'vworld_api': '📍 GPS (VWorld)',
            'unknown': '❓ 알 수 없음'
        }
        return method_map.get(method, f'❓ {method}')

    # === 기존 메서드들 (호환성을 위해 유지) ===

    def get_current_location(self) -> Optional[Dict[str, Any]]:
        """현재 선택된 위치 정보를 반환합니다."""
        location_state = SessionStateManager.get_location_state()
        if location_state.current_location:
            return {
                'success': True,
                'data': location_state.current_location,
                'method': location_state.location_method
            }
        return None

    def is_location_selected(self) -> bool:
        """위치가 선택되었는지 확인합니다."""
        location_state = SessionStateManager.get_location_state()
        return bool(location_state.current_location)