"""
세부내역 콘텐츠 추출을 위한 프롬프트 관리 모듈입니다.

이 모듈은 배출정보와 수수료 정보 추출을 위한 프롬프트를
프롬프트 시스템에 등록하고 관리합니다.
"""
from typing import Optional, Dict, Any
from src.app.core.prompt_types import PromptCategory, PromptStatus


def get_info_extraction_prompt_template() -> str:
    """배출정보 추출 프롬프트 템플릿 반환"""
    return """당신은 대형폐기물 배출 정보 분석 전문가입니다.{district_context}

다음 콘텐츠에서 배출정보를 추출하여 마크다운 형식으로 정리하세요:

---
{content}
---

다음과 같은 마크다운 형식으로 응답하세요 (필요한 섹션만 포함):

## 📦 배출 가능 물품
목록을 쉼표로 구분하여 작성

## ⛔ 배출 불가능 물품
목록을 쉼표로 구분하여 작성

## 🚚 배출 방법
배출 방법 설명

## 📅 수거 일정
수거 일정 설명

## 📞 신청 방법
### 온라인
온라인 신청 방법 및 링크

### 전화
전화번호 및 상담 시간

### 방문
방문 장소 및 주소

## 💰 기본 수수료
기본 수수료 설명

## 👥 연락처
- **담당자/기관**: 전화번호 또는 링크 (용도 설명)
- 여러 항목 가능

## ⏰ 운영 시간
운영 시간 설명

## 📌 추가 정보
기타 중요 정보

주의사항:
1. 페이지에 명시된 정보만 포함하세요
2. 명시되지 않은 정보는 절대 추가하지 마세요 (추론 금지)
3. 필요 없는 섹션은 생략해도 됩니다
4. 마크다운 형식만 응답하세요 (JSON이 아닙니다)"""


def get_fee_extraction_prompt_template() -> str:
    """수수료 정보 추출 프롬프트 템플릿 반환"""
    return """당신은 대형폐기물 수수료 정보 분석 전문가입니다.{district_context}

다음 콘텐츠에서 수수료 정보를 추출하여 마크다운 형식으로 정리하세요:

---
{content}
---

다음과 같은 마크다운 형식으로 응답하세요 (필요한 섹션만 포함):

## 📐 배출 기준
물품의 크기나 종류에 따른 배출 기준 설명

## 💵 요금 표

### 카테고리명
- **기준1**: 요금
- **기준2**: 요금

### 다른 카테고리명
- **기준1**: 요금
- **기준2**: 요금

## 📅 예약 방법
예약 방법 설명 (온라인, 전화 등)

## 💳 결제 방법
결제 수단 설명

## 🎁 할인
할인 정보 (있으면)

## 📌 추가 정보
기타 중요 정보

주의사항:
1. 페이지에 명시된 정보만 포함하세요
2. 명시되지 않은 카테고리는 절대 추가하지 마세요 (추론 금지)
3. 필요 없는 섹션은 생략해도 됩니다
4. 요금은 한글 표기 유지 (예: "10,000원~20,000원")
5. 마크다운 형식만 응답하세요 (JSON이 아닙니다)"""


def register_detail_content_prompts(prompt_service) -> Dict[str, str]:
    """
    세부내역 콘텐츠 추출 프롬프트를 프롬프트 서비스에 등록합니다.

    주의: 이미 등록된 프롬프트가 있으면 건너뜁니다 (중복 방지)

    Args:
        prompt_service: PromptService 인스턴스

    Returns:
        등록된 프롬프트 ID 딕셔너리 {'info': prompt_id, 'fee': prompt_id}
    """
    from src.app.core.logger import get_logger
    logger = get_logger(__name__)

    try:
        # 1단계: 기존 프롬프트 확인 (중복 방지)
        existing_info_prompts = prompt_service.search_prompts("detail_extraction_disposal_info")
        existing_fee_prompts = prompt_service.search_prompts("detail_extraction_fee_info")

        if existing_info_prompts and existing_fee_prompts:
            logger.info("배출정보/수수료 프롬프트는 이미 등록되어 있습니다 (중복 방지)")
            return {
                'info': existing_info_prompts[0].id,
                'fee': existing_fee_prompts[0].id
            }

        # 2단계: 프롬프트 생성 (PromptService에만)
        info_prompt = prompt_service.create_prompt(
            name="detail_extraction_disposal_info",
            description="지역별 대형폐기물 배출정보를 URL/PDF 콘텐츠에서 추출합니다",
            category=PromptCategory.CUSTOM,
            template=get_info_extraction_prompt_template(),
            created_by="system",
            tags=["detail_content", "disposal_info", "infrastructure"],
            metadata={
                "feature_type": "detail_content",
                "content_type": "info",
                "variables": ["district_context", "content"],
                "response_format": "json",
                "source_domain": "infrastructure"
            }
        )

        fee_prompt = prompt_service.create_prompt(
            name="detail_extraction_fee_info",
            description="지역별 대형폐기물 수수료 정보를 URL/PDF 콘텐츠에서 추출합니다",
            category=PromptCategory.CUSTOM,
            template=get_fee_extraction_prompt_template(),
            created_by="system",
            tags=["detail_content", "fee_info", "infrastructure"],
            metadata={
                "feature_type": "detail_content",
                "content_type": "fee",
                "variables": ["district_context", "content"],
                "response_format": "json",
                "source_domain": "infrastructure"
            }
        )

        # 3단계: Feature 등록 (PromptFeatureRegistry에 ID만 저장)
        from src.app.core.prompt_feature_registry import PromptFeatureRegistry
        registry = PromptFeatureRegistry()

        info_prompt_id = info_prompt.id if hasattr(info_prompt, 'id') else str(info_prompt)
        fee_prompt_id = fee_prompt.id if hasattr(fee_prompt, 'id') else str(fee_prompt)

        # 배출정보 세부내역 기능 등록
        registry.register_feature(
            feature_id="detail_content_disposal_info",
            name="세부내역 배출정보 관리",
            description="지역별 대형폐기물 배출정보를 자동으로 추출하고 관리합니다",
            category="infrastructure",
            is_active=True,
            required_services=["openai_service"],
            default_prompt_template="",  # 빈 문자열 (PromptService에서 로드)
            metadata={
                "content_type": "info",
                "feature_type": "detail_content",
                "prompt_id": info_prompt_id
            }
        )

        # 수수료 세부내역 기능 등록
        registry.register_feature(
            feature_id="detail_content_fee_info",
            name="세부내역 수수료 관리",
            description="지역별 대형폐기물 수수료 정보를 자동으로 추출하고 관리합니다",
            category="infrastructure",
            is_active=True,
            required_services=["openai_service"],
            default_prompt_template="",  # 빈 문자열 (PromptService에서 로드)
            metadata={
                "content_type": "fee",
                "feature_type": "detail_content",
                "prompt_id": fee_prompt_id
            }
        )

        logger.info(f"세부내역 프롬프트 등록 완료: info={info_prompt_id}, fee={fee_prompt_id}")
        return {
            'info': info_prompt_id,
            'fee': fee_prompt_id
        }

    except Exception as e:
        logger.error(f"세부내역 프롬프트 등록 실패: {e}")
        return {}
