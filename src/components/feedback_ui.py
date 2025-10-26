"""
사용자 피드백 수집 UI 컴포넌트

VisionService의 분석 결과에 대한 사용자 피드백을 수집하는 인터페이스를 제공합니다.
분류 정확성, 크기 추정 정확성, 전반적 만족도를 평가하고 개선 의견을 수집합니다.
"""
import streamlit as st
from typing import Dict, Any, Optional
import json
import uuid
from datetime import datetime

from src.components.base_ui import BaseUIComponent, UIComponent


class FeedbackUI(BaseUIComponent):
    """사용자 피드백 수집 UI 컴포넌트"""

    def __init__(self, vision_result: dict, session_id: Optional[str] = None):
        component_info = UIComponent(
            title="피드백 수집",
            description="분석 결과에 대한 피드백을 제공해주세요",
            icon="📝"
        )
        super().__init__(component_info)

        self.vision_result = vision_result
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.feedback_id = f"feedback_{self.session_id}_{int(datetime.now().timestamp())}"

    def render(self, **kwargs) -> Optional[Dict[str, Any]]:
        """피드백 수집 인터페이스를 렌더링합니다."""

        # 피드백 섹션 시작
        st.divider()
        st.subheader("📝 분석 결과가 정확한지 피드백을 주세요!")
        st.write("여러분의 피드백은 AI 모델을 개선하는데 소중한 자료가 됩니다. 🙏")

        # 분석 결과 요약 표시
        self._render_analysis_summary()

        # 피드백 수집 폼
        with st.form(key=f"feedback_form_{self.feedback_id}"):

            # 1. 분류 정확성 평가
            classification_feedback = self._render_classification_feedback()

            # 2. 크기 추정 정확성 평가
            size_feedback = self._render_size_feedback()

            # 3. 전반적 만족도
            overall_satisfaction = self._render_overall_satisfaction()

            # 4. 추가 의견
            additional_comments = self._render_additional_feedback()

            # 5. 제출 버튼
            submitted = st.form_submit_button(
                "피드백 제출 🚀",
                type="primary",
                use_container_width=True
            )

            if submitted:
                feedback_data = {
                    'feedback_id': self.feedback_id,
                    'session_id': self.session_id,
                    'timestamp': datetime.now().isoformat(),
                    'vision_result': self.vision_result,
                    'classification': classification_feedback,
                    'size': size_feedback,
                    'overall_satisfaction': overall_satisfaction,
                    'additional_comments': additional_comments
                }

                # 피드백 데이터 표시 (개발/테스트용)
                self._display_feedback_data(feedback_data)

                # 감사 메시지
                st.success("🎉 소중한 피드백 감사합니다!")
                st.balloons()

                return feedback_data

        return None

    def _render_analysis_summary(self) -> None:
        """분석 결과 요약을 표시합니다."""

        st.write("**🔍 현재 분석 결과:**")

        col1, col2 = st.columns(2)

        with col1:
            detected_item = self.vision_result.get('category', '알 수 없음')
            confidence = self.vision_result.get('confidence', 0)
            st.info(f"**감지된 물건:** {detected_item}")
            st.progress(confidence, text=f"신뢰도: {confidence:.1%}")

        with col2:
            size_info = self.vision_result.get('size_estimation', {})
            if size_info:
                width = size_info.get('width_cm', 0)
                height = size_info.get('height_cm', 0)
                st.info(f"**추정 크기:** {width:.1f}cm × {height:.1f}cm")
            else:
                st.info("**크기 정보:** 측정되지 않음")

    def _render_classification_feedback(self) -> Dict[str, Any]:
        """물건 분류 정확성 피드백을 수집합니다."""

        st.subheader("🎯 물건 분류가 정확한가요?")

        # 분류 정확성 평가
        is_correct = st.radio(
            "분류 결과가 맞나요?",
            ["정확함 ✅", "부정확함 ❌"],
            key=f"classification_correct_{self.feedback_id}",
            horizontal=True
        )

        corrected_label = None
        if is_correct == "부정확함 ❌":
            corrected_label = st.text_input(
                "올바른 물건 이름을 입력해주세요:",
                placeholder="예: 의자, 책상, 냉장고 등",
                key=f"corrected_label_{self.feedback_id}"
            )

        # 신뢰도 평가
        confidence_rating = st.slider(
            "분류 결과에 대한 신뢰도는?",
            min_value=1,
            max_value=5,
            value=3,
            format="%d점",
            help="1점: 매우 부정확, 5점: 매우 정확",
            key=f"classification_confidence_{self.feedback_id}"
        )

        return {
            'is_correct': is_correct == "정확함 ✅",
            'corrected_label': corrected_label.strip() if corrected_label else None,
            'confidence_rating': confidence_rating
        }

    def _render_size_feedback(self) -> Dict[str, Any]:
        """크기 추정 정확성 피드백을 수집합니다."""

        st.subheader("📏 크기 추정이 정확한가요?")

        size_info = self.vision_result.get('size_estimation', {})
        if not size_info:
            st.info("크기 측정이 수행되지 않았습니다.")
            return {
                'is_correct': None,
                'corrected_size': None,
                'confidence_rating': None
            }

        # 크기 정확성 평가
        is_correct = st.radio(
            "크기 추정이 맞나요?",
            ["정확함 ✅", "부정확함 ❌", "모르겠음 🤔"],
            key=f"size_correct_{self.feedback_id}",
            horizontal=True
        )

        corrected_size = None
        if is_correct == "부정확함 ❌":
            st.write("**실제 크기를 입력해주세요:**")
            col1, col2 = st.columns(2)

            with col1:
                width = st.number_input(
                    "가로 (cm)",
                    min_value=0.1,
                    max_value=1000.0,
                    step=0.1,
                    key=f"corrected_width_{self.feedback_id}"
                )

            with col2:
                height = st.number_input(
                    "세로 (cm)",
                    min_value=0.1,
                    max_value=1000.0,
                    step=0.1,
                    key=f"corrected_height_{self.feedback_id}"
                )

            corrected_size = {'width_cm': width, 'height_cm': height}

        # 신뢰도 평가 (크기 정보가 있을 때만)
        confidence_rating = None
        if is_correct != "모르겠음 🤔":
            confidence_rating = st.slider(
                "크기 추정에 대한 신뢰도는?",
                min_value=1,
                max_value=5,
                value=3,
                format="%d점",
                help="1점: 매우 부정확, 5점: 매우 정확",
                key=f"size_confidence_{self.feedback_id}"
            )

        return {
            'is_correct': is_correct == "정확함 ✅" if is_correct != "모르겠음 🤔" else None,
            'corrected_size': corrected_size,
            'confidence_rating': confidence_rating
        }

    def _render_overall_satisfaction(self) -> int:
        """전반적 만족도를 수집합니다."""

        st.subheader("⭐ 전반적으로 만족하시나요?")

        satisfaction = st.radio(
            "서비스 이용 만족도:",
            ["매우 불만족 😞", "불만족 😐", "보통 😊", "만족 😄", "매우 만족 🤩"],
            index=2,  # 기본값: 보통
            key=f"overall_satisfaction_{self.feedback_id}",
            horizontal=True
        )

        # 점수로 변환
        satisfaction_scores = {
            "매우 불만족 😞": 1,
            "불만족 😐": 2,
            "보통 😊": 3,
            "만족 😄": 4,
            "매우 만족 🤩": 5
        }

        return satisfaction_scores[satisfaction]

    def _render_additional_feedback(self) -> str:
        """추가 의견을 수집합니다."""

        st.subheader("💭 추가 의견 (선택사항)")

        additional_comments = st.text_area(
            "개선 사항이나 추가 의견이 있으시면 자유롭게 작성해주세요:",
            placeholder="예: 분류가 틀렸습니다, 크기 측정 방법을 개선해주세요, UI가 사용하기 편합니다 등",
            height=100,
            key=f"additional_comments_{self.feedback_id}"
        )

        return additional_comments.strip() if additional_comments else ""

    def _display_feedback_data(self, feedback_data: Dict[str, Any]) -> None:
        """수집된 피드백 데이터를 표시합니다 (개발/테스트용)."""

        with st.expander("🔍 수집된 피드백 데이터 (개발용)", expanded=False):
            st.json(feedback_data, expanded=False)

            # 요약 정보
            st.write("**피드백 요약:**")

            classification = feedback_data['classification']
            size = feedback_data['size']

            col1, col2, col3 = st.columns(3)

            with col1:
                classification_status = "✅ 정확" if classification['is_correct'] else "❌ 부정확"
                st.metric("분류 평가", classification_status, f"신뢰도: {classification['confidence_rating']}/5")

            with col2:
                if size['is_correct'] is not None:
                    size_status = "✅ 정확" if size['is_correct'] else "❌ 부정확"
                    confidence = f"신뢰도: {size['confidence_rating']}/5" if size['confidence_rating'] else "평가안함"
                    st.metric("크기 평가", size_status, confidence)
                else:
                    st.metric("크기 평가", "📏 측정안됨", "")

            with col3:
                satisfaction_text = f"⭐ {feedback_data['overall_satisfaction']}/5"
                st.metric("전반적 만족도", satisfaction_text, "")