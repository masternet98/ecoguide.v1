"""
분석 인터페이스 컴포넌트 - 전체 이미지 분석 인터페이스를 통합 관리합니다.
"""
import streamlit as st
from src.components.base import BaseComponent
from src.components.base_ui import AnalysisControlComponent
from src.app.core.prompt_feature_decorators import prompt_feature
from src.domains.analysis.ui.image_input import ImageInputComponent
from src.domains.analysis.ui.image_analysis import ImageAnalysisComponent
from src.domains.analysis.ui.results_display import ResultsDisplayComponent
from src.domains.analysis.ui.confirmation_ui import ConfirmationUI
from src.domains.prompts.ui.prompt_manager import PromptManagerComponent
from src.domains.prompts.ui.prompt_selector import PromptSelectorComponent
from src.domains.district.ui.location_selector import LocationSelectorComponent
from src.domains.district.ui.disposal_guide import DisposalGuideUI
from src.app.core.session_state import SessionStateManager


@prompt_feature(
    feature_id="analysis_interface",
    name="분석 인터페이스",
    description="이미지 분석을 위한 통합 인터페이스 컴포넌트",
    category="interface",
    required_services=["openai_service", "prompt_service"],
    default_prompt_template="""# 대형폐기물 이미지 분석 및 분류 시스템

이미지를 분석하여 인천광역시 대형폐기물 분류 체계에 따라 정확히 분류하고 크기를 측정해주세요.

## 분류 체계 (4단계)

### 1차 분류 (필수)
- FURN: 가구 (침대, 소파, 테이블, 의자 등)
- APPL: 가전 (냉장고, 세탁기, TV, 에어컨 등)
- HLTH: 건강/의료용품 (병원침대, 휠체어 등)
- LIFE: 생활/주방용품 (싱크대, 욕조, 수납함 등)
- SPOR: 스포츠/레저 (운동기구, 자전거 등)
- MUSC: 악기 (피아노, 드럼 등)
- HOBB: 조경/장식 (화분, 트리 등)
- MISC: 기타 (공업용, 건축자재 등)

### 2차 분류 (세부 카테고리)
예시: FURN_BED(침대), FURN_SOFA(소파), APPL_FRIDGE(냉장고), APPL_WASH(세탁기)

### 3차 분류 (크기 측정 방식)
- SIZE_DIM_SUM: 가로+세로+높이 합계 (침대, 소파 등)
- SIZE_WIDTH: 가로 길이 기준 (테이블, 책상 등)
- SIZE_AREA: 면적 기준 (싱크대, 문짝 등)
- SIZE_HEIGHT: 높이 기준 (냉장고 등)
- SIZE_WEIGHT: 무게 기준 (헬스기구 등)
- SIZE_FLAT: 고정요금 (소형 전자제품 등)

## 크기 측정 정확도 향상 방법
1. 손 크기를 기준점으로 활용 (성인 손 길이 약 18-20cm)
2. 주변 사물과의 비례 관계 파악
3. 일반적인 제품 규격 지식 활용

## JSON 응답 형식 (필수)
```json
{
  "primary_category": "FURN",
  "secondary_category": "FURN_BED",
  "size_type": "SIZE_DIM_SUM",
  "object_name": "침대",
  "dimensions": {
    "width_cm": 200,
    "height_cm": 120,
    "depth_cm": 30,
    "dimension_sum_cm": 350
  },
  "confidence": 0.85,
  "reasoning": "매트리스와 프레임이 보이는 2인용 침대로 판단됩니다."
}
```

정확한 분류와 치수 측정을 위해 신중히 분석해주세요.""",
    metadata={"component_type": "interface", "ui_type": "streamlit"}
)
class AnalysisInterfaceComponent(BaseComponent):
    """이미지 분석 인터페이스를 통합 관리하는 컴포넌트입니다."""
    
    def __init__(self, app_context):
        super().__init__(app_context)
        self.image_input = ImageInputComponent(app_context)
        self.image_analysis = ImageAnalysisComponent(app_context)
        self.results_display = ResultsDisplayComponent(app_context)
        self.prompt_manager = PromptManagerComponent(app_context)
        self.prompt_selector = PromptSelectorComponent(app_context)
        self.location_selector = LocationSelectorComponent(app_context)
    
    def render(self, model: str) -> None:
        """
        이미지 분석 인터페이스를 렌더링합니다.

        Args:
            model: 사용할 모델명
        """
        # 배출 안내 페이지 표시 여부 확인
        if getattr(st.session_state, 'show_disposal_guide', False):
            self._render_disposal_guide()
            return

        # 위치 선택 UI 먼저 렌더링
        location_selected = self.location_selector.render()

        # # 위치 정보 요약 표시 (위치가 선택된 경우)
        # location_summary = SessionStateManager.get_current_location_summary()
        # if location_summary:
        #     st.info(f"📍 **선택된 위치**: {location_summary}")

        st.markdown("---")  # 구분선 추가

        # 동적 프롬프트 렌더링 (RAG 컨텍스트 포함)
        default_prompt = self._get_analysis_prompt_with_context(location_selected)

        st.subheader("📝 프롬프트 설정")

        # 관리되는 프롬프트 선택 UI
        selected_prompt_text = self.prompt_selector.render("camera_analysis")

        # 선택된 프롬프트가 있으면 사용, 없으면 기본 프롬프트 사용
        initial_prompt = selected_prompt_text if selected_prompt_text else default_prompt

        # 프롬프트 입력/편집 UI
        prompt = st.text_area(label="입력 프롬프트", value=initial_prompt, height=100, key="prompt_input")
        
        # 탭 선택 및 전환 감지
        tab_selector = st.radio("탭 선택", ["📷 카메라", "🖼️ 갤러리"], index=0)
        SessionStateManager.handle_tab_switch(tab_selector)
        
        # 이미지 입력 처리
        selected_bytes = self.image_input.render(tab_selector)
        
        # 선택된 이미지가 없으면 분석 결과 초기화
        if not selected_bytes:
            SessionStateManager.update_analysis_results(None, None)
            return
        
        # 이미지 분석 처리 (버튼 포함)
        output_text, raw_response = self.image_analysis.render(selected_bytes, prompt, model)
        
        # 분석 결과 표시 (분석 버튼 아래에 확장형으로 표시)
        if output_text is not None or raw_response is not None:
            st.markdown("---")  # 구분선 추가

            # 결과 표시를 위한 컨테이너 생성
            results_container = st.container()
            self.results_display.render(results_container, output_text, raw_response)

    def _render_disposal_guide(self):
        """배출 안내 페이지를 렌더링합니다."""
        disposal_guide = DisposalGuideUI(self.app_context)

        # 확인된 분석 결과가 있으면 함께 전달
        confirmed_analysis = getattr(st.session_state, 'confirmed_analysis', None)
        disposal_guide.render(confirmed_analysis)

    def _get_analysis_prompt_with_context(self, location_selected=None) -> str:
        """RAG 컨텍스트가 포함된 분석 프롬프트를 가져옵니다."""
        try:
            # 프롬프트 서비스에서 향상된 프롬프트 가져오기
            prompt_service = self.get_service('prompt_service')
            if not prompt_service:
                return self._get_fallback_prompt()

            # enhanced_waste_analysis 프롬프트 조회
            prompt_template = prompt_service.get_prompt("enhanced_waste_analysis")
            if not prompt_template:
                # 이름으로 검색 시도
                prompts = prompt_service.search_prompts("enhanced_waste_analysis")
                if prompts:
                    prompt_template = prompts[0]
                else:
                    return self._get_fallback_prompt()

            # RAG 컨텍스트 생성 (waste_types.json 포함)
            rag_service = self.get_service('rag_context_service')
            if rag_service:
                if location_selected and location_selected.get('success'):
                    location_data = location_selected.get('data', {})
                    context_vars = rag_service.render_context_variables(
                        location_data={
                            'city': location_data.get('sido', ''),
                            'district': location_data.get('sigungu', '')
                        },
                        include_waste_classification=True
                    )
                else:
                    # 위치 정보가 없어도 waste_types.json 기반 분류는 포함
                    context_vars = rag_service.render_context_variables(
                        include_waste_classification=True
                    )
            else:
                # RAG 서비스가 없으면 기본 컨텍스트 사용
                context_vars = {
                    "location_context": "기본 배출 안내 정보가 표시됩니다.",
                    "waste_classification_context": "### 분류 기준\n기본 분류 정보를 사용합니다."
                }

            # 프롬프트 렌더링
            prompt_renderer = prompt_service.renderer
            rendered_prompt = prompt_renderer.render_prompt(prompt_template, context_vars)

            return rendered_prompt if rendered_prompt else self._get_fallback_prompt()

        except Exception as e:
            self.logger.warning(f"Dynamic prompt loading failed: {e}")
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """폴백 프롬프트를 반환합니다."""
        return """당신은 대형폐기물 분석 전문가입니다. 이미지를 분석하여 다음 형식으로 응답해주세요:

```json
{
  "object_name": "물체명",
  "category": "분류",
  "disposal_method": "배출 방법",
  "confidence": "신뢰도 (0.0-1.0)"
}
```"""