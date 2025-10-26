"""
배출 방법 안내 UI 컴포넌트

Phase 1 완성: 확인 완료 후 자연스러운 배출 안내 제공
"""
import streamlit as st
from typing import Dict, Any, Optional
from src.app.core.app_factory import ApplicationContext
import logging

logger = logging.getLogger(__name__)


class DisposalGuideUI:
    """
    대형폐기물 배출 방법을 안내하는 UI 컴포넌트
    """

    def __init__(self, app_context: ApplicationContext):
        self.app_context = app_context
        self.district_service = app_context.get_service('district_service')
        self.location_service = app_context.get_service('location_service')

    def render(self, confirmed_analysis: Optional[Dict[str, Any]] = None):
        """배출 방법 안내를 렌더링합니다."""
        st.header("🚛 대형폐기물 배출 방법 안내")

        # 확인된 분석 결과가 있는 경우 요약 표시
        if confirmed_analysis:
            self._render_confirmed_analysis_summary(confirmed_analysis)
            st.divider()

        # 지역별 배출 방법 안내
        self._render_location_based_guide()

        # 일반적인 배출 절차 안내
        self._render_general_disposal_process()

        # 주의사항 및 추가 정보
        self._render_additional_info()

    def _render_confirmed_analysis_summary(self, confirmed_analysis: Dict[str, Any]):
        """확인된 분석 결과 요약"""
        st.subheader("✅ 확인된 분석 결과")

        original_analysis = confirmed_analysis.get('original_analysis', {})
        classification_result = confirmed_analysis.get('classification_result', {})
        size_result = confirmed_analysis.get('size_result', {})

        # 최종 물건 정보
        object_name = original_analysis.get('object_name', '알 수 없음')
        if classification_result.get('override'):
            object_name = classification_result['override'].get('object_name', object_name)

        primary_category = original_analysis.get('primary_category', 'MISC')
        secondary_category = original_analysis.get('secondary_category', 'MISC_UNCLASS')

        col1, col2 = st.columns(2)

        with col1:
            st.info(f"**물건:** {object_name}")
            st.info(f"**분류:** {primary_category} → {secondary_category}")

        with col2:
            # 크기 정보
            dimensions = original_analysis.get('dimensions', {})
            if size_result.get('override'):
                dimensions.update(size_result['override'])

            if dimensions and any(dimensions.values()):
                width = dimensions.get('width_cm', 0)
                height = dimensions.get('height_cm', 0)
                depth = dimensions.get('depth_cm', 0)
                dimension_sum = dimensions.get('dimension_sum_cm', width + height + depth)

                st.info(f"**예상 크기:** {width}×{height}×{depth}cm")
                st.info(f"**크기 합계:** {dimension_sum}cm")
            else:
                st.info("**크기:** 정보 없음")

    def _render_location_based_guide(self):
        """지역별 배출 방법 안내"""
        st.subheader("📍 지역별 배출 방법")

        # 세션에서 현재 위치 정보 가져오기
        if hasattr(st.session_state, 'current_location') and st.session_state.current_location:
            location_data = st.session_state.current_location
            sido = location_data.get('sido', '')
            sigungu = location_data.get('sigungu', '')

            if sido and sigungu:
                st.success(f"🎯 **현재 선택된 지역:** {sido} {sigungu}")

                # 지역별 맞춤 안내
                if '인천' in sido:
                    self._render_incheon_guide(sigungu)
                else:
                    self._render_general_regional_guide(sido, sigungu)
            else:
                st.warning("위치 정보가 설정되지 않았습니다. 위에서 지역을 선택해주세요.")
        else:
            st.warning("위치 정보가 없습니다. 메인 페이지에서 지역을 선택해주세요.")

    def _render_incheon_guide(self, sigungu: str):
        """인천광역시 배출 안내"""
        st.markdown("### 🏢 인천광역시 대형폐기물 배출 절차")

        with st.expander("📞 신고 및 접수", expanded=True):
            st.markdown("""
            **1. 인터넷 신고 (추천)**
            - 인천광역시 대형폐기물 신고 사이트
            - 24시간 언제든지 신고 가능

            **2. 전화 신고**
            - 각 구청별 전담 번호
            - 평일 09:00~18:00
            """)

        with st.expander("💰 수수료 안내"):
            st.markdown(f"""
            **{sigungu} 수수료 기준**
            - 가구류: 크기별 차등 적용
            - 가전제품: 품목별 고정 요금
            - 기타 생활용품: 크기 합계 기준

            ⚠️ **정확한 수수료는 신고 시 확인됩니다**
            """)

        with st.expander("📅 배출 방법"):
            st.markdown("""
            **배출 절차**
            1. 신고 접수 후 스티커 발급
            2. 스티커를 물건에 부착
            3. 지정된 배출일에 내놓기
            4. 수거 완료 확인

            **주의사항**
            - 스티커 없이 배출 시 수거 불가
            - 지정 장소 외 배출 금지
            """)

    def _render_general_regional_guide(self, sido: str, sigungu: str):
        """일반 지역 배출 안내"""
        st.markdown(f"### 🏛️ {sido} {sigungu} 대형폐기물 배출 안내")

        st.info("""
        **일반적인 배출 절차**
        1. 해당 지역 관할 주민센터나 구청에 신고
        2. 배출 수수료 납부
        3. 수수료 납부증명서 또는 스티커 부착
        4. 지정된 날짜에 지정 장소에 배출
        """)

        st.warning(f"""
        **{sido} {sigungu} 정확한 정보**는 다음 방법으로 확인하세요:
        - 해당 지역 홈페이지 검색
        - 주민센터 전화 문의
        - 120 다산콜센터 문의
        """)

    def _render_general_disposal_process(self):
        """일반적인 배출 절차 안내"""
        st.subheader("📋 배출 절차 요약")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("""
            **1️⃣ 신고**
            - 인터넷/전화 신고
            - 물건 정보 입력
            - 배출 희망일 선택
            """)

        with col2:
            st.markdown("""
            **2️⃣ 수수료 납부**
            - 온라인 결제
            - 가상계좌 입금
            - 스티커 발급
            """)

        with col3:
            st.markdown("""
            **3️⃣ 배출**
            - 스티커 부착
            - 지정 장소 배출
            - 배출일 준수
            """)

        with col4:
            st.markdown("""
            **4️⃣ 수거**
            - 배출일 수거
            - 수거 확인
            - 완료 알림
            """)

    def _render_additional_info(self):
        """주의사항 및 추가 정보"""
        st.subheader("⚠️ 주의사항")

        with st.expander("배출 시 주의사항", expanded=True):
            st.warning("""
            **반드시 지켜야 할 사항:**
            - 신고 없이 배출 금지
            - 스티커 없이 배출 금지
            - 지정 장소 외 배출 금지
            - 지정일 외 배출 금지
            """)

        with st.expander("추가 도움말"):
            st.info("""
            **도움이 필요하시면:**
            - 120 다산콜센터: 전국 공통
            - 해당 지역 주민센터
            - 관할 구청 환경과

            **온라인 자료:**
            - 각 지자체 홈페이지
            - 대형폐기물 신고 사이트
            """)

        # 다음 단계 안내
        st.divider()
        st.success("""
        🎉 **배출 준비 완료!**
        위 안내에 따라 신고 접수를 진행하시면 됩니다.
        """)

        if st.button("🔄 새로운 물건 분석하기", type="primary"):
            # 세션 상태 초기화
            if hasattr(st.session_state, 'latest_analysis_result'):
                del st.session_state.latest_analysis_result
            if hasattr(st.session_state, 'confirmed_analysis'):
                del st.session_state.confirmed_analysis
            st.rerun()