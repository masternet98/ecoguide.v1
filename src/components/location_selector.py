"""
위치 선택 UI 컴포넌트입니다.
사용자의 GPS 위치 자동 감지 또는 수동 시/도 및 시/군/구 선택을 제공합니다.
"""
import streamlit as st
from typing import Optional, Dict, Any

from src.components.base import BaseComponent
from src.core.session_state import SessionStateManager

# GPS 자동 감지 기능 추가
try:
    from streamlit_geolocation import streamlit_geolocation
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False
    st.warning("⚠️ GPS 기능을 사용하려면 'pip install streamlit-geolocation' 설치 필요")


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
        st.subheader("📍 위치 선택")

        # 위치 서비스 상태 확인
        if not self.location_service:
            st.error("위치 서비스를 사용할 수 없습니다.")
            return None

        # 현재 세션에서 선택된 위치 정보 가져오기
        location_state = SessionStateManager.get_location_state()

        # 0. 저장된 사용자 위치 확인 및 로딩
        saved_location = self._check_and_load_saved_location()
        if saved_location:
            return saved_location

        # UI 재설계: 수동 선택이 기본, GPS는 옵션
        selected_location = None
        selection_method = "manual"  # 기본값은 수동 선택

        # 1. 기본 수동 선택 UI (3열 레이아웃)
        selected_location = self._render_manual_selector_redesigned(location_state)

        # 2. GPS 자동 감지 옵션 (expander 형태)
        if not selected_location:  # 수동 선택이 완료되지 않은 경우만 GPS 옵션 제공
            with st.expander("📍 GPS 자동 감지", expanded=False):
                gps_location = self._render_gps_button_selector(location_state)
                if gps_location:
                    selected_location = gps_location
                    selection_method = "gps"  # GPS 선택으로 변경

        # 선택된 위치 정보 표시 및 저장 옵션
        if selected_location and selected_location.get('success'):
            self._render_location_info(selected_location['data'])

            # 사용자 위치 저장 옵션 제공
            self._render_save_location_option(selected_location['data'], selection_method)

            # 세션 상태 업데이트
            try:
                SessionStateManager.update_location_info(
                    selected_location['data'],
                    selection_method
                )
            except Exception as e:
                st.warning(f"⚠️ 세션 상태 업데이트 중 오류가 발생했습니다: {str(e)}")
                # 세션 상태 업데이트 실패해도 location_result는 반환

            return selected_location

        return None

    def _check_and_load_saved_location(self) -> Optional[Dict[str, Any]]:
        """저장된 사용자 위치를 확인하고 로딩합니다"""
        if SessionStateManager.has_saved_user_location():
            saved_location = SessionStateManager.load_user_location()
            if saved_location:
                location_data = saved_location.get('location_data')
                method = saved_location.get('method', 'manual')
                saved_at = saved_location.get('saved_at', 'N/A')

                # 저장된 위치 표시
                st.success("✅ **저장된 내 위치 정보**")

                col1, col2 = st.columns([3, 1])
                with col1:
                    self._render_location_info(location_data)
                    st.caption(f"📅 저장 시간: {saved_at}")

                with col2:
                    if st.button("🗑️ 삭제", key="delete_saved_location"):
                        st.session_state.saved_user_location = None
                        st.rerun()

                    if st.button("🔄 다시 선택", key="reselect_location"):
                        return None  # 새로 선택하도록

                # 저장된 위치를 세션 상태에 로딩
                try:
                    SessionStateManager.update_location_info(location_data, method)
                except Exception as e:
                    st.warning(f"⚠️ 저장된 위치 로딩 중 오류: {str(e)}")

                return {
                    'success': True,
                    'message': f'저장된 위치 정보를 불러왔습니다. ({method})',
                    'data': location_data
                }

        return None

    def _render_save_location_option(self, location_data: Dict[str, Any], method: str) -> None:
        """사용자 위치 저장 옵션을 렌더링합니다"""
        st.markdown("---")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("**💾 내 위치 저장하기**")
            st.caption("다음번에 앱을 사용할 때 이 위치를 기본으로 설정합니다.")

        with col2:
            if st.button("📍 내 위치 저장", key="save_user_location", type="primary"):
                try:
                    SessionStateManager.save_user_location(location_data, method)
                    st.success("✅ 내 위치가 저장되었습니다!")
                    st.balloons()
                    # 약간의 지연 후 리프레시
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 위치 저장 실패: {str(e)}")

    def _render_gps_button_selector(self, location_state) -> Optional[Dict[str, Any]]:
        """버튼 방식의 GPS 자동 감지 UI를 렌더링합니다."""

        if not GPS_AVAILABLE:
            st.error("❌ GPS 기능을 사용할 수 없습니다. streamlit-geolocation 패키지가 필요합니다.")
            return None

        st.markdown(
            """
            **📱 GPS 위치 확인 안내**
            - 브라우저에서 위치 접근 권한을 요청합니다
            - 정확한 위치 확인을 위해 권한을 허용해주세요
            - 실외에서 더 정확한 결과를 얻을 수 있습니다
            """
        )

        request_flag_key = "_gps_request_active"
        status_message_key = "_gps_status_message"

        if request_flag_key not in st.session_state:
            st.session_state[request_flag_key] = False
        if status_message_key not in st.session_state:
            st.session_state[status_message_key] = ""

        gps_button_clicked = st.button("📍 GPS 위치 확인", type="primary")
        if gps_button_clicked:
            st.session_state[request_flag_key] = True
            st.session_state[status_message_key] = "📡 브라우저에 위치 정보를 요청했습니다. 권한 허용을 확인해주세요."

        if not st.session_state.get(request_flag_key):
            st.caption("버튼을 누르면 최신 좌표를 가져옵니다.")
            return None

        status_message = st.session_state.get(status_message_key)
        if status_message:
            st.info(status_message)

        location_data = streamlit_geolocation()

        if location_data is None:
            st.info("📍 GPS 감지 중... 잠시만 기다려주세요")
            return None

        if location_data == "No Location Info":
            st.warning("⏳ GPS 위치 감지 중입니다. 브라우저에서 위치 권한을 허용한 뒤 다시 시도해주세요.")
            return None

        if isinstance(location_data, dict) and location_data.get('error'):
            st.error(f"❌ GPS 감지 실패: {location_data['error']}")
            st.session_state[request_flag_key] = False
            st.session_state[status_message_key] = ""
            return None

        if not isinstance(location_data, dict):
            st.warning("⚠️ 예상하지 못한 GPS 데이터 형식입니다.")
            st.write("디버깅 정보:", location_data)
            st.session_state[request_flag_key] = False
            st.session_state[status_message_key] = ""
            return None

        lat = location_data.get("latitude")
        lng = location_data.get("longitude")
        accuracy = location_data.get("accuracy")

        if lat is None or lng is None:
            st.info("📍 좌표 수신을 기다리는 중입니다...")
            return None

        st.success(f"✅ GPS 좌표 확인: 위도 {lat:.6f}, 경도 {lng:.6f}")

        try:
            accuracy_value = float(accuracy)
        except (TypeError, ValueError):
            accuracy_value = None

        if accuracy_value is not None:
            st.info(f"📏 정확도: {accuracy_value:.0f}m")
        else:
            st.info("📏 정확도: 알 수 없음")

        with st.spinner("🔍 주소 변환 중..."):
            location_result = self.location_service.get_location_from_coords(lat, lng)

        st.session_state[request_flag_key] = False
        st.session_state[status_message_key] = ""

        if location_result and location_result.get("success"):
            st.success("✅ GPS 위치 감지 완료!")
            data = location_result["data"]
            address_info = f"📍 **감지된 위치**: {data.get('full_address', 'N/A')}"
            if data.get("dong"):
                address_info += f"\n🏘️ **동 정보**: {data.get('dong')} ({data.get('dong_type', 'N/A')})"
            st.markdown(address_info)
            return location_result

        st.error(f"❌ 주소 변환 실패: {location_result.get('message', '알 수 없는 오류') if location_result else 'API 연결 실패'}")

        fallback_data = {
            "sido": "GPS 감지 위치",
            "sigungu": f"위도 {lat:.4f}, 경도 {lng:.4f}",
            "full_address": f"GPS 좌표: {lat:.6f}, {lng:.6f}",
            "coords": {"lat": lat, "lng": lng},
            "method": "gps",
            "accuracy": accuracy,
        }

        st.info("📁 좌표 정보만 우선 제공하며, 주소 변환 실패 원인을 확인해주세요.")

        return {
            "success": True,
            "message": "GPS 좌표는 감지되었으나 주소 변환에 실패했습니다.",
            "data": fallback_data,
        }

    def _render_gps_selector(self, location_state) -> Optional[Dict[str, Any]]:
        """GPS 자동 감지 UI를 렌더링합니다."""

        col1, col2 = st.columns([2, 1])

        with col1:
            st.info("📍 현재 위치 버튼을 클릭하면 GPS를 통해 자동으로 위치를 감지합니다.")

        gps_ui_open = st.session_state.get('_gps_ui_open', False)

        with col2:
            get_location_clicked = st.button(
                "📍 현재 위치",
                key="get_gps_location",
                help="GPS를 사용하여 현재 위치를 자동 감지합니다."
            )
            if get_location_clicked:
                gps_ui_open = True
                st.session_state._gps_ui_open = True

        if (location_state.current_location and
            location_state.location_method == "gps"):
            return {
                'success': True,
                'message': '이전에 감지된 GPS 위치입니다.',
                'data': location_state.current_location
            }

        if gps_ui_open:
            location_result = self._get_gps_location()
            if location_result:
                st.session_state._gps_ui_open = False
                return location_result

        return None

    def _render_manual_selector_redesigned(self, location_state) -> Optional[Dict[str, Any]]:
        """재설계된 수동 선택 UI: 3열 레이아웃 + 실시간 API 동 목록"""

        st.markdown("**🗺️ 지역 선택**")

        # 시/도 목록 가져오기
        sido_list = self.location_service.get_sido_list()
        if not sido_list:
            st.error("행정구역 데이터를 불러올 수 없습니다.")
            return None

        # 3열 레이아웃 구성
        col1, col2, col3 = st.columns(3)

        # 1열: 시/도 선택
        with col1:
            current_sido_idx = 0
            if location_state.selected_sido and location_state.selected_sido in sido_list:
                current_sido_idx = sido_list.index(location_state.selected_sido)

            selected_sido = st.selectbox(
                "시/도 선택",
                options=sido_list,
                index=current_sido_idx,
                key="redesigned_sido_selector"
            )

        # 2열: 시/군/구 선택
        with col2:
            if selected_sido:
                sigungu_list = self.location_service.get_sigungu_list_by_sido(selected_sido)

                if sigungu_list:
                    current_sigungu_idx = 0
                    if (location_state.selected_sigungu and
                        location_state.selected_sigungu in sigungu_list):
                        current_sigungu_idx = sigungu_list.index(location_state.selected_sigungu)

                    selected_sigungu = st.selectbox(
                        "시/군/구 선택",
                        options=sigungu_list,
                        index=current_sigungu_idx,
                        key="redesigned_sigungu_selector"
                    )
                else:
                    st.warning("시/군/구 데이터 없음")
                    selected_sigungu = None
            else:
                st.info("시/도를 먼저 선택하세요")
                selected_sigungu = None

        # 3열: 동 선택 (실시간 API 호출)
        with col3:
            if selected_sido and selected_sigungu:
                # 동 목록 로딩 상태 표시
                with st.spinner("동 목록 로딩 중..."):
                    dong_list = self.location_service.get_dong_list_by_sampling(selected_sido, selected_sigungu)

                if dong_list:
                    dong_options = ["동 선택 안함"] + [
                        f"{dong_info.get('dong', '')} ({dong_info.get('dong_type', '')})"
                        for dong_info in dong_list if dong_info.get('dong')
                    ]

                    current_dong_idx = 0
                    if location_state.selected_dong:
                        # 세션에서 이전 선택된 동 찾기
                        for idx, option in enumerate(dong_options):
                            if location_state.selected_dong in option:
                                current_dong_idx = idx
                                break

                    selected_dong_option = st.selectbox(
                        "법정동 선택",
                        options=dong_options,
                        index=current_dong_idx,
                        key="redesigned_dong_selector"
                    )

                    # 선택된 동 파싱
                    selected_dong = None
                    selected_dong_info = None
                    if selected_dong_option != "동 선택 안함":
                        # "동이름 (타입)" 형태에서 동이름 추출
                        dong_name = selected_dong_option.split(" (")[0]
                        selected_dong = dong_name

                        # 상세 정보 찾기
                        for dong_info in dong_list:
                            if dong_info.get('dong') == dong_name:
                                selected_dong_info = dong_info
                                break

                else:
                    st.info("동 정보 수집 중...")
                    selected_dong = None
                    selected_dong_info = None
            else:
                st.info("시/군/구를 먼저 선택하세요")
                selected_dong = None
                selected_dong_info = None

        # 선택 완료 버튼 및 결과 처리
        if selected_sido and selected_sigungu:
            # 선택 미리보기
            preview_text = f"**선택된 위치**: {selected_sido} {selected_sigungu}"
            if selected_dong:
                preview_text += f" {selected_dong}"
            st.info(preview_text)

            # 위치 선택 완료 버튼
            if st.button("✅ 위치 선택 완료", key="redesigned_location_complete", type="primary"):
                # 위치 정보 구성
                if selected_dong and selected_dong_info:
                    location_result = self.location_service.get_location_info_with_dong(
                        selected_sido, selected_sigungu, selected_dong
                    )
                else:
                    location_result = self.location_service.get_location_info(selected_sido, selected_sigungu)

                if location_result['success']:
                    st.success(f"✅ 위치 선택 완료: {preview_text.replace('**선택된 위치**: ', '')}")
                    return location_result
                else:
                    st.error(f"❌ 위치 검증 실패: {location_result['message']}")
                    return None

        return None

    def _render_manual_selector(self, location_state) -> Optional[Dict[str, Any]]:
        """수동 선택 UI를 렌더링합니다."""

        # 시/도 목록 가져오기
        sido_list = self.location_service.get_sido_list()

        if not sido_list:
            st.error("행정구역 데이터를 불러올 수 없습니다.")
            return None

        # 현재 선택된 시/도 (세션 상태에서 가져오기)
        current_sido_idx = 0
        if location_state.selected_sido and location_state.selected_sido in sido_list:
            current_sido_idx = sido_list.index(location_state.selected_sido)

        # 시/도 선택
        selected_sido = st.selectbox(
            "시/도 선택:",
            options=sido_list,
            index=current_sido_idx,
            key="sido_selector"
        )

        if selected_sido:
            # 선택된 시/도의 시/군/구 목록 가져오기
            sigungu_list = self.location_service.get_sigungu_list_by_sido(selected_sido)

            if not sigungu_list:
                st.warning(f"{selected_sido}의 시/군/구 데이터를 찾을 수 없습니다.")
                return None

            # 현재 선택된 시/군/구
            current_sigungu_idx = 0
            if (location_state.selected_sigungu and
                location_state.selected_sigungu in sigungu_list):
                current_sigungu_idx = sigungu_list.index(location_state.selected_sigungu)

            # 시/군/구 선택
            selected_sigungu = st.selectbox(
                "시/군/구 선택:",
                options=sigungu_list,
                index=current_sigungu_idx,
                key="sigungu_selector"
            )

            if selected_sigungu:
                # Phase 3: 3단계 동 선택 콤보박스 추가
                # 선택된 시/군/구의 동 목록 가져오기
                dong_list = self.location_service.get_dong_list_by_sigungu(selected_sido, selected_sigungu)

                selected_dong = None
                if dong_list:
                    # 동 옵션에 "동 선택 안함" 추가
                    dong_options = ["동 선택 안함"] + [dong_info.get('dong', '') for dong_info in dong_list if dong_info.get('dong')]

                    # 현재 선택된 동 (세션 상태에서 가져오기)
                    current_dong_idx = 0
                    if (location_state.selected_dong and
                        location_state.selected_dong in dong_options):
                        current_dong_idx = dong_options.index(location_state.selected_dong)

                    # 동 선택 콤보박스
                    selected_dong_option = st.selectbox(
                        "동 선택:",
                        options=dong_options,
                        index=current_dong_idx,
                        key="dong_selector"
                    )

                    # "동 선택 안함"이 아닌 경우만 동으로 설정
                    if selected_dong_option != "동 선택 안함":
                        selected_dong = selected_dong_option

                        # 선택된 동의 상세 정보 표시
                        selected_dong_info = None
                        for dong_info in dong_list:
                            if dong_info.get('dong') == selected_dong:
                                selected_dong_info = dong_info
                                break

                        if selected_dong_info:
                            dong_type = selected_dong_info.get('dong_type', '')
                            st.caption(f"**선택된 동**: {selected_dong} ({dong_type})")
                else:
                    st.info("💡 해당 지역의 동 정보가 캐시에 없습니다. GPS 기능으로 먼저 탐색해보세요.")

                # 위치 선택 완료 버튼
                button_text = "✅ 위치 선택 완료"
                if selected_dong:
                    button_text += f" ({selected_sido} {selected_sigungu} {selected_dong})"
                else:
                    button_text += f" ({selected_sido} {selected_sigungu})"

                if st.button(button_text, key="manual_location_complete"):
                    # 동 정보가 있으면 동 포함 위치 정보 구성
                    if selected_dong:
                        location_result = self.location_service.get_location_info_with_dong(
                            selected_sido, selected_sigungu, selected_dong
                        )
                    else:
                        # 동 정보가 없으면 기존 방식 사용
                        location_result = self.location_service.get_location_info(selected_sido, selected_sigungu)

                    if location_result['success']:
                        success_message = "✅ 위치가 선택되었습니다!"
                        if selected_dong:
                            success_message += f" (동: {selected_dong})"
                        st.success(success_message)
                        return location_result
                    else:
                        st.error(f"❌ 위치 검증 실패: {location_result['message']}")
                        return None

                # 선택 미리보기 정보
                preview_text = f"📍 선택하려는 위치: **{selected_sido} {selected_sigungu}"
                if selected_dong:
                    preview_text += f" {selected_dong}"
                preview_text += "**"
                st.info(preview_text)

        return None

    def _render_real_gps_selector(self, location_state) -> Optional[Dict[str, Any]]:
        """실제 GPS 자동 감지 기능을 렌더링합니다."""

        if not GPS_AVAILABLE:
            st.error("❌ GPS 기능을 사용할 수 없습니다. streamlit-geolocation 패키지가 필요합니다.")
            return self._render_gps_fallback_selector(location_state)

        # 현재 GPS 세션 상태 확인
        if (location_state.current_location and
            location_state.location_method == "gps" and
            location_state.coordinates):

            st.success("✅ 이미 GPS로 감지된 위치가 있습니다.")
            coords = location_state.coordinates
            st.info(f"📍 GPS 좌표: ({coords['lat']:.6f}, {coords['lng']:.6f})")

            if st.button("🔄 GPS 위치 다시 감지", key="refresh_gps"):
                # 세션 상태 초기화하고 다시 감지
                SessionStateManager.clear_location_info()
                st.rerun()

            return {
                'success': True,
                'message': '이전에 감지된 GPS 위치입니다.',
                'data': location_state.current_location
            }

        # 실제 GPS 감지 수행
        st.markdown("**🛰️ 실시간 GPS 위치 감지**")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.info("""
            **GPS 사용 안내:**
            - 브라우저에서 위치 권한을 허용해주세요
            - 정확한 위치 감지를 위해 GPS를 활성화하세요
            - 실내보다는 실외에서 더 정확합니다
            """)

        with col2:
            # streamlit-geolocation 컴포넌트 사용 (key 파라미터 제거)
            location_data = streamlit_geolocation()

            if location_data is None:
                st.info("📍 위 버튼을 클릭하여 GPS 위치를 감지하세요")
                return None
            elif location_data == "No Location Info":
                st.warning("⏳ GPS 위치 감지 중... 잠시만 기다려주세요")
                return None
            elif isinstance(location_data, dict) and 'latitude' in location_data:
                # GPS 좌표 획득 성공!
                lat = location_data['latitude']
                lng = location_data['longitude']
                accuracy = location_data.get('accuracy', None)

                # 방어적 코딩: None 값 처리
                if lat is None or lng is None:
                    st.error("❌ GPS 좌표가 올바르지 않습니다.")
                    return None

                st.success("🎯 GPS 위치 감지 성공!")
                st.info(f"📍 좌표: ({lat:.6f}, {lng:.6f})")

                # accuracy가 None이거나 'N/A'인 경우 안전하게 처리
                if accuracy is not None and accuracy != 'N/A' and str(accuracy).replace('.', '').isdigit():
                    st.info(f"📏 정확도: {accuracy}m")
                else:
                    st.info("📏 정확도: 알 수 없음")

                # VWorld API로 좌표를 주소로 변환
                with st.spinner("GPS 좌표를 주소로 변환 중..."):
                    location_result = self.location_service.get_location_from_coords(lat, lng)

                if location_result['success']:
                    st.success('✅ GPS 기반 주소 변환 완료!')

                    # 추가 정보 표시
                    data = location_result['data']
                    address_info = f"📍 **감지된 위치**: {data.get('full_address', 'N/A')}"
                    if data.get('dong'):
                        address_info += f"\n🏘️ **동 정보**: {data.get('dong')} ({data.get('dong_type', 'N/A')})"
                    st.markdown(address_info)

                    return location_result
                else:
                    # VWorld API 실패 시 폴백 처리
                    st.error(f"❌ 주소 변환 실패: {location_result['message']}")

                    # 기본 GPS 데이터라도 저장
                    fallback_data = {
                        'sido': 'GPS 감지 위치',
                        'sigungu': f"위도 {lat:.4f}, 경도 {lng:.4f}",
                        'full_address': f"GPS 좌표: {lat:.6f}, {lng:.6f}",
                        'coords': {'lat': lat, 'lng': lng},
                        'method': 'gps_raw',
                        'accuracy': accuracy
                    }

                    return {
                        'success': True,
                        'message': 'GPS 좌표는 감지되었으나 주소 변환에 실패했습니다.',
                        'data': fallback_data
                    }
            else:
                st.warning("⚠️ 예상하지 못한 GPS 데이터 형식입니다.")
                st.write("디버깅 정보:", location_data)
                return None

        return None

    def _render_gps_fallback_selector(self, location_state) -> Optional[Dict[str, Any]]:
        """GPS 패키지가 없을 때의 대체 GPS 선택기"""
        return self._get_gps_location()  # 기존 테스트 위치 선택 기능 사용

    def _get_gps_location(self) -> Optional[Dict[str, Any]]:
        """브라우저 GPS 감지를 시도하고 대체 입력 옵션을 제공합니다."""

        st.warning("브라우저와의 직접 GPS 연동은 개발 중입니다. 아래 대안을 사용해 주세요.")

        with st.expander("🧪 좌표 직접 입력 (GPS 대안)", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                manual_lat = st.number_input("위도 (Latitude)", value=37.5665, format="%.6f", key="manual_lat")
            with col2:
                manual_lng = st.number_input("경도 (Longitude)", value=126.9780, format="%.6f", key="manual_lng")

            if st.button("🔍 좌표로 주소 찾기", key="manual_coords_lookup"):
                with st.spinner(f"좌표 ({manual_lat:.6f}, {manual_lng:.6f})를 주소로 변환 중입니다..."):
                    location_result = self.location_service.get_location_from_coords(manual_lat, manual_lng)
                    if location_result['success']:
                        st.success('✅ 좌표 기반 주소 변환 완료!')
                        return location_result
                    else:
                        # 🔧 상세한 오류 정보 표시
                        st.error(f"❌ 주소 변환 실패: {location_result['message']}")

                        # API 상태 정보 표시
                        api_status = self.location_service.get_api_status()
                        with st.expander("🔧 디버깅 정보"):
                            st.write("**API 상태:**")
                            st.json(api_status)
                            st.write("**오류 응답:**")
                            st.json(location_result)
                            st.write("**해결 방법:**")
                            if not api_status['vworld_api']['available']:
                                st.write("- `.env` 파일에 유효한 VWorld API 키를 설정해주세요")
                                st.write("- VWORLD_API_KEY 설정 필요")
                                st.write("- VWorld API 키 발급: https://www.vworld.kr")
                            else:
                                st.write("- VWorld API 키가 유효한지 확인해주세요")
                                st.write("- VWorld 개발자센터에서 키 상태 확인")
                        return None

        test_locations = {
            "서울시 강남구": (37.5175, 127.0473),
            "서울시 종로구": (37.5735, 126.9788),
            "부산시 해운대구": (35.1584, 129.1604),
            "대구시 중구": (35.8714, 128.5911),
            "대전시 서구": (36.3553, 127.2986),
        }

        st.info("🔧 **개발 중인 GPS 기능**: 브라우저 제약으로 자동 감지가 어려울 경우 아래 테스트 위치를 활용할 수 있습니다.")

        selected_test_location = st.selectbox(
            "🧪 테스트 위치 선택:",
            options=list(test_locations.keys()),
            key="test_location_selector",
        )

        if st.button("🔍 선택한 위치로 테스트", key="test_location_convert"):
            lat, lng = test_locations[selected_test_location]
            with st.spinner(f"테스트 좌표 ({lat:.6f}, {lng:.6f})를 주소로 변환 중입니다..."):
                location_result = self.location_service.get_location_from_coords(lat, lng)
                if location_result['success']:
                    st.success('✅ 테스트 위치 기반 주소 변환 완료!')
                    return location_result
                else:
                    # 🔧 상세한 오류 정보 표시
                    st.error(f"❌ 주소 변환 실패: {location_result['message']}")

                    # API 상태 정보 표시
                    api_status = self.location_service.get_api_status()
                    with st.expander("🔧 디버깅 정보"):
                        st.write("**API 상태:**")
                        st.json(api_status)
                        st.write("**오류 응답:**")
                        st.json(location_result)
                        st.write("**해결 방법:**")
                        if not api_status['vworld_api']['available']:
                            st.write("- `.env` 파일에 유효한 VWorld API 키를 설정해주세요")
                            st.write("- VWORLD_API_KEY 설정 필요")
                            st.write("- VWorld API 키 발급: https://www.vworld.kr")
                        else:
                            st.write("- VWorld API 키가 유효한지 확인해주세요")
                            st.write("- VWorld 개발자센터에서 키 상태 확인")
                    return None

        with st.expander("📱 GPS 사용 안내"):
            st.write("""
            **GPS 사용 팁**

            1. **권한 허용**: 브라우저 위치 권한을 허용해야 합니다.
            2. **HTTPS 환경**: 보안 연결(HTTPS)에서만 GPS가 동작합니다. (localhost 예외)
            3. **실외 환경**: 실내에서는 GPS 정확도가 낮을 수 있습니다.
            4. **대안 방법**: 자동 감지가 실패하면 좌표 직접 입력이나 수동 선택을 이용하세요.
            """)

        return None

    def _render_location_info(self, location_data: Dict[str, Any]) -> None:
        """선택된 위치 정보를 카드 형태로 표시합니다."""

        st.success("✅ 위치가 선택되었습니다")

        with st.container():
            col1, col2 = st.columns([2, 1])

            with col1:
                # 동 정보 표시 준비
                dong_info = self._get_dong_display_info(location_data)

                st.markdown(f"""
                **📍 선택된 위치**
                - **시/도**: {location_data.get('sido', 'N/A')}
                - **시/군/구**: {location_data.get('sigungu', 'N/A')}{dong_info}
                - **전체 주소**: {location_data.get('full_address', 'N/A')}
                - **선택 방법**: {self._get_method_display(location_data.get('method', 'unknown'))}
                """)

            with col2:
                # 위치 변경 버튼
                if st.button("🔄 위치 변경", key="change_location"):
                    SessionStateManager.clear_location_info()
                    st.session_state.pop('_gps_ui_open', None)
                    st.rerun()

                # 좌표 정보 (GPS인 경우만)
                coords = location_data.get('coords')
                if coords and self.config.location.show_coordinate_info:
                    st.markdown(f"""
                    **📐 좌표 정보**
                    - 위도: {coords.get('lat', 'N/A')}
                    - 경도: {coords.get('lng', 'N/A')}
                    """)

    def _get_method_display(self, method: str) -> str:
        """위치 선택 방법을 사용자 친화적으로 표시합니다."""
        method_map = {
            'gps': '📍 GPS 자동 감지',
            'manual': '🗺️ 수동 선택',
            'vworld_api': '📍 GPS (VWorld)',
            'unknown': '❓ 알 수 없음'
        }
        return method_map.get(method, f'❓ {method}')

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

    def _get_dong_display_info(self, location_data: Dict[str, Any]) -> str:
        """동 정보가 있을 때 표시할 문자열을 반환합니다."""
        dong = location_data.get('dong', '')
        dong_type = location_data.get('dong_type', '')

        if dong:
            type_display = f"({dong_type})" if dong_type else ""
            return f"\n                - **동**: {dong}{type_display}"

        return ""  # 동 정보가 없으면 빈 문자열