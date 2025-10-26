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

        col1, col2 = st.columns(2)

        # 대분류 선택
        with col1:
            main_categories = waste_service.get_main_categories() if waste_service else []
            selected_main = st.selectbox(
                "대분류",
                options=main_categories,
                index=main_categories.index(normalized['primary_category']) if normalized['primary_category'] in main_categories else 0,
                key="result_main_category"
            )
            normalized['primary_category'] = selected_main

        # 세분류 선택
        with col2:
            if waste_service:
                subcategories = waste_service.get_subcategories(selected_main)
                sub_options = [sub.get('명칭', '') for sub in subcategories]

                selected_sub = st.selectbox(
                    "세분류",
                    options=sub_options,
                    index=sub_options.index(normalized['secondary_category']) if normalized['secondary_category'] in sub_options else 0,
                    key="result_sub_category"
                )
                normalized['secondary_category'] = selected_sub
            else:
                st.write(f"**세분류:** {normalized['secondary_category']}")

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
        st.subheader("📏 크기 정보")

        dimensions = normalized.get('dimensions', {})

        if dimensions and any(dimensions.values()):
            # 크기 정보가 있는 경우 표시
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("가로", f"{dimensions.get('width_cm', '-')} cm")

            with col2:
                st.metric("세로", f"{dimensions.get('height_cm', '-')} cm")

            with col3:
                st.metric("높이", f"{dimensions.get('depth_cm', '-')} cm")

            with col4:
                dim_sum = dimensions.get('dimension_sum_cm')
                if dim_sum:
                    st.metric("합계", f"{dim_sum} cm")

            # 크기 수정 옵션
            modify_size = st.checkbox("크기를 수정하시겠습니까?", key="modify_size_info")

            if modify_size:
                size_col1, size_col2, size_col3 = st.columns(3)

                with size_col1:
                    width = st.number_input("가로 (cm)", min_value=0.0, value=float(dimensions.get('width_cm') or 0), step=1.0, key="mod_width")

                with size_col2:
                    height = st.number_input("세로 (cm)", min_value=0.0, value=float(dimensions.get('height_cm') or 0), step=1.0, key="mod_height")

                with size_col3:
                    depth = st.number_input("높이 (cm)", min_value=0.0, value=float(dimensions.get('depth_cm') or 0), step=1.0, key="mod_depth")

                normalized['dimensions'] = {
                    'width_cm': width if width > 0 else None,
                    'height_cm': height if height > 0 else None,
                    'depth_cm': depth if depth > 0 else None,
                    'dimension_sum_cm': width + height + depth if any([width, height, depth]) else None
                }
        else:
            # 크기 정보가 없는 경우
            st.info("💡 크기 정보가 제공되지 않았습니다")

            provide_size = st.checkbox(
                "직접 크기를 입력하시겠습니까?",
                key="provide_size_manual"
            )

            if provide_size:
                st.markdown("**실제 크기를 입력해주세요 (단위: cm)**")
                size_col1, size_col2, size_col3 = st.columns(3)

                with size_col1:
                    width = st.number_input("가로 (cm)", min_value=0.0, step=1.0, key="manual_width")

                with size_col2:
                    height = st.number_input("세로 (cm)", min_value=0.0, step=1.0, key="manual_height")

                with size_col3:
                    depth = st.number_input("높이 (cm)", min_value=0.0, step=1.0, key="manual_depth")

                if any([width > 0, height > 0, depth > 0]):
                    normalized['dimensions'] = {
                        'width_cm': width if width > 0 else None,
                        'height_cm': height if height > 0 else None,
                        'depth_cm': depth if depth > 0 else None,
                        'dimension_sum_cm': width + height + depth
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

        # 피드백 저장 및 라벨링 데이터 저장
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
        if st.button("📖 배출 방법 안내", use_container_width=True, key="show_disposal"):
            st.info(f"**{normalized['object_name']}** ({normalized['primary_category']}) 배출 방법:\n\n"
                   f"1. 위치 확인\n"
                   f"2. 배출 가능 여부 확인\n"
                   f"3. 담당 부서에 신청\n\n"
                   f"자세한 사항은 해당 지역의 폐기물 관리 부서에 문의하세요.")

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

        from src.domains.prompts.ui.prompt_selector import PromptSelectorComponent
        prompt_selector = PromptSelectorComponent(app_context)
        selected_prompt = prompt_selector.render("camera_analysis")

        # 기본 프롬프트
        default_prompt = """이 이미지에 있는 제품을 대형폐기물로 배출하려고 합니다.

대형폐기물 배출 시 제품의 크기가 가격에 중요한 영향을 미치므로, 다음 정보를 JSON 형식으로 분석해 주세요:

```json
{
  "object_name": "제품명",
  "primary_category": "대분류 (가구/가전/건강/의료용품/생활/주방용품/스포츠/레저/악기/조경/장식/행사용품/기타)",
  "secondary_category": "세분류 (예: 침대/매트리스, 냉장고 등)",
  "confidence": "신뢰도 (0.0~1.0)",
  "dimensions": {
    "width_cm": "가로 (cm)",
    "height_cm": "세로 (cm)",
    "depth_cm": "깊이 (cm)"
  },
  "reasoning": "판단 근거"
}
```"""

        prompt = selected_prompt if selected_prompt else default_prompt

        prompt = st.text_area(
            "프롬프트",
            value=prompt,
            height=150,
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
