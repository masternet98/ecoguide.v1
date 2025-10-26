"""
EcoGuide.v1 - 새로운 아키텍처 기반 메인 애플리케이션

이미지 분석 이후 프로세스를 깔끔하게 재구현한 버전입니다.
- 위치 기능: 동작 ✓
- 폐기물 분류 관리: 동작 ✓
- 이미지 업로드 및 전처리: 동작 ✓
- 이미지 분석 이후 프로세스: 새로 구현 ✓

흐름:
1. 이미지 업로드/캡처 → 전처리
2. OpenAI Vision API로 분석
3. JSON 파싱 및 정규화
4. 폐기물 분류 매핑
5. 사용자 확인 및 수정
6. 최종 제출
"""

import streamlit as st
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from src.app.core.app_factory import get_application
from src.app.core.session_state import SessionStateManager
from src.app.core.error_handler import handle_errors, create_streamlit_error_ui, get_error_handler

logger = logging.getLogger(__name__)


class AnalysisState:
    """이미지 분석 상태를 관리하는 클래스"""

    def __init__(self):
        """세션 상태를 초기화합니다"""
        if 'analysis_step' not in st.session_state:
            st.session_state.analysis_step = 'image_input'  # image_input, analysis, confirmation, complete

        if 'current_image' not in st.session_state:
            st.session_state.current_image = None

        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = None

        if 'normalized_result' not in st.session_state:
            st.session_state.normalized_result = None

        if 'label_saved' not in st.session_state:
            st.session_state.label_saved = False  # 라벨 저장 완료 여부

    def set_step(self, step: str) -> None:
        """분석 단계를 설정합니다"""
        st.session_state.analysis_step = step

    def get_step(self) -> str:
        """현재 분석 단계를 반환합니다"""
        return st.session_state.analysis_step

    def set_image(self, image_bytes: bytes) -> None:
        """현재 이미지를 설정합니다"""
        st.session_state.current_image = image_bytes

    def get_image(self) -> Optional[bytes]:
        """현재 이미지를 반환합니다"""
        return st.session_state.current_image

    def set_analysis_result(self, result: str, raw: Dict) -> None:
        """분석 결과를 설정합니다"""
        st.session_state.analysis_result = {'text': result, 'raw': raw}

    def get_analysis_result(self) -> Optional[Dict]:
        """분석 결과를 반환합니다"""
        return st.session_state.analysis_result

    def set_normalized_result(self, result: Dict[str, Any]) -> None:
        """정규화된 결과를 설정합니다"""
        st.session_state.normalized_result = result

    def get_normalized_result(self) -> Optional[Dict[str, Any]]:
        """정규화된 결과를 반환합니다"""
        return st.session_state.normalized_result

    def reset(self) -> None:
        """모든 상태를 초기화합니다"""
        st.session_state.analysis_step = 'image_input'
        st.session_state.current_image = None
        st.session_state.analysis_result = None
        st.session_state.normalized_result = None
        st.session_state.label_saved = False  # 라벨 저장 상태 초기화


class ImageUploadStep:
    """Step 1: 이미지 업로드/캡처"""

    def __init__(self, app_context):
        self.app_context = app_context

    def render(self, state: AnalysisState) -> Optional[bytes]:
        """이미지 업로드 UI를 렌더링합니다"""
        # 이미지 입력 방식 선택 (탭)
        tab1, tab2 = st.tabs(["📷 카메라", "🖼️ 파일 업로드"])

        with tab1:
            st.markdown("**카메라로 사진 촬영**")
            camera_image = st.camera_input("사진을 촬영하세요")
            if camera_image:
                return camera_image.getvalue()

        with tab2:
            st.markdown("**파일에서 이미지 선택**")
            uploaded_file = st.file_uploader("이미지를 선택하세요", type=['jpg', 'jpeg', 'png'])
            if uploaded_file:
                return uploaded_file.getvalue()

        return None


