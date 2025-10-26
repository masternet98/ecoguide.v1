"""
분석 결과 표시 컴포넌트

LLM이 반환한 JSON 응답을 파싱해 표준화된 구조로 보여주고, 이어서
사용자가 즉시 확인/수정할 수 있도록 ConfirmationUI와 연결한다.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

import streamlit as st

from src.components.base import BaseComponent
from src.domains.analysis.ui.confirmation_ui import ConfirmationUI
from src.domains.analysis.ui.enhanced_confirmation_ui import EnhancedConfirmationUI


class ResultsDisplayComponent(BaseComponent):
    """분석 결과를 표준 형태로 보여주고 확인 단계로 넘기는 컴포넌트"""

    def render(self, result_container, output_text: Optional[str], raw_response: Any) -> None:
        """분석 결과와 원본 응답, 확인 UI까지 한 번에 처리한다."""

        normalized_result: Optional[Dict[str, Any]] = None

        with result_container.expander("📊 분석 결과", expanded=True):
            if output_text:
                normalized_result = self._display_parsed_output(output_text)
            else:
                st.info("모델에서 구조화된 JSON 응답을 반환하지 않았습니다. 원본 응답을 참고하세요.")

            self._display_raw_response(raw_response)

        if not normalized_result:
            return

        # 세션 상태에 최신 결과를 저장해 다른 페이지/컴포넌트에서 재사용할 수 있도록 한다.
        st.session_state.latest_analysis_result = normalized_result

        self._render_confirmation_interface(normalized_result)

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _display_parsed_output(self, output_text: str) -> Optional[Dict[str, Any]]:
        """LLM이 반환한 JSON을 파싱하고 표준 필드로 매핑한다."""

        parsing_successful = False
        parsing_error = None

        try:
            parsed = json.loads(output_text)
            parsing_successful = True
        except json.JSONDecodeError as e:
            parsing_error = str(e)

            # JSON 파싱 실패 시 텍스트에서 정보 추출
            st.info("⚠️ 구조화된 JSON 형식을 인식하지 못했습니다. 텍스트 분석 모드로 진행합니다.")

            with st.expander("📝 원본 응답 보기", expanded=False):
                st.code(output_text)
                if parsing_error:
                    st.caption(f"파싱 오류: {parsing_error}")

            text_lower = output_text.lower()

            # 기본값으로 구성
            object_name = "알 수 없음"
            primary_category = "MISC"
            secondary_category = "MISC_UNCLASS"

            # 간단한 키워드 매칭으로 정보 추출
            if "선풍기" in text_lower:
                object_name = "선풍기"
                primary_category = "APPL"
                secondary_category = "APPL_OTHER"
            elif "냉장고" in text_lower:
                object_name = "냉장고"
                primary_category = "APPL"
                secondary_category = "APPL_FRIDGE"
            elif "가전" in text_lower:
                primary_category = "APPL"
            elif "가구" in text_lower:
                primary_category = "FURN"

            # 파싱된 것처럼 구성
            parsed = {
                "object_name": object_name,
                "primary_category": primary_category,
                "secondary_category": secondary_category,
                "confidence": 0.7,
                "reasoning": f"텍스트 분석을 통해 {object_name}으로 식별되었습니다.",
                "_parsing_failed": True
            }

        # 더 유연한 필드명 매핑
        object_name = (parsed.get("object_name") or
                      parsed.get("detected_item") or
                      parsed.get("object") or
                      parsed.get("item") or
                      "알 수 없음")

        primary_category = (parsed.get("primary_category") or
                           parsed.get("main_category") or
                           "MISC")

        secondary_category = (parsed.get("secondary_category") or
                             parsed.get("sub_category") or
                             parsed.get("category") or
                             "MISC_UNCLASS")
        size_type = parsed.get("size_type", parsed.get("size_rule", "SIZE_FLAT"))
        confidence = float(parsed.get("confidence", 0.8))  # 기본 신뢰도 0.8로 설정
        dimensions = parsed.get("dimensions", parsed.get("size_estimation", {})) or {}
        reasoning = parsed.get("reasoning", f"{object_name}으로 분석되었습니다.")

        width = dimensions.get("width_cm")
        height = dimensions.get("height_cm")
        depth = dimensions.get("depth_cm")
        dimension_sum = dimensions.get("dimension_sum_cm")
        if dimension_sum is None and all(value is not None for value in (width, height, depth)):
            dimension_sum = float(width) + float(height) + float(depth)

        size_estimation = {
            "width_cm": width,
            "height_cm": height,
            "depth_cm": depth,
            "dimension_sum_cm": dimension_sum
        }

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**감지된 품목:** {object_name}")
            st.write(f"**1차 분류:** {primary_category}")
            st.write(f"**2차 분류:** {secondary_category}")
            st.write(f"**크기 규칙:** {size_type}")
            if size_estimation["width_cm"] or size_estimation["height_cm"] or size_estimation["depth_cm"]:
                st.write(
                    "**추정 크기:** "
                    f"가로 {size_estimation['width_cm']}cm / "
                    f"세로 {size_estimation['height_cm']}cm / "
                    f"높이 {size_estimation['depth_cm']}cm"
                )
            else:
                st.write("**추정 크기:** 정보 없음")

        with col2:
            st.metric("신뢰도", f"{confidence:.0%}")
            if reasoning:
                st.info(f"판단 근거: {reasoning}")

        normalized_result = {
            "object_name": object_name,
            "primary_category": primary_category,
            "secondary_category": secondary_category,
            "size_type": size_type,
            "confidence": confidence,
            "dimensions": size_estimation,
            "reasoning": reasoning,
            "raw_response": parsed,
            # 하위 호환 필드
            "category": secondary_category,
            "size_estimation": size_estimation
        }

        return normalized_result

    def _display_raw_response(self, raw_response: Any) -> None:
        """LLM에서 반환된 원본 응답을 그대로 보여준다."""

        with st.expander("🔍 원본 응답(JSON) 자세히 보기", expanded=False):
            try:
                st.json(raw_response)
            except Exception:
                st.code(str(raw_response))

    def _render_confirmation_interface(self, vision_result: Dict[str, Any]) -> None:
        """확인 UI를 연결하고 사용자가 입력한 결과를 세션에 저장한다."""

        # 이미지 ID 생성 (간단한 타임스탬프 기반)
        import uuid
        image_id = st.session_state.get('image_id', str(uuid.uuid4())[:8])

        # UI 선택 옵션
        ui_choice = st.radio(
            "확인 UI 선택",
            options=["🎯 개선된 지능형 UI (추천)", "📋 기본 UI"],
            index=0,
            key=f"ui_choice_{image_id}",
            help="개선된 UI는 waste_types.json 기반 계층 구조와 AI 추천을 활용합니다"
        )

        if ui_choice.startswith("🎯"):
            # 새로운 개선된 UI 사용
            confirmation_ui = EnhancedConfirmationUI(
                app_context=self.app_context,
                image_id=image_id,
                analysis_result=vision_result
            )
        else:
            # 기존 UI 사용
            confirmation_ui = ConfirmationUI(
                app_context=self.app_context,
                image_id=image_id,
                analysis_result=vision_result
            )

        confirmation_result = confirmation_ui.render()

        if confirmation_result:
            st.session_state.confirmed_analysis = confirmation_result

            # 확인 결과의 구조에 맞게 상태 확인
            if confirmation_result.get("user_confirmed"):
                st.success("✅ 사용자 확인이 완료되었습니다. 배출 방법 안내 단계로 이동할 수 있습니다.")

                # 빠른 확인인지 상세 확인인지 표시
                if confirmation_result.get("quick_confirm"):
                    st.info("🚀 빠른 확인을 통해 효율적으로 진행되었습니다.")
                else:
                    st.info("📋 상세 확인을 통해 품질 높은 피드백을 제공해주셨습니다.")
            else:
                st.warning("⚠️ 수정이 필요한 사항이 있습니다. 운영팀이 검토하여 AI 정확도 개선에 활용하겠습니다.")

            with st.expander("🔎 확인 결과 (개발용)", expanded=False):
                st.json(confirmation_result, expanded=False)
