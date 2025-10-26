"""
개선된 확인 UI - 계층 구조 기반

waste_types.json 계층 구조를 활용한 지능형 확인 UI입니다.
AI 분석 결과를 자동 매핑하고 사용자가 쉽게 수정할 수 있도록 지원합니다.
"""
import streamlit as st
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedConfirmationUI:
    """계층 구조 기반 개선된 확인 UI"""

    def __init__(self, app_context, image_id: str, analysis_result: dict):
        self.app_context = app_context
        self.image_id = image_id
        self.analysis_result = analysis_result

        # 서비스 로드
        self.waste_service = self.app_context.get_service('waste_classification_service')
        self.ai_mapper = self.app_context.get_service('ai_classification_mapper')
        self.confirmation_service = self.app_context.get_service('confirmation_service')

        # 세션 ID 관리
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())[:8]
        self.session_id = st.session_state.session_id

        # 매핑된 결과 생성
        self.mapped_result = self._create_mapped_result()

    def _create_mapped_result(self) -> Dict[str, Any]:
        """분석 결과를 새로운 계층 구조로 매핑합니다."""
        if not self.ai_mapper or not self.waste_service:
            return self.analysis_result

        try:
            # 1. 기존 분석 결과를 새 구조로 매핑
            mapped = self.ai_mapper.map_legacy_analysis(self.analysis_result)

            # 2. AI 추천으로 개선
            enhanced = self.ai_mapper.enhance_with_ai_suggestion(mapped, self.waste_service)

            return enhanced

        except Exception as e:
            logger.error(f"Error creating mapped result: {e}")
            return self.analysis_result

    def render(self) -> Optional[Dict[str, Any]]:
        """개선된 확인 UI를 렌더링합니다."""
        if not self._check_services():
            return None

        st.divider()
        st.subheader("✅ AI 분석 결과 확인")
        st.caption("새로운 계층 구조 기반으로 정확한 분류를 확인하고 수정하세요.")

        # 진행 상태 표시
        self._render_progress_indicator()

        # 빠른 확인 옵션
        quick_confirm = self._render_quick_confirm_option()
        if quick_confirm:
            return quick_confirm

        # 분석 결과 요약
        self._render_analysis_summary()

        # 메인 확인 섹션
        classification_result = self._render_enhanced_classification_section()
        size_result = self._render_size_section()
        notes = self._render_notes_section()

        # 제출 버튼
        if st.button("✅ 확인 완료", type="primary", use_container_width=True):
            return self._handle_submission(classification_result, size_result, notes)

        return None

    def _check_services(self) -> bool:
        """필수 서비스 가용성을 확인합니다."""
        missing_services = []

        if not self.waste_service:
            missing_services.append("WasteClassificationService")
        if not self.ai_mapper:
            missing_services.append("AIClassificationMapper")
        if not self.confirmation_service:
            missing_services.append("ConfirmationService")

        if missing_services:
            st.error(f"다음 서비스를 로드할 수 없습니다: {', '.join(missing_services)}")
            return False

        return True

    def _render_progress_indicator(self) -> None:
        """진행 상태를 표시합니다."""
        st.info("📍 **진행 단계**: 이미지 업로드 → AI 분석 → **✨ 지능형 결과 확인** → 배출 방법 안내")

    def _render_quick_confirm_option(self) -> Optional[Dict[str, Any]]:
        """빠른 확인 옵션을 제공합니다."""
        st.markdown("---")
        st.markdown("#### 🚀 빠른 확인")

        # AI 추천 정보 표시
        ai_suggestion = self.mapped_result.get('ai_suggestion', {})
        if ai_suggestion.get('has_ai_suggestion'):
            if ai_suggestion.get('recommendation_applied'):
                st.success("🎯 AI가 최적의 분류를 추천하여 자동 적용했습니다!")
            else:
                st.info("💡 AI 추천 분류와 기존 분류가 다릅니다. 상세 확인을 권장합니다.")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("**분석 결과가 정확하다면 빠르게 진행하세요!**")
            current_classification = f"{self.mapped_result.get('main_category', 'N/A')} > {self.mapped_result.get('sub_category', 'N/A')}"
            st.caption(f"현재 분류: {current_classification}")

        with col2:
            if st.button("✅ 정확합니다! 바로 진행", type="primary", use_container_width=True, key=f"enhanced_quick_confirm_{self.image_id}"):
                return self._process_quick_confirmation()

        st.markdown("---")
        return None

    def _render_analysis_summary(self) -> None:
        """분석 결과 요약을 표시합니다."""
        st.markdown("#### 📋 분석 결과 요약")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**🏷️ 물건**")
            st.code(self.mapped_result.get('object_name', 'N/A'))

        with col2:
            st.markdown("**📂 주분류**")
            st.code(self.mapped_result.get('main_category', 'N/A'))

        with col3:
            st.markdown("**📋 세분류**")
            st.code(self.mapped_result.get('sub_category', 'N/A'))

        # 매핑 정보 표시
        mapping_info = self.mapped_result.get('mapping_info', {})
        if mapping_info.get('needs_review'):
            st.warning("⚠️ 이 분류는 수동 검토가 필요할 수 있습니다.")

        # AI 추천 정보
        ai_suggestion = self.mapped_result.get('ai_suggestion', {})
        if ai_suggestion.get('differs_from_mapping'):
            with st.expander("🤖 AI 추천 정보"):
                st.info(f"AI 추천: {ai_suggestion.get('ai_main_category')} > {ai_suggestion.get('ai_sub_category')}")
                st.caption(f"신뢰도: {ai_suggestion.get('ai_confidence', 0):.2%}")

    def _render_enhanced_classification_section(self) -> Dict[str, Any]:
        """개선된 분류 확인 섹션을 렌더링합니다."""
        st.markdown("#### 🏷️ 분류 확인 및 수정")

        current_main = self.mapped_result.get('main_category', '')
        current_sub = self.mapped_result.get('sub_category', '')
        mapping_info = self.mapped_result.get('mapping_info', {})
        requires_user_input = mapping_info.get('requires_user_input', False)

        # 사용자 입력 필요 여부 확인
        if requires_user_input and current_main == '기타' and current_sub == '분류불가':
            st.warning("⚠️ AI가 분류하지 못한 물품입니다. 아래에서 물품 유형을 입력해주세요.")
            return self._render_user_input_section()

        # 1단계: 분류 정확성 확인
        col1, col2 = st.columns(2)

        with col1:
            is_correct = st.radio(
                "분류가 정확한가요?",
                options=["정확합니다", "수정이 필요합니다"],
                key=f"enhanced_classification_check_{self.image_id}"
            ) == "정확합니다"

        with col2:
            confidence_rating = st.slider(
                "분류 신뢰도",
                min_value=1,
                max_value=5,
                value=4 if is_correct else 2,
                help="1=매우 부정확, 2=부정확, 3=보통, 4=정확, 5=매우 정확",
                key=f"enhanced_classification_confidence_{self.image_id}"
            )

        # 2단계: 수정이 필요한 경우 계층적 선택
        corrected_main = current_main
        corrected_sub = current_sub
        user_custom_name = None

        if not is_correct:
            st.markdown("##### 🔧 분류 수정")

            # 주분류 선택
            main_categories = self.waste_service.get_main_categories()
            try:
                main_index = main_categories.index(current_main) if current_main in main_categories else 0
            except (ValueError, IndexError):
                main_index = 0

            corrected_main = st.selectbox(
                "올바른 주분류 선택",
                options=main_categories,
                index=main_index,
                key=f"enhanced_corrected_main_{self.image_id}"
            )

            # 세분류 선택
            if corrected_main:
                subcategories = self.waste_service.get_subcategories(corrected_main)
                sub_options = [sub.get('명칭', '') for sub in subcategories]

                try:
                    sub_index = sub_options.index(current_sub) if current_sub in sub_options else 0
                except (ValueError, IndexError):
                    sub_index = 0

                if sub_options:
                    corrected_sub = st.selectbox(
                        "올바른 세분류 선택",
                        options=sub_options,
                        index=sub_index,
                        key=f"enhanced_corrected_sub_{self.image_id}"
                    )

                    # 선택된 세분류의 예시 표시
                    selected_sub_data = next((sub for sub in subcategories if sub.get('명칭') == corrected_sub), {})
                    examples = selected_sub_data.get('예시', [])
                    if examples:
                        st.caption(f"💡 예시: {', '.join(examples[:3])}")

                    # "기타" 분류 선택 시 사용자 입력 필드 제공
                    if corrected_main == '기타' and corrected_sub == '분류불가':
                        st.markdown("##### 📝 물품 상세 입력")
                        user_custom_name = st.text_input(
                            "물품의 상세한 설명을 입력해주세요",
                            placeholder="예: 목재 선반, 스테인리스 식탁 등",
                            max_chars=100,
                            key=f"user_custom_name_{self.image_id}",
                            help="정확한 배출 방법 안내를 위해 물품의 구체적인 특징을 설명해주세요"
                        )

        # AI 추천 적용 버튼
        ai_suggestion = self.mapped_result.get('ai_suggestion', {})
        if ai_suggestion.get('has_ai_suggestion') and not ai_suggestion.get('recommendation_applied'):
            if st.button("🤖 AI 추천 분류 적용", key=f"apply_ai_suggestion_{self.image_id}"):
                corrected_main = ai_suggestion.get('ai_main_category', current_main)
                corrected_sub = ai_suggestion.get('ai_sub_category', current_sub)
                st.success(f"AI 추천 적용: {corrected_main} > {corrected_sub}")
                st.rerun()

        return {
            "is_correct": is_correct,
            "confidence_rating": confidence_rating,
            "original_main": current_main,
            "original_sub": current_sub,
            "corrected_main": corrected_main,
            "corrected_sub": corrected_sub,
            "user_custom_name": user_custom_name,
            "user_feedback": {
                "classification_accurate": is_correct,
                "confidence_level": confidence_rating,
                "corrected_main_category": corrected_main if not is_correct else None,
                "corrected_sub_category": corrected_sub if not is_correct else None,
                "user_custom_name": user_custom_name
            }
        }

    def _render_user_input_section(self) -> Dict[str, Any]:
        """분류 불가능한 물품에 대한 사용자 입력 섹션을 렌더링합니다."""
        st.markdown("##### 📝 물품 상세 입력")
        st.info("시스템이 분류하지 못한 물품입니다. 아래에서 선택하거나 직접 입력해주세요.")

        # 1단계: 대분류 선택 (기타 제외)
        main_categories = self.waste_service.get_main_categories()
        other_categories = [cat for cat in main_categories if cat != '기타']

        col1, col2 = st.columns(2)

        with col1:
            selected_main = st.selectbox(
                "물품의 주분류를 선택해주세요",
                options=['직접 입력'] + other_categories,
                key=f"user_input_main_{self.image_id}",
                help="물품이 속할 것으로 예상되는 대분류를 선택해주세요"
            )

        with col2:
            user_custom_name = st.text_input(
                "물품명 또는 상세 설명",
                placeholder="예: 목재 선반, 스테인리스 식탁, 헬스벤치 등",
                max_chars=100,
                key=f"user_input_custom_{self.image_id}",
                help="정확한 배출 방법 안내를 위해 구체적으로 설명해주세요"
            )

        # 선택된 분류에 따른 세분류 제시
        if selected_main != '직접 입력':
            subcategories = self.waste_service.get_subcategories(selected_main)
            sub_options = [sub.get('명칭', '') for sub in subcategories]

            selected_sub = st.selectbox(
                f"{selected_main} 내 세분류 선택 (선택사항)",
                options=['지정 안함'] + sub_options,
                key=f"user_input_sub_{self.image_id}",
                help="선택적입니다. 원하지 않으면 '지정 안함'을 선택하세요"
            )

            selected_sub = None if selected_sub == '지정 안함' else selected_sub
        else:
            selected_main = '기타'
            selected_sub = None

        return {
            "is_correct": True,
            "confidence_rating": 1,  # 사용자 입력 필요하므로 낮은 신뢰도
            "original_main": '기타',
            "original_sub": '분류불가',
            "corrected_main": selected_main,
            "corrected_sub": selected_sub or '분류불가',
            "user_custom_name": user_custom_name,
            "user_feedback": {
                "classification_accurate": True,
                "confidence_level": 1,
                "user_provided_input": True,
                "user_custom_name": user_custom_name,
                "corrected_main_category": selected_main,
                "corrected_sub_category": selected_sub
            }
        }

    def _render_size_section(self) -> Dict[str, Any]:
        """크기 확인 섹션을 렌더링합니다."""
        st.markdown("---")
        st.markdown("#### 📏 크기 정보 확인")

        dimensions = self.mapped_result.get('dimensions', {})

        if not dimensions or not any(dimensions.values()):
            st.info("크기 정보가 제공되지 않았습니다.")

            provide_size = st.checkbox(
                "직접 크기를 입력하시겠습니까?",
                key=f"enhanced_provide_size_{self.image_id}",
                help="크기 정보를 제공하시면 수수료 계산에 도움이 됩니다"
            )

            if provide_size:
                return self._render_manual_size_input()
            else:
                return {"status": "no_size", "is_correct": None}

        # 크기 정보가 있는 경우
        return self._render_size_validation(dimensions)

    def _render_manual_size_input(self) -> Dict[str, Any]:
        """수동 크기 입력을 렌더링합니다."""
        st.info("실제 크기를 입력해주세요. (단위: cm)")
        st.markdown("**크기 정의:**\n- 가로(W): 정면에서 본 좌우 길이\n- 높이(H): 정면에서 본 상하 길이\n- 깊이(D): 물체의 앞뒤 길이")

        col1, col2, col3 = st.columns(3)

        with col1:
            width = st.number_input("가로(W) cm", min_value=0.0, value=0.0, step=1.0, key=f"enhanced_manual_width_{self.image_id}", help="정면에서 본 좌우 길이")
        with col2:
            height = st.number_input("높이(H) cm", min_value=0.0, value=0.0, step=1.0, key=f"enhanced_manual_height_{self.image_id}", help="정면에서 본 상하 길이")
        with col3:
            depth = st.number_input("깊이(D) cm", min_value=0.0, value=0.0, step=1.0, key=f"enhanced_manual_depth_{self.image_id}", help="물체의 앞뒤 길이")

        if any([width > 0, height > 0, depth > 0]):
            return {
                "status": "user_provided",
                "is_correct": True,
                "dimensions": {
                    "w_cm": width if width > 0 else None,
                    "h_cm": height if height > 0 else None,
                    "d_cm": depth if depth > 0 else None
                },
                "user_feedback": {
                    "size_available": True,
                    "user_provided_size": True,
                    "confidence_level": 4
                }
            }

        return {"status": "no_size", "is_correct": None}

    def _render_size_validation(self, dimensions: Dict[str, Any]) -> Dict[str, Any]:
        """크기 검증을 렌더링합니다."""
        # 현재 크기 표시
        col1, col2, col3 = st.columns(3)

        with col1:
            w_val = dimensions.get('w_cm') or dimensions.get('width_cm', 0)
            st.metric("가로(W)", f"{w_val:.0f} cm", help="정면에서 본 좌우 길이")
        with col2:
            h_val = dimensions.get('h_cm') or dimensions.get('height_cm', 0)
            st.metric("높이(H)", f"{h_val:.0f} cm", help="정면에서 본 상하 길이")
        with col3:
            d_val = dimensions.get('d_cm') or dimensions.get('depth_cm', 0)
            st.metric("깊이(D)", f"{d_val:.0f} cm", help="물체의 앞뒤 길이")

        # 정확성 확인
        col1, col2 = st.columns(2)

        with col1:
            is_correct = st.radio(
                "크기 추정이 정확한가요?",
                options=["정확합니다", "부정확합니다"],
                key=f"enhanced_size_check_{self.image_id}"
            ) == "정확합니다"

        with col2:
            confidence_rating = st.slider(
                "크기 신뢰도",
                min_value=1,
                max_value=5,
                value=4 if is_correct else 2,
                key=f"enhanced_size_confidence_{self.image_id}"
            )

        result = {
            "status": "validated",
            "is_correct": is_correct,
            "confidence_rating": confidence_rating,
            "original_dimensions": dimensions,
            "user_feedback": {
                "size_available": True,
                "size_accurate": is_correct,
                "confidence_level": confidence_rating
            }
        }

        # 수정이 필요한 경우
        if not is_correct:
            st.markdown("##### 🔧 크기 수정")
            result.update(self._render_manual_size_input())
            result["user_feedback"]["corrected_dimensions"] = result.get("dimensions")

        return result

    def _render_notes_section(self) -> str:
        """추가 메모 섹션을 렌더링합니다."""
        st.markdown("---")
        st.markdown("#### 💬 추가 정보")

        return st.text_area(
            "추가로 알려주실 내용이 있다면 적어주세요 (선택사항)",
            key=f"enhanced_confirmation_notes_{self.image_id}",
            placeholder="예: 분리가 가능한 제품입니다, 특별한 재질로 만들어졌습니다 등",
            help="이 정보는 더 정확한 수수료 계산과 배출 방법 안내에 도움이 됩니다"
        ).strip()

    def _process_quick_confirmation(self) -> Dict[str, Any]:
        """빠른 확인을 처리합니다."""
        try:
            # 빠른 확인용 피드백 데이터 구성
            quick_feedback = {
                "classification": {
                    "classification_accurate": True,
                    "confidence_level": 5,
                    "corrected_main_category": None,
                    "corrected_sub_category": None,
                    "enhanced_ui_used": True,
                    "quick_confirm": True
                },
                "size": {
                    "size_available": bool(self.mapped_result.get('dimensions')),
                    "size_accurate": True if self.mapped_result.get('dimensions') else None,
                    "confidence_level": 4 if self.mapped_result.get('dimensions') else None
                },
                "overall": {
                    "user_confirmed": True,
                    "feedback_timestamp": datetime.now().isoformat()
                }
            }

            # 저장 처리
            save_result = self.confirmation_service.save_confirmation(
                session_id=self.session_id,
                image_id=self.image_id,
                original_analysis=self.mapped_result,
                is_correct=True,
                corrected_data={"feedback_details": quick_feedback}
            )

            if save_result and save_result.get('success'):
                st.success("✅ 개선된 분류 시스템으로 확인 완료!")
                st.info("🎯 AI 기반 지능형 분류가 적용되었습니다.")
                st.balloons()

                confirmation_result = {
                    "confirmation_id": save_result.get('confirmation_id'),
                    "session_id": self.session_id,
                    "image_id": self.image_id,
                    "timestamp": datetime.now().isoformat(),
                    "original_analysis": self.mapped_result,
                    "user_confirmed": True,
                    "enhanced_ui": True,
                    "quick_confirm": True,
                    "comprehensive_feedback": quick_feedback
                }

                st.session_state.confirmed_analysis = confirmation_result

                if st.button("🚛 배출 방법 안내 보기", type="primary", use_container_width=True, key=f"enhanced_disposal_guide_{self.image_id}"):
                    st.session_state.show_disposal_guide = True
                    st.rerun()

                return confirmation_result
            else:
                st.error("저장 중 오류가 발생했습니다.")
                return None

        except Exception as e:
            logger.error(f"Error during enhanced quick confirmation: {e}")
            st.error("빠른 확인 중 오류가 발생했습니다.")
            return None

    def _handle_submission(self, classification_result: Dict[str, Any],
                          size_result: Dict[str, Any], notes: str) -> Dict[str, Any]:
        """확인 결과를 처리하고 저장합니다."""
        try:
            # 확인 상태 판정
            classification_confirmed = classification_result.get("is_correct", False)
            size_confirmed = size_result.get("is_correct")

            user_confirmed = (
                classification_confirmed and
                (size_confirmed is True or size_confirmed is None)
            )

            # 종합 피드백 구성
            comprehensive_feedback = {
                "classification": classification_result.get("user_feedback", {}),
                "size": size_result.get("user_feedback", {}),
                "overall": {
                    "user_confirmed": user_confirmed,
                    "additional_notes": notes or None,
                    "enhanced_ui_used": True,
                    "feedback_timestamp": datetime.now().isoformat()
                }
            }

            # 확인 결과 구성
            confirmation_result = {
                "confirmation_id": str(uuid.uuid4()),
                "session_id": self.session_id,
                "image_id": self.image_id,
                "timestamp": datetime.now().isoformat(),
                "original_analysis": self.mapped_result,
                "user_confirmed": user_confirmed,
                "enhanced_ui": True,
                "classification_result": classification_result,
                "size_result": size_result,
                "notes": notes or None,
                "comprehensive_feedback": comprehensive_feedback
            }

            # 저장 처리
            save_result = self.confirmation_service.save_confirmation(
                session_id=self.session_id,
                image_id=self.image_id,
                original_analysis=self.mapped_result,
                is_correct=user_confirmed,
                corrected_data={
                    "classification": {
                        "main_category": classification_result.get("corrected_main"),
                        "sub_category": classification_result.get("corrected_sub")
                    },
                    "size": size_result.get("dimensions"),
                    "notes": notes,
                    "feedback_details": comprehensive_feedback
                }
            )

            if save_result and save_result.get('success'):
                if user_confirmed:
                    st.success("✅ 개선된 분류 시스템으로 확인 완료!")
                    st.info("🎯 새로운 계층 구조 기반 분류가 적용되었습니다.")
                    st.balloons()
                else:
                    st.warning("⚠️ 수정 사항이 저장되었습니다.")
                    st.info("개선된 분류 시스템을 통해 더 정확한 데이터가 수집됩니다.")

                # 세션 상태에 저장
                st.session_state.confirmed_analysis = confirmation_result

                # 배출 안내로 이동
                if st.button("🚛 배출 방법 안내 보기", type="primary", use_container_width=True, key=f"enhanced_final_guide_{self.image_id}"):
                    st.session_state.show_disposal_guide = True
                    st.rerun()

                return confirmation_result
            else:
                st.error("저장 중 오류가 발생했습니다.")
                return None

        except Exception as e:
            logger.error(f"Error handling enhanced submission: {e}")
            st.error("확인 처리 중 오류가 발생했습니다.")
            return None