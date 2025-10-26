
"""
AI 분석 결과에 대한 간단한 확인 UI 컴포넌트

설계서 Phase 1에 따라 복잡한 피드백 시스템을 간단한 확인 시스템으로 축소하였습니다.
"""
import streamlit as st
from typing import Optional, Dict, Any
from src.app.core.app_factory import ApplicationContext
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfirmationUI:
    """
    AI 분석 결과에 대한 사용자의 간단한 확인을 받는 UI 컴포넌트입니다.
    Phase 1 설계: 복잡한 피드백 대신 간단한 확인/수정 프로세스
    """

    def __init__(self, app_context: ApplicationContext, image_id: str, analysis_result: dict):
        self.app_context = app_context
        self.image_id = image_id
        self.analysis_result = analysis_result
        self.confirmation_service = self.app_context.get_service('confirmation_service')
        # 세션 ID를 일관되게 유지
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())[:8]
        self.session_id = st.session_state.session_id

    def render(self) -> Optional[Dict[str, Any]]:
        """UI를 렌더링하고 사용자 입력을 처리합니다."""
        if not self.confirmation_service:
            st.error("Confirmation service를 로드할 수 없습니다. 관리자에게 문의하세요.")
            logger.error("Failed to load confirmation_service.")
            return None

        st.divider()
        st.subheader("✅ 분석 결과를 한 번만 체크해주세요")
        st.caption("잘못된 부분이 있다면 바로 고쳐서 다음 단계(수수료 안내)로 이어집니다.")

        # 진행 상태 표시
        self._render_progress_indicator()

        # 빠른 확인 옵션
        quick_confirm = self._render_quick_confirm_option()
        if quick_confirm:
            return quick_confirm

        # 분석 결과 요약 표시
        self._render_analysis_summary()

        # 확인 폼
        with st.form(key=f"confirmation_form_{self.image_id}_{int(datetime.now().timestamp())}"):
            classification_result = self._render_classification_section()
            size_result = self._render_size_section()
            notes = self._render_notes_section()

            submitted = st.form_submit_button(
                "결과 확인 완료",
                type="primary",
                use_container_width=True
            )

        if not submitted:
            return None

        return self._handle_submission(classification_result, size_result, notes)

    def _render_analysis_summary(self):
        """현재 분석 결과를 요약해서 보여줍니다."""
        object_name = self.analysis_result.get('object_name', '알 수 없음')
        primary_category = self.analysis_result.get('primary_category', 'MISC')
        secondary_category = self.analysis_result.get('secondary_category', 'MISC_UNCLASS')
        confidence = float(self.analysis_result.get('confidence', 0))
        dimensions = self.analysis_result.get('dimensions', {}) or {}

        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**감지된 품목:** {object_name}")
            st.write(f"**1차 분류:** {primary_category}")
            st.write(f"**2차 분류:** {secondary_category}")

            if dimensions:
                width = dimensions.get('width_cm')
                height = dimensions.get('height_cm')
                depth = dimensions.get('depth_cm')
                items = []
                if width:
                    items.append(f"가로 {width}cm")
                if height:
                    items.append(f"세로 {height}cm")
                if depth:
                    items.append(f"높이 {depth}cm")
                st.write("**추정 크기:** " + ", ".join(items) if items else "크기 정보 없음")
            else:
                st.write("**추정 크기:** 정보 없음")

        with col2:
            st.metric("신뢰도", f"{confidence:.0%}")

    def _render_progress_indicator(self):
        """진행 상태를 표시합니다."""
        progress_steps = ["📸 이미지 업로드", "🧠 AI 분석", "✅ 결과 확인", "🚛 배출 안내"]
        current_step = 2  # 결과 확인 단계

        cols = st.columns(len(progress_steps))
        for i, step in enumerate(progress_steps):
            with cols[i]:
                if i < current_step:
                    st.markdown(f"✅ {step}")
                elif i == current_step:
                    st.markdown(f"🔄 **{step}**")
                else:
                    st.markdown(f"⏸️ {step}")

        # 진행률 표시
        progress = (current_step + 1) / len(progress_steps)
        st.progress(progress)
        st.caption(f"진행률: {progress:.0%} ({current_step + 1}/{len(progress_steps)})")

    def _render_quick_confirm_option(self) -> Optional[Dict[str, Any]]:
        """빠른 확인 옵션을 렌더링합니다."""
        st.markdown("---")

        # 빠른 확인 섹션
        with st.expander("⚡ 빠른 확인 (분석 결과가 정확한 경우)", expanded=False):
            st.info("분석 결과가 정확하다면 아래 버튼을 클릭해서 바로 다음 단계로 진행하세요!")

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("👍 분석 결과가 정확합니다",
                           type="primary",
                           use_container_width=True,
                           key=f"quick_confirm_{self.image_id}"):
                    return self._create_quick_confirmation_result()

            with col2:
                if st.button("📝 상세 검토가 필요합니다",
                           use_container_width=True,
                           key=f"detailed_review_{self.image_id}"):
                    st.info("아래에서 상세히 확인해주세요.")

        st.markdown("---")
        return None

    def _create_quick_confirmation_result(self) -> Dict[str, Any]:
        """빠른 확인 결과를 생성합니다."""
        # 기본적으로 정확함으로 설정된 결과 생성
        classification_result = {
            "is_correct": True,
            "confidence_rating": 4,  # 기본 신뢰도
            "status": "confirmed",
            "override": None,
            "user_feedback": {
                "classification_accurate": True,
                "confidence_level": 4,
                "corrected_label": None,
                "corrected_category": None
            }
        }

        size_result = {
            "is_correct": True,
            "confidence_rating": 4,  # 기본 신뢰도
            "status": "confirmed",
            "override": None,
            "user_feedback": {
                "size_available": True,
                "size_accurate": True,
                "confidence_level": 4,
                "user_provided_size": False
            }
        }

        notes = ""  # 빠른 확인시에는 메모 없음

        # 빠른 확인 표시
        st.success("⚡ 빠른 확인이 완료되었습니다!")
        st.balloons()

        return self._handle_submission(classification_result, size_result, notes)

    def _render_classification_section(self) -> Dict[str, Any]:
        """분류 결과 확인/수정을 처리합니다."""
        st.subheader("🎯 분류 결과")

        # 1단계: 기본 확인
        choice = st.radio(
            "분류 결과가 정확한가요?",
            ("정확합니다", "부정확합니다"),
            key=f"classification_choice_{self.image_id}",
            index=0,
            help="AI가 분석한 물건 분류가 맞는지 확인해주세요"
        )

        # 2단계: 신뢰도 평가 (항상 표시)
        confidence_rating = st.slider(
            "분류 결과에 대한 신뢰도를 평가해주세요",
            min_value=1,
            max_value=5,
            value=4 if choice == "정확합니다" else 2,
            help="1=매우 부정확, 2=부정확, 3=보통, 4=정확, 5=매우 정확",
            key=f"classification_confidence_{self.image_id}"
        )

        corrected_label = None
        corrected_category = None

        # 3단계: 수정 입력 (부정확한 경우에만)
        if choice == "부정확합니다":
            st.info("💡 올바른 정보를 입력해주시면 AI 학습에 도움이 됩니다.")

            col1, col2 = st.columns(2)

            with col1:
                corrected_label = st.text_input(
                    "올바른 물건 이름",
                    value="",
                    placeholder="예: 2인용 소파, 양문형 냉장고",
                    key=f"corrected_label_{self.image_id}",
                    help="정확한 물건 이름을 입력해주세요"
                ).strip()

            with col2:
                # 간단한 카테고리 선택
                category_options = [
                    "선택하지 않음",
                    "가구 (침대, 소파, 테이블 등)",
                    "가전 (냉장고, 세탁기, TV 등)",
                    "생활용품 (싱크대, 욕조 등)",
                    "스포츠/레저 (운동기구, 자전거 등)",
                    "기타"
                ]
                corrected_category = st.selectbox(
                    "올바른 분류",
                    options=category_options,
                    key=f"corrected_category_{self.image_id}",
                    help="대략적인 분류를 선택해주세요"
                )

        # 결과 구성
        is_correct = choice == "정확합니다"
        override_data = None

        if not is_correct and (corrected_label or corrected_category != "선택하지 않음"):
            override_data = {
                "object_name": corrected_label if corrected_label else None,
                "category_feedback": corrected_category if corrected_category != "선택하지 않음" else None
            }

        return {
            "is_correct": is_correct,
            "confidence_rating": confidence_rating,
            "status": "confirmed" if is_correct else "needs_review",
            "override": override_data,
            "user_feedback": {
                "classification_accurate": is_correct,
                "confidence_level": confidence_rating,
                "corrected_label": corrected_label,
                "corrected_category": corrected_category if corrected_category != "선택하지 않음" else None
            }
        }

    def _render_size_section(self) -> Dict[str, Any]:
        """크기 추정 확인/수정을 처리합니다."""
        st.subheader("📏 크기 추정")
        dimensions = self.analysis_result.get('dimensions', {}) or {}

        # 크기 정보가 없는 경우
        if not dimensions or not any(dimensions.values()):
            st.info("크기 정보가 제공되지 않았습니다.")

            # 사용자가 직접 입력할 수 있는 옵션 제공
            provide_size = st.checkbox(
                "직접 크기를 입력하시겠습니까?",
                key=f"provide_size_{self.image_id}",
                help="크기 정보를 제공하시면 수수료 계산에 도움이 됩니다"
            )

            if provide_size:
                st.info("실제 크기를 입력해주세요. (단위: cm)")
                col1, col2, col3 = st.columns(3)

                with col1:
                    width = st.number_input(
                        "가로 (cm)",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        key=f"manual_width_{self.image_id}"
                    )
                with col2:
                    height = st.number_input(
                        "세로 (cm)",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        key=f"manual_height_{self.image_id}"
                    )
                with col3:
                    depth = st.number_input(
                        "높이/깊이 (cm)",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        key=f"manual_depth_{self.image_id}"
                    )

                if any([width > 0, height > 0, depth > 0]):
                    return {
                        "status": "user_provided",
                        "is_correct": None,
                        "confidence_rating": 3,  # 기본값
                        "override": {
                            "width_cm": width if width > 0 else None,
                            "height_cm": height if height > 0 else None,
                            "depth_cm": depth if depth > 0 else None,
                            "dimension_sum_cm": width + height + depth
                        },
                        "user_feedback": {
                            "size_available": True,
                            "size_accurate": None,
                            "user_provided_size": True,
                            "confidence_level": 3
                        }
                    }

            return {
                "status": "unknown",
                "is_correct": None,
                "confidence_rating": None,
                "override": None,
                "user_feedback": {
                    "size_available": False,
                    "size_accurate": None,
                    "user_provided_size": False
                }
            }

        # 크기 정보가 있는 경우
        width_default = float(dimensions.get('width_cm', 0))
        height_default = float(dimensions.get('height_cm', 0))
        depth_default = float(dimensions.get('depth_cm', 0))

        # 1단계: 기본 확인
        choice = st.radio(
            "크기 추정이 정확한가요?",
            ("정확합니다", "부정확합니다", "잘 모르겠어요"),
            key=f"size_choice_{self.image_id}",
            index=0,
            help="AI가 추정한 크기가 실제와 비슷한지 확인해주세요"
        )

        # 2단계: 신뢰도 평가 (잘 모르겠어요가 아닌 경우)
        confidence_rating = None
        if choice != "잘 모르겠어요":
            confidence_rating = st.slider(
                "크기 추정에 대한 신뢰도를 평가해주세요",
                min_value=1,
                max_value=5,
                value=4 if choice == "정확합니다" else 2,
                help="1=매우 부정확, 2=부정확, 3=보통, 4=정확, 5=매우 정확",
                key=f"size_confidence_{self.image_id}"
            )

        # 결과 처리
        if choice == "정확합니다":
            return {
                "status": "confirmed",
                "is_correct": True,
                "confidence_rating": confidence_rating,
                "override": None,
                "user_feedback": {
                    "size_available": True,
                    "size_accurate": True,
                    "confidence_level": confidence_rating,
                    "user_provided_size": False
                }
            }

        elif choice == "잘 모르겠어요":
            return {
                "status": "unknown",
                "is_correct": None,
                "confidence_rating": None,
                "override": None,
                "user_feedback": {
                    "size_available": True,
                    "size_accurate": None,
                    "user_provided_size": False
                }
            }

        # 3단계: 수정 입력 (부정확한 경우)
        st.info("💡 정확한 크기를 입력해주시면 정확한 수수료 계산에 도움이 됩니다.")

        # 측정 팁 제공
        with st.expander("📐 측정 팁", expanded=False):
            st.markdown("""
            **정확한 측정을 위한 팁:**
            - **가로**: 물건의 가장 긴 폭
            - **세로**: 물건의 깊이 또는 앞뒤 길이
            - **높이**: 바닥에서 가장 높은 부분까지
            - 단위는 cm로 입력해주세요
            - 대략적인 크기라도 괜찮습니다
            """)

        col1, col2, col3 = st.columns(3)

        with col1:
            width = st.number_input(
                "가로 (cm)",
                min_value=0.0,
                value=width_default,
                step=1.0,
                key=f"corrected_width_{self.image_id}",
                help="물건의 가장 긴 폭"
            )
        with col2:
            height = st.number_input(
                "세로 (cm)",
                min_value=0.0,
                value=height_default,
                step=1.0,
                key=f"corrected_height_{self.image_id}",
                help="물건의 깊이 또는 앞뒤 길이"
            )
        with col3:
            depth = st.number_input(
                "높이 (cm)",
                min_value=0.0,
                value=depth_default,
                step=1.0,
                key=f"corrected_depth_{self.image_id}",
                help="바닥에서 가장 높은 부분까지"
            )

        # 크기 합계 자동 계산 및 표시
        dimension_sum = width + height + depth
        if dimension_sum > 0:
            st.info(f"📊 **크기 합계**: {dimension_sum:.0f}cm (가로 + 세로 + 높이)")

        return {
            "status": "needs_review",
            "is_correct": False,
            "confidence_rating": confidence_rating,
            "override": {
                "width_cm": width if width > 0 else None,
                "height_cm": height if height > 0 else None,
                "depth_cm": depth if depth > 0 else None,
                "dimension_sum_cm": dimension_sum if dimension_sum > 0 else None
            },
            "user_feedback": {
                "size_available": True,
                "size_accurate": False,
                "confidence_level": confidence_rating,
                "user_provided_size": True,
                "corrected_dimensions": {
                    "width_cm": width,
                    "height_cm": height,
                    "depth_cm": depth,
                    "dimension_sum_cm": dimension_sum
                }
            }
        }

    def _render_notes_section(self) -> str:
        """추가 메모를 입력합니다."""
        return st.text_area(
            "추가로 알려주실 내용이 있다면 적어주세요 (선택)",
            key=f"confirmation_notes_{self.image_id}",
            placeholder="예: 3인용 소파지만 분리형입니다, 팔걸이가 없습니다 등"
        ).strip()

    def _render_progress_indicator(self) -> None:
        """진행 상태를 시각적으로 표시합니다."""
        st.info("📍 **진행 단계**: 이미지 업로드 → AI 분석 → **결과 확인** → 배출 방법 안내")

    def _render_quick_confirm_option(self) -> Optional[Dict[str, Any]]:
        """빠른 확인 옵션을 제공합니다 (정확한 분석일 때 빠르게 진행)."""
        st.markdown("---")
        st.markdown("#### 🚀 빠른 확인")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("**분석 결과가 정확하다면 빠르게 진행하세요!**")
            st.caption("물건 이름과 크기가 모두 맞다면 바로 배출 방법을 확인할 수 있습니다.")

        with col2:
            if st.button("✅ 정확합니다! 바로 진행", type="primary", use_container_width=True, key=f"quick_confirm_{self.image_id}"):
                # 빠른 확인 처리
                return self._process_quick_confirmation()

        st.markdown("---")
        st.markdown("#### 📋 상세 확인")
        st.caption("수정하거나 더 자세히 확인하고 싶다면 아래에서 단계별로 진행하세요.")

        return None

    def _process_quick_confirmation(self) -> Dict[str, Any]:
        """빠른 확인을 처리합니다."""
        try:
            # 빠른 확인용 기본 피드백 데이터 구성
            quick_feedback = {
                "classification": {
                    "classification_accurate": True,
                    "confidence_level": 4,  # 기본 신뢰도 4
                    "corrected_label": None,
                    "corrected_category": None
                },
                "size": {
                    "size_available": bool(self.analysis_result.get('dimensions')),
                    "size_accurate": True if self.analysis_result.get('dimensions') else None,
                    "confidence_level": 4 if self.analysis_result.get('dimensions') else None,
                    "user_provided_size": False,
                    "corrected_dimensions": None
                },
                "overall": {
                    "user_confirmed": True,
                    "additional_notes": None,
                    "feedback_timestamp": datetime.now().isoformat()
                }
            }

            # ConfirmationService를 통해 저장
            if self.confirmation_service:
                save_result = self.confirmation_service.save_confirmation(
                    session_id=self.session_id,
                    image_id=self.image_id,
                    original_analysis=self.analysis_result,
                    is_correct=True,
                    corrected_data={
                        "feedback_details": quick_feedback
                    }
                )

                if save_result and save_result.get('success'):
                    st.success("✅ 분석 결과를 확인했습니다!")
                    st.info("💡 빠른 확인을 통해 AI 학습에 도움을 주셨습니다!")
                    st.balloons()

                    # 확인 결과 구성
                    confirmation_result = {
                        "confirmation_id": save_result.get('confirmation_id'),
                        "session_id": self.session_id,
                        "image_id": self.image_id,
                        "timestamp": datetime.now().isoformat(),
                        "original_analysis": self.analysis_result,
                        "user_confirmed": True,
                        "quick_confirm": True,
                        "comprehensive_feedback": quick_feedback
                    }

                    # 세션 상태에 저장
                    st.session_state.confirmed_analysis = confirmation_result

                    # 배출 안내로 바로 이동
                    if st.button("🚛 배출 방법 안내 보기", type="primary", use_container_width=True, key=f"disposal_guide_{self.image_id}"):
                        st.session_state.show_disposal_guide = True
                        st.rerun()

                    return confirmation_result
                else:
                    st.error("저장 중 오류가 발생했습니다. 상세 확인을 통해 진행해주세요.")
                    return None
            else:
                st.error("Confirmation service를 사용할 수 없습니다.")
                return None

        except Exception as e:
            logger.error(f"Error during quick confirmation: {e}", exc_info=True)
            st.error("빠른 확인 중 오류가 발생했습니다. 상세 확인을 통해 진행해주세요.")
            return None

    def _handle_submission(self, classification_result: Dict[str, Any],
                          size_result: Dict[str, Any], notes: str) -> Dict[str, Any]:
        """확인 결과를 처리하고 저장합니다."""
        try:
            # 사용자 확인 상태 판정 (개선된 로직)
            classification_confirmed = classification_result.get("is_correct", False)
            size_confirmed = size_result.get("is_correct")  # None, True, False 가능

            # 전체적으로 확인된 상태인지 판단
            user_confirmed = (
                classification_confirmed and
                (size_confirmed is True or size_confirmed is None)  # 크기는 모르는 것도 허용
            )

            # 종합 피드백 데이터 구성
            comprehensive_feedback = {
                "classification": classification_result.get("user_feedback", {}),
                "size": size_result.get("user_feedback", {}),
                "overall": {
                    "user_confirmed": user_confirmed,
                    "additional_notes": notes or None,
                    "feedback_timestamp": datetime.now().isoformat()
                }
            }

            confirmation_result = {
                "confirmation_id": str(uuid.uuid4()),
                "session_id": self.session_id,
                "image_id": self.image_id,
                "timestamp": datetime.now().isoformat(),
                "original_analysis": self.analysis_result,
                "user_confirmed": user_confirmed,
                "classification_result": classification_result,
                "size_result": size_result,
                "notes": notes or None,
                "comprehensive_feedback": comprehensive_feedback  # 새로운 구조화된 피드백
            }

            # ConfirmationService를 통해 저장 (개선된 데이터 구조)
            if self.confirmation_service:
                save_result = self.confirmation_service.save_confirmation(
                    session_id=self.session_id,
                    image_id=self.image_id,
                    original_analysis=self.analysis_result,
                    is_correct=user_confirmed,
                    corrected_data={
                        "classification": classification_result.get("override"),
                        "size": size_result.get("override"),
                        "notes": notes,
                        "feedback_details": comprehensive_feedback  # 상세 피드백 포함
                    }
                )

                # 사용자 경험 개선된 메시지
                if user_confirmed:
                    st.success("✅ 분석 결과를 확인했습니다!")

                    # 피드백 감사 메시지
                    feedback_count = 0
                    if classification_result.get("confidence_rating"):
                        feedback_count += 1
                    if size_result.get("confidence_rating"):
                        feedback_count += 1

                    if feedback_count > 0:
                        st.info(f"💡 소중한 피드백 {feedback_count}개를 주셨습니다. AI 개선에 큰 도움이 됩니다!")

                    st.balloons()

                    # 세션 상태에 확인된 분석 결과 저장
                    st.session_state.confirmed_analysis = confirmation_result

                    # 배출 안내 페이지로 이동 버튼
                    if st.button("🚛 배출 방법 안내 보기", type="primary", use_container_width=True):
                        st.session_state.show_disposal_guide = True
                        st.rerun()
                else:
                    st.warning("⚠️ 수정이 필요한 내역이 저장되었습니다.")
                    st.info("운영자가 검토하여 AI 정확도 개선에 활용하겠습니다. 감사합니다!")

            return confirmation_result

        except Exception as e:
            st.error("오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            logger.error(f"Error during confirmation submission: {e}", exc_info=True)
            return None

