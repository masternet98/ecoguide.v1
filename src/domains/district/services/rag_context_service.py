"""
지역 기반 RAG (Retrieval Augmented Generation) 컨텍스트 서비스입니다.

지역별 폐기물 배출 정보, 수수료, 규정을 조회하여 프롬프트에 주입할 컨텍스트를 생성합니다.
"""
import json
import os
from typing import Dict, Optional, Any, List
from src.app.core.base_service import BaseService
from src.app.core.logger import get_logger


class RAGContextService(BaseService):
    """지역 기반 RAG 컨텍스트를 생성하는 서비스입니다."""

    def __init__(self, config):
        super().__init__(config)
        self.logger = get_logger(__name__)
        self._waste_types_data = None

    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "rag_context_service"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "1.0.0"

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "지역별 RAG 컨텍스트 생성 서비스"

    def get_location_context(self, location_data: Dict[str, Any]) -> str:
        """
        지역 정보를 바탕으로 RAG 컨텍스트를 생성합니다.

        Args:
            location_data: 위치 정보 데이터
                - city: 시/도 (예: "인천광역시")
                - district: 구/군 (예: "서구")
                - additional_info: 추가 정보

        Returns:
            프롬프트에 주입할 지역 컨텍스트 문자열
        """
        if not location_data:
            return self._get_default_context()

        city = location_data.get('city', '')
        district = location_data.get('district', '')
        location_name = f"{city} {district}".strip()

        # 지역별 특화 정보 생성
        context = f"""### 🏠 {location_name} 대형폐기물 배출 안내

**배출 방법:**
- 사전신고제: 배출 전 해당 구청에 신고 필수
- 신고 방법: 온라인 신고 또는 전화 신고
- 배출 일정: 신고 후 지정된 날짜에 배출
- 배출 시간: 오후 6시 이후 ~ 자정 이전

**수수료 체계:**
- 크기별 차등 적용 (소형/중형/대형)
- 재질별 수수료 차이 (목재, 금속, 플라스틱 등)
- 현금 또는 신용카드 결제 가능

**특별 주의사항:**
- 분리수거 가능한 부분은 사전 분리
- 유독물질 포함 제품은 별도 처리
- 과대형 폐기물은 별도 상담 필요

**문의처:**
- {location_name} 청소과: (지역별 연락처)
- 온라인 신고 시스템: (지역별 웹사이트)"""

        # 특정 지역에 대한 특화 정보 추가
        if "인천" in city and "서구" in district:
            context += """

**인천 서구 특화 정보:**
- 월 2회 수거 (매월 2째, 4째 주)
- 아파트 단지는 관리사무소 통합 신고 가능
- 재활용센터: 인천 서구 청라동 소재
- 특별 할인: 3개 이상 동시 배출 시 10% 할인"""

        return context

    def _get_default_context(self) -> str:
        """기본 컨텍스트를 반환합니다."""
        return """### 🏠 대형폐기물 배출 기본 안내

**일반 배출 방법:**
- 해당 지역 관할 구청에 사전신고
- 신고 후 지정된 날짜와 장소에 배출
- 배출 수수료는 크기와 재질에 따라 차등 적용

**공통 주의사항:**
- 분리 가능한 부품은 사전 분리하여 재활용품으로 배출
- 배출 전 청소 및 이물질 제거
- 지정된 시간과 장소 준수

**추가 정보:**
- 정확한 수수료와 배출 일정은 해당 지역 구청 확인 필요
- 위치 선택 시 더 자세한 지역별 정보를 제공합니다"""

    def get_waste_type_context(self, waste_category: str) -> str:
        """
        폐기물 유형별 특화 컨텍스트를 생성합니다.

        Args:
            waste_category: 폐기물 카테고리 (예: "가구", "가전")

        Returns:
            폐기물 유형별 컨텍스트
        """
        waste_contexts = {
            "가구": """
**가구류 배출 특칙:**
- 목재가구: 철제 부품 분리 후 배출
- 패브릭 소파: 금속 스프링 별도 분리
- 유리 포함 가구: 유리 안전 포장 필수""",

            "가전": """
**가전제품 배출 특칙:**
- 냉장고/에어컨: 냉매 처리 필요 (별도 수수료)
- 세탁기: 급수/배수 호스 제거
- TV/모니터: 전자파 차단 포장 권장""",

            "전자제품": """
**전자제품 배출 특칙:**
- 개인정보 완전 삭제 필수
- 배터리 별도 분리 배출
- 소형 전자제품은 재활용센터 직접 방문 가능"""
        }

        return waste_contexts.get(waste_category, "")

    def render_context_variables(self,
                                location_data: Optional[Dict[str, Any]] = None,
                                waste_category: Optional[str] = None,
                                additional_context: Optional[Dict[str, str]] = None,
                                include_waste_classification: bool = True) -> Dict[str, str]:
        """
        프롬프트 변수 치환용 컨텍스트를 렌더링합니다.

        Args:
            location_data: 위치 정보
            waste_category: 폐기물 카테고리
            additional_context: 추가 컨텍스트
            include_waste_classification: waste_types.json 분류 기준 포함 여부

        Returns:
            프롬프트 변수 딕셔너리
        """
        context_parts = []

        # waste_types.json 기반 분류 기준 추가 (가장 먼저 표시)
        if include_waste_classification:
            classification_context = self.get_waste_classification_context()
            if classification_context:
                context_parts.append(classification_context)

        # 지역 컨텍스트 추가
        if location_data:
            context_parts.append(self.get_location_context(location_data))
        else:
            context_parts.append(self._get_default_context())

        # 폐기물 유형별 컨텍스트 추가
        if waste_category:
            waste_context = self.get_waste_type_context(waste_category)
            if waste_context:
                context_parts.append(waste_context)

        # 추가 컨텍스트 병합
        if additional_context:
            for key, value in additional_context.items():
                context_parts.append(f"**{key}:** {value}")

        # 최종 컨텍스트 조합
        full_context = "\n\n".join(context_parts)

        return {
            "location_context": full_context,
            "waste_classification_context": self.get_waste_classification_context() if include_waste_classification else "",
            "timestamp": self._get_timestamp(),
            "version": self.get_service_version()
        }

    def _get_timestamp(self) -> str:
        """현재 타임스탬프를 반환합니다."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _load_waste_types_data(self) -> Dict[str, Any]:
        """waste_types.json 데이터를 로딩합니다."""
        if self._waste_types_data is not None:
            return self._waste_types_data

        try:
            # 프로젝트 루트에서 waste_types.json 파일 경로 찾기
            possible_paths = [
                "uploads/waste_types/waste_types.json",
                "../uploads/waste_types/waste_types.json",
                "../../uploads/waste_types/waste_types.json",
                os.path.join(os.getcwd(), "uploads", "waste_types", "waste_types.json")
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self._waste_types_data = json.load(f)
                    self.logger.info(f"waste_types.json loaded from: {path}")
                    return self._waste_types_data

            self.logger.warning("waste_types.json not found in any expected location")
            return {}

        except Exception as e:
            self.logger.error(f"Failed to load waste_types.json: {e}")
            return {}

    def get_waste_classification_context(self) -> str:
        """waste_types.json 기반의 분류 기준 컨텍스트를 생성합니다."""
        waste_data = self._load_waste_types_data()
        if not waste_data:
            return "분류 기준 데이터를 로딩할 수 없습니다."

        context_lines = ["### 분류 기준 (waste_types.json 기반)", ""]

        for i, (category, details) in enumerate(waste_data.items(), 1):
            # 대분류
            context_lines.append(f"{i}. **{category}** - {details.get('설명', '')}")

            # 세분류 추가 (모든 세분류를 표시하여 AI가 정확히 분류하도록 함)
            subcategories = details.get('세분류', [])
            if subcategories:
                for subcat in subcategories:  # 모든 세분류 표시
                    name = subcat.get('명칭', '')
                    examples = subcat.get('예시', [])
                    if examples:
                        # 예시를 모두 표시 (AI가 정확히 참고할 수 있도록)
                        example_text = f" ({', '.join(examples)})"
                    else:
                        example_text = ""
                    context_lines.append(f"   - {name}{example_text}")

            context_lines.append("")  # 빈 줄 추가

        return "\n".join(context_lines)

    def get_enhanced_waste_categories(self) -> List[str]:
        """waste_types.json에서 모든 카테고리 이름을 반환합니다."""
        waste_data = self._load_waste_types_data()
        return list(waste_data.keys()) if waste_data else []

    def get_category_details(self, category: str) -> Dict[str, Any]:
        """특정 카테고리의 세부 정보를 반환합니다."""
        waste_data = self._load_waste_types_data()
        return waste_data.get(category, {}) if waste_data else {}

    def search_disposal_guidance(self, location_code: str, waste_category: str) -> Dict[str, Any]:
        """
        선택된 지역(location_code)을 기반으로 district_links 데이터에서
        4개의 배출정보 URL을 정확하게 추출합니다.

        Args:
            location_code: 지역 코드 (예: "인천광역시_서구" - sido_sigungu 형식)
            waste_category: 폐기물 카테고리 (예: "가구", "가전") - 현재는 미사용

        Returns:
            배출정보 4개 변수를 포함하는 딕셔너리:
            {
                'success': True/False,
                'waste_detail_info': 'info_url의 URL 또는 "URL없음"',
                'waste_system_info': 'system_url의 URL 또는 "URL없음"',
                'waste_fee_info': 'fee_url의 URL 또는 "URL없음"',
                'appliance_info': 'appliance_url의 URL 또는 기본값'
            }
        """
        try:
            from src.domains.infrastructure.services.link_collector_service import load_registered_links
            from src.app.core.config import load_config

            self.logger.info(f"search_disposal_guidance 호출: location_code='{location_code}'")

            config = load_config()
            registered_links_data = load_registered_links(config)
            registered_links = registered_links_data.get("links", {})

            self.logger.debug(f"등록된 district_links 키 목록: {list(registered_links.keys())}")

            # 지역 코드로 정확하게 일치하는 링크 정보 조회
            link_info = registered_links.get(location_code, {})

            if not link_info:
                self.logger.warning(f"District links에서 '{location_code}' 정보를 찾을 수 없음")
                return {
                    'success': False,
                    'waste_detail_info': '',
                    'waste_system_info': '',
                    'waste_fee_info': '',
                    'appliance_info': ''
                }

            # district_links에서 4개 URL을 정확하게 추출
            info_url = link_info.get('info_url', '') or ''
            system_url = link_info.get('system_url', '') or ''
            fee_url = link_info.get('fee_url', '') or ''
            appliance_url = link_info.get('appliance_url', '') or 'https://15990903.or.kr/portal/main/main.do'

            self.logger.info(
                f"District links 조회 성공 ({location_code}): "
                f"info_url={bool(info_url)}, system_url={bool(system_url)}, "
                f"fee_url={bool(fee_url)}, appliance_url={bool(appliance_url)}"
            )

            # 결과 구성: URL을 그대로 반환
            result = {
                'success': True,
                'waste_detail_info': info_url if info_url else "배출정보 URL없음",
                'waste_system_info': system_url if system_url else "시스템 URL없음",
                'waste_fee_info': fee_url if fee_url else "수수료 URL없음",
                'appliance_info': appliance_url
            }

            self.logger.debug(f"반환 결과: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to search disposal guidance for '{location_code}': {e}", exc_info=True)
            return {
                'success': False,
                'waste_detail_info': '',
                'waste_system_info': '',
                'waste_fee_info': '',
                'appliance_info': ''
            }