class AnalysisStep:
    """Step 2: OpenAI Vision API로 이미지 분석"""

    def __init__(self, app_context):
        self.app_context = app_context

    def render(self, state: AnalysisState, model: str, prompt: str) -> bool:
        """이미지 분석을 실행합니다"""
        image_bytes = state.get_image()

        if not image_bytes:
            st.error("이미지가 없습니다")
            return False

        st.subheader("🧠 이미지 분석")

        # 이미지 표시
        st.image(image_bytes, caption="분석할 이미지", use_container_width=True)

        # 분석 옵션
        col1, col2 = st.columns(2)

        with col1:
            max_size = st.slider(
                "최대 변환 크기 (px)",
                min_value=480,
                max_value=1280,
                value=1024,
                step=64,
                key="max_size"
            )

        with col2:
            st.metric("프롬프트 길이", f"{len(prompt)} 자")

        # 최종 프롬프트 확인 (expander)
        with st.expander("🔍 AI에 전달되는 최종 프롬프트 확인", expanded=False):
            st.markdown("**AI에 다음의 프롬프트와 함께 이미지가 전달됩니다:**")
            st.markdown("---")
            st.code(prompt, language="markdown")
            st.markdown("---")
            st.info("💡 프롬프트가 정상적으로 작성되지 않았다면 AI의 분류 결과가 부정확할 수 있습니다.")

        # 분석 버튼
        if not st.button("🔍 분석 시작", use_container_width=True, key="start_analysis"):
            return False

        # OpenAI 서비스 확인
        openai_service = self.app_context.get_service('openai_service')
        if not openai_service or not openai_service.is_ready():
            st.error("OpenAI 서비스를 사용할 수 없습니다")
            return False

        if not openai_service.has_api_key():
            st.error("OpenAI API Key가 필요합니다")
            return False

        # 이미지 전처리
        try:
            from src.domains.analysis.services.openai_service import jpeg_bytes_from_image

            with st.spinner("🖼️ 이미지 전처리 중..."):
                jpeg_bytes = jpeg_bytes_from_image(image_bytes, int(max_size), 85)

            # LLM 분석
            with st.spinner("🤖 AI가 이미지를 분석 하고 있습니다. 잠시만 기다려주세요."):
                output_text, raw = openai_service.analyze_image(jpeg_bytes, prompt.strip(), model)

                if not output_text or not raw:
                    st.error("분석 결과를 받을 수 없습니다")
                    return False

                # 결과 저장
                state.set_analysis_result(output_text, raw)
                st.success("✅ 분석 완료!")
                return True

        except Exception as e:
            error_info = get_error_handler().handle_error(e)
            create_streamlit_error_ui(error_info)
            return False


class ConfirmationStep:
    """Step 3: 분석 결과 확인 및 분류 선택"""

    def __init__(self, app_context):
        self.app_context = app_context

    def _parse_analysis_result(self, output_text: str) -> Dict[str, Any]:
        """LLM 분석 결과를 파싱합니다"""
        import json

        try:
            # JSON 마크다운 코드 블록에서 추출
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output_text)
            if json_match:
                output_text = json_match.group(1).strip()

            parsed = json.loads(output_text)
            return parsed
        except json.JSONDecodeError:
            st.warning("JSON 파싱 실패. 텍스트 기반 분석으로 진행합니다.")
            return {
                'object_name': '알 수 없음',
                'primary_category': '기타',
                'secondary_category': '분류불가',
                'confidence': 0.3,
                'reasoning': '자동 파싱 실패'
            }

    def _normalize_result(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """분석 결과를 정규화합니다"""
        waste_service = self.app_context.get_service('waste_classification_service')
        ai_mapper = self.app_context.get_service('ai_classification_mapper')

        # 기본 필드 추출
        object_name = parsed.get('object_name', '알 수 없음')
        primary_category = parsed.get('primary_category') or parsed.get('main_category', '기타')
        secondary_category = parsed.get('secondary_category') or parsed.get('sub_category', '분류불가')
        confidence = float(parsed.get('confidence', 0.5))
        dimensions = parsed.get('dimensions', {}) or parsed.get('size_estimation', {})

        normalized = {
            'object_name': object_name,
            'primary_category': primary_category,
            'secondary_category': secondary_category,
            'confidence': confidence,
            'dimensions': dimensions,
            'reasoning': parsed.get('reasoning', ''),
            'raw_response': parsed
        }

        return normalized

    def render(self, state: AnalysisState) -> Optional[Dict[str, Any]]:
        """분석 결과를 확인하고 분류를 선택합니다"""
        analysis_result = state.get_analysis_result()

        if not analysis_result:
            st.error("분석 결과가 없습니다")
            return None

        # 분석된 이미지 표시
        image_bytes = state.get_image()
        if image_bytes:
            st.image(image_bytes, caption="분석된 이미지", use_container_width=True)
            st.markdown("---")

        # 분석 결과 파싱
        parsed = self._parse_analysis_result(analysis_result['text'])
        normalized = self._normalize_result(parsed)

        # 분석 결과 표시 (콤보박스 형태)
        st.subheader("📊 분석 결과")

        # 물품명 표시
        st.write(f"**감지된 물품:** {normalized['object_name']}")

        # 폐기물 분류 서비스 가져오기
        waste_service = self.app_context.get_service('waste_classification_service')

        # 폐기물 분류 서비스 확인
        if not waste_service:
            st.warning("⚠️ 폐기물 분류 서비스를 로드할 수 없습니다. 관리 페이지에서 분류를 설정하세요.")

        col1, col2 = st.columns(2)

        # 대분류 선택
        with col1:
            main_categories = waste_service.get_main_categories() if waste_service else []
            if not main_categories:
                st.error("❌ 사용 가능한 대분류가 없습니다.")
            else:
                selected_main = st.selectbox(
                    "대분류",
                    options=main_categories,
                    index=main_categories.index(normalized['primary_category']) if normalized['primary_category'] in main_categories else 0,
                    key="result_main_category",
                    help="폐기물의 주 카테고리를 선택하세요"
                )
                normalized['primary_category'] = selected_main

        # 세분류 선택
        with col2:
            if waste_service and waste_service.get_main_categories():
                # 현재 선택된 대분류의 세분류 가져오기
                current_main = normalized.get('primary_category')
                if current_main:
                    subcategories = waste_service.get_subcategories(current_main)
                    if subcategories:
                        sub_options = [sub.get('명칭', '') for sub in subcategories]

                        # 현재 선택된 세분류의 인덱스 계산
                        try:
                            default_index = sub_options.index(normalized['secondary_category'])
                        except (ValueError, IndexError):
                            default_index = 0

                        selected_sub = st.selectbox(
                            "세분류",
                            options=sub_options,
                            index=default_index,
                            key=f"result_sub_category_{current_main}",  # 대분류별 고유 키
                            help="폐기물의 세부 카테고리를 선택하세요"
                        )
                        normalized['secondary_category'] = selected_sub
                    else:
                        st.warning(f"⚠️ '{current_main}'에 해당하는 세분류가 없습니다.")
                        normalized['secondary_category'] = "분류불가"
                else:
                    st.info("💡 먼저 대분류를 선택하세요.")
            else:
                st.write(f"**세분류:** {normalized.get('secondary_category', '분류불가')}")

        # 신뢰도 표시
        st.metric("신뢰도", f"{normalized['confidence']:.0%}")

        # 신뢰도 조정
        st.markdown("---")
        confidence_rating = st.slider(
            "신뢰도 조정",
            min_value=1,
            max_value=5,
            value=int(normalized['confidence'] * 5) if normalized['confidence'] > 0 else 3,
            key="confidence_rating"
        )
        normalized['confidence'] = confidence_rating / 5

        # 크기 정보 섹션
        st.markdown("---")
        st.subheader("📏 크기 정보 (3D 차원)")

        dimensions = normalized.get('dimensions', {})

        if dimensions and any(dimensions.values()):
            # 크기 정보가 있는 경우 표시
            col1, col2, col3 = st.columns(3)

            with col1:
                w_val = dimensions.get('w_cm') or dimensions.get('width_cm', '-')
                st.metric("가로(W)", f"{w_val} cm", help="정면에서 본 좌우 길이")

            with col2:
                h_val = dimensions.get('h_cm') or dimensions.get('height_cm', '-')
                st.metric("높이(H)", f"{h_val} cm", help="정면에서 본 상하 길이")

            with col3:
                d_val = dimensions.get('d_cm') or dimensions.get('depth_cm', '-')
                st.metric("깊이(D)", f"{d_val} cm", help="물체의 앞뒤 길이(깊이)")

            # 크기 수정 옵션
            modify_size = st.checkbox("크기를 수정하시겠습니까?", key="modify_size_info")

            if modify_size:
                st.markdown("**슬라이더로 크기를 조정하세요 (단위: cm):**")

                width = st.slider(
                    "가로(W) - 정면에서 본 좌우 길이",
                    min_value=0,
                    max_value=300,
                    value=int(dimensions.get('w_cm') or dimensions.get('width_cm') or 0),
                    step=5,
                    key="mod_width"
                )

                height = st.slider(
                    "높이(H) - 정면에서 본 상하 길이",
                    min_value=0,
                    max_value=300,
                    value=int(dimensions.get('h_cm') or dimensions.get('height_cm') or 0),
                    step=5,
                    key="mod_height"
                )

                depth = st.slider(
                    "깊이(D) - 물체의 앞뒤 길이",
                    min_value=0,
                    max_value=300,
                    value=int(dimensions.get('d_cm') or dimensions.get('depth_cm') or 0),
                    step=5,
                    key="mod_depth"
                )

                normalized['dimensions'] = {
                    'w_cm': width if width > 0 else None,
                    'h_cm': height if height > 0 else None,
                    'd_cm': depth if depth > 0 else None
                }
        else:
            # 크기 정보가 없는 경우
            st.info("💡 크기 정보가 제공되지 않았습니다. 직접 입력하실 수 있습니다.")

            provide_size = st.checkbox(
                "직접 크기를 입력하시겠습니까?",
                key="provide_size_manual"
            )

            if provide_size:
                st.markdown("**슬라이더로 실제 크기를 입력해주세요 (단위: cm):**")

                width = st.slider(
                    "가로(W) - 정면에서 본 좌우 길이",
                    min_value=0,
                    max_value=300,
                    value=0,
                    step=5,
                    key="manual_width"
                )

                height = st.slider(
                    "높이(H) - 정면에서 본 상하 길이",
                    min_value=0,
                    max_value=300,
                    value=0,
                    step=5,
                    key="manual_height"
                )

                depth = st.slider(
                    "깊이(D) - 물체의 앞뒤 길이",
                    min_value=0,
                    max_value=300,
                    value=0,
                    step=5,
                    key="manual_depth"
                )

                if any([width > 0, height > 0, depth > 0]):
                    normalized['dimensions'] = {
                        'w_cm': width if width > 0 else None,
                        'h_cm': height if height > 0 else None,
                        'd_cm': depth if depth > 0 else None
                    }

        # 기타 분류인 경우 사용자 입력
        if normalized['primary_category'] == '기타' and normalized['secondary_category'] == '분류불가':
            st.markdown("---")
            user_input = st.text_input(
                "물품 상세 설명",
                placeholder="예: 목재 선반, 스테인리스 식탁",
                max_chars=100,
                key="user_custom_name"
            )
            normalized['user_custom_name'] = user_input

        # 사용자 피드백 섹션
        st.markdown("---")
        st.subheader("💬 추가 정보")

        feedback_notes = st.text_area(
            "분류 또는 크기에 대해 추가로 알려주실 내용이 있으신가요? (선택사항)",
            placeholder="예: 분리가 가능한 제품입니다, 특별한 재질로 만들어졌습니다 등",
            height=100,
            key="feedback_notes"
        )

        normalized['user_feedback'] = {
            'notes': feedback_notes.strip(),
            'timestamp': datetime.now().isoformat()
        }

        # AI 피드백 섹션 (선택적)
        st.markdown("---")
        st.subheader("🤖 AI 피드백 (선택)")

        if st.button("💭 AI 의견 듣기", use_container_width=True, key="get_ai_feedback"):
            try:
                # 프롬프트 서비스 가져오기
                prompt_service = self.app_context.get_service('prompt_service')
                openai_service = self.app_context.get_service('openai_service')

                if prompt_service and openai_service:
                    # Simple Prompt 패턴:
                    # 1. 저장된 프롬프트 로드 (또는 기본값으로 생성)
                    confirmation_prompt = prompt_service.get_default_prompt_for_feature('confirmation_analysis')

                    if confirmation_prompt:
                        # 2. 변수 준비
                        dimensions = normalized.get('dimensions', {})
                        dimensions_str = f"{dimensions.get('w_cm', '-')}cm x {dimensions.get('h_cm', '-')}cm x {dimensions.get('d_cm', '-')}cm"

                        variables = {
                            'item_name': normalized['object_name'],
                            'category': normalized['primary_category'],
                            'dimensions': dimensions_str,
                            'confidence': f"{normalized['confidence']:.0%}",
                            'user_feedback': feedback_notes.strip() or '없음'
                        }

                        # 3. 프롬프트 렌더링 (변수 치환)
                        rendered_prompt = prompt_service.render_prompt(
                            confirmation_prompt.id,
                            variables
                        )

                        if rendered_prompt:
                            # 4. LLM 호출
                            with st.spinner("🤖 AI가 피드백을 생성 중입니다..."):
                                feedback_result = openai_service.call_with_prompt(rendered_prompt)

                            if feedback_result:
                                st.success("✅ AI 피드백")
                                st.markdown(feedback_result)
                            else:
                                st.warning("AI 피드백 생성에 실패했습니다")
                        else:
                            st.warning("프롬프트 렌더링에 실패했습니다")
                    else:
                        st.info("💡 저장된 피드백 프롬프트가 없습니다. Admin에서 'confirmation_analysis' 기능용 프롬프트를 생성해주세요.")
                else:
                    st.error("필요한 서비스를 사용할 수 없습니다")

            except Exception as e:
                error_info = get_error_handler().handle_error(e)
                st.warning(f"AI 피드백 생성 중 오류: {str(e)}")
                logger.error(f"AI feedback generation error: {e}", exc_info=True)

        # 최종 확인 버튼
        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ 확인", use_container_width=True, key="confirm_btn"):
                state.set_normalized_result(normalized)
                state.set_step('complete')
                return normalized

        with col2:
            if st.button("🔙 다시 분석", use_container_width=True, key="retry_btn"):
                state.reset()
                st.rerun()

        return None


class CompleteStep:
    """Step 4: 분류 완료 및 배출 안내"""

    def __init__(self, app_context):
        self.app_context = app_context

    def render(self, state: AnalysisState) -> None:
        """분류 완료 화면을 렌더링합니다"""
        normalized = state.get_normalized_result()

        if not normalized:
            st.error("결과가 없습니다")
            return

        # 분석된 이미지 표시
        image_bytes = state.get_image()
        if image_bytes:
            st.image(image_bytes, caption="분석된 이미지", use_container_width=True)
            st.markdown("---")

        # 최종 결과 표시
        result_container = st.container(border=True)

        with result_container:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("물품명", normalized['object_name'])

            with col2:
                st.metric("대분류", normalized['primary_category'])

            with col3:
                st.metric("세분류", normalized['secondary_category'])

        # 피드백 저장 및 라벨링 데이터 저장 (단 한 번만)
        if not st.session_state.get('label_saved', False):
            try:
                confirmation_service = self.app_context.get_service('confirmation_service')

                if confirmation_service:
                    # 피드백 데이터 구성
                    feedback_data = {
                        "classification": {
                            "object_name": normalized.get('object_name'),
                            "primary_category": normalized.get('primary_category'),
                            "secondary_category": normalized.get('secondary_category'),
                            "confidence": normalized.get('confidence')
                        },
                        "dimensions": normalized.get('dimensions', {}),
                        "user_feedback": normalized.get('user_feedback', {}),
                        "timestamp": datetime.now().isoformat()
                    }

                    # 피드백 저장
                    save_result = confirmation_service.save_confirmation(
                        session_id=st.session_state.get('session_id', 'unknown'),
                        image_id=st.session_state.get('image_id', 'unknown'),
                        original_analysis=normalized,
                        is_correct=True,
                        corrected_data={'feedback_details': feedback_data}
                    )

                    if save_result and save_result.get('success'):
                        st.success("✅ 분류가 완료되었습니다!")
                        st.info("💾 피드백이 저장되었습니다")

                        # 라벨링 서비스를 통해 학습 데이터로 저장
                        try:
                            labeling_service = self.app_context.get_service('labeling_service')
                            if labeling_service:
                                if image_bytes:
                                    label_result = labeling_service.save_label(
                                        image_bytes=image_bytes,
                                        analysis_result=normalized,
                                        user_feedback=normalized.get('user_feedback', {})
                                    )

                                    if label_result.get('success'):
                                        st.success(f"📊 학습 데이터로 저장되었습니다. (ID: {label_result.get('file_id')})")
                                        logger.info(f"Label saved successfully: {label_result.get('file_id')}")

                                        # 라벨 저장 완료 표시
                                        st.session_state.label_saved = True
                                    else:
                                        st.warning(f"학습 데이터 저장 중 오류: {label_result.get('error')}")
                                        logger.warning(f"Label save failed: {label_result.get('error')}")
                                else:
                                    logger.warning("이미지 바이트 데이터가 없습니다")
                            else:
                                logger.warning("LabelingService를 초기화할 수 없습니다")
                        except Exception as e:
                            logger.error(f"라벨링 데이터 저장 중 예외 발생: {e}", exc_info=True)
                            st.warning(f"라벨링 데이터 저장 중 오류: {str(e)}")

            except Exception as e:
                st.warning(f"피드백 저장 중 오류가 발생했습니다: {e}")

        # 배출 방법 안내 (선택사항)
        st.markdown("---")
        st.subheader("📖 배출 방법 안내")

        if st.button("💡 배출 방법 확인", use_container_width=True, key="show_disposal"):
            try:
                # 프롬프트 서비스 가져오기
                prompt_service = self.app_context.get_service('prompt_service')
                openai_service = self.app_context.get_service('openai_service')
                location_service = self.app_context.get_service('location_service')

                if prompt_service and openai_service:
                    # Simple Prompt 패턴:
                    # 1. 저장된 프롬프트 로드
                    disposal_prompt = prompt_service.get_default_prompt_for_feature('disposal_guidance_main')

                    if disposal_prompt:
                        # 2. 변수 준비
                        dimensions = normalized.get('dimensions', {})
                        dimensions_str = f"{dimensions.get('w_cm', '-')}cm x {dimensions.get('h_cm', '-')}cm x {dimensions.get('d_cm', '-')}cm"

                        # 위치 정보 (현재 선택된 위치가 있으면 사용)
                        location_info = st.session_state.get('selected_location', {}) or {}
                        location_full = location_info.get('full_address', '미지정')
                        location_code = location_info.get('code', '')

                        # RAG를 통해 지역별 배출 정보 수집 (선택적)
                        location_context = '일반 배출 규정'
                        if location_service and location_code:
                            try:
                                rag_service = self.app_context.get_service('rag_context_service')
                                if rag_service:
                                    rag_result = rag_service.search_disposal_guidance(
                                        location_code=location_code,
                                        waste_category=normalized['primary_category']
                                    )
                                    if rag_result and rag_result.get('success'):
                                        location_context = rag_result.get('location_context', location_context)
                            except Exception as e:
                                logger.warning(f"RAG 검색 실패: {e}")
                                # RAG 실패해도 계속 진행

                        variables = {
                            'location_full': location_full,
                            'item_name': normalized['object_name'],
                            'category': normalized['primary_category'],
                            'dimensions': dimensions_str,
                            'location_context': location_context,
                            'waste_context': f"세분류: {normalized['secondary_category']}"
                        }

                        # 3. 프롬프트 렌더링 (변수 치환)
                        rendered_prompt = prompt_service.render_prompt(
                            disposal_prompt.id,
                            variables
                        )

                        if rendered_prompt:
                            # 4. LLM 호출
                            with st.spinner("🤖 배출 방법을 찾고 있습니다..."):
                                disposal_result = openai_service.call_with_prompt(rendered_prompt)

                            if disposal_result:
                                st.success("✅ 배출 방법 안내")
                                st.markdown(disposal_result)
                            else:
                                st.warning("배출 방법 안내 생성에 실패했습니다")
                        else:
                            st.warning("프롬프트 렌더링에 실패했습니다")
                    else:
                        st.info("💡 저장된 배출 안내 프롬프트가 없습니다. Admin에서 'disposal_guidance_main' 기능용 프롬프트를 생성해주세요.\n\n"
                               f"기본 배출 방법:\n"
                               f"1. 해당 지역의 폐기물 관리 부서 확인\n"
                               f"2. **{normalized['object_name']}** ({normalized['primary_category']})의 배출 가능 여부 확인\n"
                               f"3. 배출 신청 및 수거 예약")
                else:
                    st.error("필요한 서비스를 사용할 수 없습니다")

            except Exception as e:
                logger.error(f"Disposal guidance generation error: {e}", exc_info=True)
                st.warning(f"배출 방법 안내 생성 중 오류: {str(e)}")

        # 초기화 버튼
        st.markdown("---")

        if st.button("🔄 새로운 사진 분석", use_container_width=True, key="new_analysis"):
            state.reset()
            st.rerun()


@handle_errors(show_user_message=True, reraise=False)
def main():
    """메인 애플리케이션"""
    # 페이지 설정
    st.set_page_config(
        page_title="EcoGuide.v1 - 대형폐기물 분류",
        page_icon="📷",
        layout="centered"
    )

    # 애플리케이션 컨텍스트 초기화
    try:
        app_context = get_application()
    except Exception as e:
        st.error("애플리케이션 초기화에 실패했습니다.")
        create_streamlit_error_ui(get_error_handler().handle_error(e))
        st.stop()

    # 세션 상태 초기화
    SessionStateManager.init_image_state()
    SessionStateManager.init_ui_state()
    SessionStateManager.init_location_state()

    state = AnalysisState()

    # 폐기물 분류 관리 페이지 확인
    if st.session_state.get('show_waste_management', False):
        from src.domains.analysis.ui.waste_types_management import WasteTypesManagementComponent
        waste_mgmt = WasteTypesManagementComponent(app_context)

        # 뒤로 가기 버튼
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🔙 닫기", use_container_width=True, key="close_waste_mgmt"):
                st.session_state.show_waste_management = False
                st.rerun()

        st.markdown("---")
        waste_mgmt.render()
        return  # st.stop() 대신 return 사용

    # 사이드바 설정
    with st.sidebar:
        st.title("⚙️ 설정")
        st.markdown("---")

        # 모델 선택
        model = st.selectbox(
            "분석 모델",
            options=["gpt-4o-mini", "gpt-4-vision"],
            index=0,
            key="model_select"
        )

        st.markdown("---")

        # 진행 상태 표시
        st.subheader("진행 상태")
        step_names = {
            'image_input': "1️⃣ 이미지 업로드",
            'analysis': "2️⃣ 분석 중",
            'confirmation': "3️⃣ 결과 확인",
            'complete': "4️⃣ 완료"
        }
        current_step = state.get_step()
        for step_id, step_name in step_names.items():
            if step_id == current_step:
                st.write(f"**{step_name} ← 현재**")
            else:
                st.write(step_name)

        st.markdown("---")

        # 관리 페이지 링크
        st.subheader("🛠️ 관리")

        if st.button("🗂️ 폐기물 분류 관리", use_container_width=True, key="waste_mgmt_button"):
            st.session_state.show_waste_management = True
            st.rerun()  # 즉시 rerun으로 위의 관리 페이지 표시

        st.markdown("---")

    # 메인 콘텐츠
    st.title("✨ EcoGuide.AI")
    st.caption("버리려는 그 순간, 찰칵! AI가 최적의 방법을 알려드립니다!")
    st.markdown("---")

    # 지역 선택 (메인 화면에 표시)
    st.subheader("📍 지역 선택")
    from src.domains.district.ui.location_selector import LocationSelectorComponent
    location_selector = LocationSelectorComponent(app_context)
    location = location_selector.render()

    if location and location.get('success'):
        location_data = location.get('data', {})
        st.success(f"📍 선택된 위치: {location_data.get('sido', '')} {location_data.get('sigungu', '')}")

    st.markdown("---")

    # Step 1: 이미지 업로드
    if state.get_step() == 'image_input':
        st.header("📷 이미지 업로드")
        st.markdown("---")

        upload_step = ImageUploadStep(app_context)
        image_bytes = upload_step.render(state)

        if image_bytes:
            state.set_image(image_bytes)
            state.set_step('analysis')
            st.rerun()

    # Step 2: 분석
    elif state.get_step() == 'analysis':

        # 프롬프트 설정
        st.subheader("📝 분석 프롬프트")

        # waste_types.json에서 분류 체계 텍스트 생성
        def build_waste_classification_text() -> str:
            """waste_types.json을 기반으로 분류 체계 텍스트를 생성합니다."""
            import json
            import os

            try:
                # waste_types.json 찾기
                possible_paths = [
                    "uploads/waste_types/waste_types.json",
                    "/home/jaeho/projects_linux/ecoguide.v1/uploads/waste_types/waste_types.json",
                    os.path.join(os.getcwd(), "uploads", "waste_types", "waste_types.json")
                ]

                waste_data = None
                for path in possible_paths:
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            waste_data = json.load(f)
                        break

                if not waste_data:
                    raise FileNotFoundError("waste_types.json을 찾을 수 없습니다.")

                # 분류 체계 텍스트 생성
                classification_text = "## 폐기물 분류 체계\n\n"

                for main_cat, details in waste_data.items():
                    description = details.get('설명', '')
                    classification_text += f"### {main_cat} - {description}\n"

                    subcategories = details.get('세분류', [])
                    for sub in subcategories:
                        name = sub.get('명칭', '')
                        examples = sub.get('예시', [])
                        if examples:
                            example_str = ', '.join(examples)
                            classification_text += f"- **{name}** ({example_str})\n"
                        else:
                            classification_text += f"- **{name}**\n"

                    classification_text += "\n"

                return classification_text

            except Exception as e:
                logger.warning(f"Failed to load waste_types.json: {e}")
                return ""

        # registry.json에서 분석 인터페이스 프롬프트 로드
        def load_analysis_prompt_from_registry() -> str:
            """prompt_feature_registry.json에서 analysis_interface 프롬프트를 로드합니다."""
            import json
            import os

            try:
                # registry.json 찾기
                possible_paths = [
                    "data/prompts/features/prompt_feature_registry.json",
                    "/home/jaeho/projects_linux/ecoguide.v1/data/prompts/features/prompt_feature_registry.json",
                    os.path.join(os.getcwd(), "data", "prompts", "features", "prompt_feature_registry.json")
                ]

                registry_data = None
                loaded_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            registry_data = json.load(f)
                        loaded_path = path
                        logger.info(f"registry.json 로드 성공: {path}")
                        break

                if not registry_data:
                    logger.warning("registry.json을 찾을 수 없습니다. 기본 프롬프트를 사용합니다.")
                    return None

                # analysis_interface 기능의 프롬프트 찾기
                for feature in registry_data.get('features', []):
                    if feature.get('feature_id') == 'analysis_interface':
                        prompt = feature.get('default_prompt_template', None)
                        if prompt:
                            logger.info(f"analysis_interface 프롬프트 로드 성공 (길이: {len(prompt)} 자)")
                        return prompt

                logger.warning("analysis_interface 기능을 찾을 수 없습니다.")
                return None

            except Exception as e:
                logger.error(f"registry.json 로드 실패: {e}", exc_info=True)
                return None

        # Fallback 프롬프트 함수 정의
        def _get_fallback_prompt(classification_text: str) -> str:
            """fallback 프롬프트를 반환합니다."""
            return f"""당신은 대형폐기물 분류 전문가입니다. 다음의 분류 체계를 정확히 따라서 이미지를 분석해주세요.

{classification_text}

## 분석 지침

1. 위의 분류 체계에서 **정확한 대분류(primary_category)**를 선택하세요
2. 해당 대분류 아래의 **정확한 세분류(secondary_category)**를 선택하세요
3. 세분류는 반드시 위 목록에 있는 것 중에서만 선택하세요
4. 이미지의 물품을 식별하고 크기를 추정하세요
5. 신뢰도를 0.0~1.0 범위로 지정하세요

## 3D 크기(Width, Height, Depth) 정의
- **width_cm (가로)**: 정면에서 본 물체의 좌우 길이
- **height_cm (높이)**: 정면에서 본 물체의 상하 길이
- **depth_cm (깊이)**: 물체의 앞뒤 깊이 (안쪽으로 들어가는 정도)

## 응답 형식 (JSON만 반환, 다른 텍스트는 없음)

```json
{{
  "object_name": "구체적인 물품명",
  "primary_category": "대분류명 (위 목록에서 선택)",
  "secondary_category": "세분류명 (위 목록에서 선택)",
  "confidence": 0.0,
  "dimensions": {{
    "width_cm": 0,
    "height_cm": 0,
    "depth_cm": 0
  }},
  "reasoning": "판단 근거"
}}
```

**중요**: secondary_category는 반드시 위의 분류 체계 목록에 있는 정확한 이름으로 기입하세요."""

        # 분류 체계 텍스트 생성
        classification_text = build_waste_classification_text()

        # registry.json에서 프롬프트 로드 및 변수 바인딩
        registry_prompt = load_analysis_prompt_from_registry()

        if registry_prompt:
            # registry 프롬프트에 {CLASSIFICATION_TEXT} 변수 바인딩
            try:
                default_prompt = registry_prompt.format(CLASSIFICATION_TEXT=classification_text)
                logger.info("registry 프롬프트에 분류 체계 바인딩 성공")
            except Exception as e:
                logger.error(f"프롬프트 바인딩 실패: {e}")
                # fallback으로 기본 프롬프트 사용
                default_prompt = _get_fallback_prompt(classification_text)
        else:
            # fallback: 기본 프롬프트 사용
            logger.warning("registry 프롬프트 미로드 - fallback 프롬프트 사용")
            default_prompt = _get_fallback_prompt(classification_text)

        prompt = st.text_area(
            "프롬프트",
            value=default_prompt,
            height=200,
            key="analysis_prompt"
        )

        # 분석 실행
        analysis_step = AnalysisStep(app_context)
        if analysis_step.render(state, model, prompt):
            state.set_step('confirmation')
            st.rerun()

    # Step 3: 확인
    elif state.get_step() == 'confirmation':
        st.header("📋 분석 결과 확인")
        st.markdown("---")

        confirmation_step = ConfirmationStep(app_context)
        result = confirmation_step.render(state)

        if result:
            st.rerun()

    # Step 4: 완료
    elif state.get_step() == 'complete':
        st.header("✅ 분류 완료")
        st.markdown("---")

        complete_step = CompleteStep(app_context)
        complete_step.render(state)


if __name__ == "__main__":
    main()
