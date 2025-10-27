# 세부내역 마크다운 변수 주입 가이드

## 개요

세부내역 서비스는 웹페이지 콘텐츠를 AI로 분석하여 **마크다운 형식**으로 저장합니다. 이 마크다운 콘텐츠는 향후 배출정보 안내 및 사용자 가이드 템플릿에 변수로 주입될 수 있습니다.

## 저장 구조

### 저장 경로
```
uploads/waste_links/detail_contents.json
```

### 데이터 구조

```json
{
  "metadata": {
    "version": "1.0",
    "created_at": "2025-10-27T16:08:29",
    "last_updated": "2025-10-27T16:08:29"
  },
  "contents": {
    "지역키": {
      "info_detail": {
        "content": "마크다운 형식의 배출정보 콘텐츠",
        "created_at": "2025-10-27T16:08:29",
        "source": "ai_analyzed"
      },
      "fee_detail": {
        "content": "마크다운 형식의 수수료 콘텐츠",
        "created_at": "2025-10-27T16:08:29",
        "source": "ai_analyzed"
      },
      "managed_at": "2025-10-27T16:08:29"
    }
  }
}
```

## 마크다운 콘텐츠 형식

### 배출정보 (info) 형식

```markdown
## 📦 배출 가능 물품
소파, 침대, 책장, 식탁 등

## ⛔ 배출 불가능 물품
유리, 액체물질, 위험물 등

## 🚚 배출 방법
배출 전 예약 필수. 대형폐기물 신청 시스템에서 배출 예약

## 📅 수거 일정
평일 09:00~18:00, 토요일 09:00~13:00 (일요일 휴무)

## 📞 신청 방법

### 온라인
배출정보 관리 시스템: https://example.com

### 전화
02-1234-5678 (평일 09:00~18:00)

### 방문
강남구청 대형폐기물과, 서울시 강남구 ...

## 💰 기본 수수료
물품별로 상이합니다. 요금표 참조

## 👥 연락처

- **대형폐기물 신청센터**: 02-1234-5678 (배출 예약, 문의)
- **온라인 신청 시스템**: https://example.com (배출 예약)
- **강남구청 대형폐기물과**: 서울시 강남구 ... (방문 신청, 상담)

## ⏰ 운영 시간
평일 09:00~18:00, 토요일 09:00~13:00

## 📌 추가 정보
대형폐기물은 반드시 예약 후 배출해야 합니다.
```

### 수수료 정보 (fee) 형식

```markdown
## 📐 배출 기준
물품의 크기와 종류에 따라 요금이 결정됩니다.

## 💵 요금 표

### 소파
- **크기**: 2인용 이상 → **요금**: 18,000원~27,000원
- **크기**: 1인용 → **요금**: 9,000원~13,500원

### 침대
- **크기**: 더블/퀸 → **요금**: 13,500원~18,000원
- **크기**: 싱글 → **요금**: 9,000원~13,500원

### 책장
- **크기**: 대형(1.5m 이상) → **요금**: 18,000원
- **크기**: 중형(1m~1.5m) → **요금**: 13,500원
- **크기**: 소형(1m 미만) → **요금**: 9,000원

## 📅 예약 방법
온라인 또는 전화로 예약. 배출 7일 전 신청 권장

## 💳 결제 방법
현장 카드/현금 결제 가능

## 🎁 할인
- 다량 배출 시 10% 할인
- 환경미화원 협회 회원 5% 할인

## 📌 추가 정보
변동될 수 있으니 공식 사이트 확인 권장
```

## 변수 주입 사용 예시

### 1. Python에서 변수 주입

```python
from src.domains.infrastructure.services.detail_content_service import DetailContentService
from src.app.core.config import load_config

# 세부내역 로드
config = load_config()
service = DetailContentService(config)

# 지역별 배출정보 로드
district_key = "서울특별시_강남구"
info_detail = service.get_detail_content(district_key, "info")
fee_detail = service.get_detail_content(district_key, "fee")

# 마크다운 콘텐츠 추출
info_content = info_detail.get("content", "")  if info_detail else ""
fee_content = fee_detail.get("content", "")  if fee_detail else ""

# 템플릿에 주입
guidance_template = f"""
# {district_key} 대형폐기물 배출 안내

{info_content}

## 요금 정보

{fee_content}

---
최종 업데이트: {info_detail.get('created_at', '')}
"""

print(guidance_template)
```

### 2. Streamlit에서 변수 주입

```python
import streamlit as st
from src.domains.infrastructure.services.detail_content_service import DetailContentService
from src.app.core.config import load_config

config = load_config()
service = DetailContentService(config)

district_key = st.selectbox("지역 선택", ["서울특별시_강남구", "인천광역시_서구"])

# 배출정보와 수수료 정보 로드
info_detail = service.get_detail_content(district_key, "info")
fee_detail = service.get_detail_content(district_key, "fee")

if info_detail and fee_detail:
    # 탭으로 나누어 표시
    tab1, tab2 = st.tabs(["배출정보", "수수료"])

    with tab1:
        st.markdown(info_detail.get("content", "정보 없음"))

    with tab2:
        st.markdown(fee_detail.get("content", "정보 없음"))
else:
    st.warning("세부정보를 찾을 수 없습니다.")
```

### 3. 템플릿 문자열 포맷팅

```python
# 프롬프트나 템플릿에서 변수로 사용
DISPOSAL_GUIDANCE_TEMPLATE = """
# {district_name} 대형폐기물 배출 안내

사용자님이 배출 예정인 물품에 대한 배출 정보입니다.

{disposal_info}

## 배출 요금

{fee_info}

---

추가 문의는 지역 청소과에 연락주세요.
"""

# 데이터 주입
guidance = DISPOSAL_GUIDANCE_TEMPLATE.format(
    district_name="강남구",
    disposal_info=info_content,
    fee_info=fee_content
)
```

## 주요 특징

### ✅ 마크다운 형식의 장점

1. **가독성**: 구조화된 마크다운은 사용자가 읽기 쉬움
2. **유연성**: Streamlit의 `st.markdown()`으로 바로 렌더링 가능
3. **확장성**: HTML로 변환하거나 PDF로 내보내기 용이
4. **일관성**: AI가 생성한 콘텐츠를 일정한 형식으로 저장

### 📝 메타데이터

각 항목에 저장되는 메타데이터:

- `content`: 마크다운 형식의 실제 콘텐츠
- `created_at`: 생성 일시 (ISO 8601 형식)
- `source`: 데이터 출처 (`ai_analyzed`, `manual`, `ai_generated` 등)

## 통합 워크플로우

```
┌─────────────────────┐
│ 웹페이지 콘텐츠     │ (사용자가 복사)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ DetailContentService│ (AI 분석)
│ generate_content()  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 마크다운 형식 변환  │ (JSON → Markdown)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 저장소 저장         │ (detail_contents.json)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 템플릿에 변수 주입  │ (향후 사용)
│ 사용자 가이드 생성  │
└─────────────────────┘
```

## 데이터 마이그레이션 (옛날 JSON 포맷)

기존 JSON 형식의 데이터는 마크다운으로 자동 변환되지 않습니다. 필요시 다음과 같이 수동으로 재분석할 수 있습니다:

```python
# 레거시 데이터 확인
service = DetailContentService(config)
old_detail = service.get_detail_content(district_key, "info")

# 래거시 형식인지 확인 ('content' 필드 없음)
if old_detail and 'content' not in old_detail:
    print("레거시 형식 데이터입니다. 재분석을 권장합니다.")
    # UI에서 '재분석' 버튼으로 재처리
```

## 향후 개선사항

1. **별도 MD 파일 저장**: 각 지역/타입별로 별도의 `.md` 파일로도 저장 가능
2. **버전 관리**: 변경 이력 추적 및 이전 버전 복원
3. **다국어 지원**: 지역별 언어로 템플릿 생성
4. **캐싱**: 자주 접근하는 지역 정보의 성능 최적화

## 참고 자료

- **서비스**: `src/domains/infrastructure/services/detail_content_service.py`
- **UI**: `src/domains/infrastructure/ui/detail_content_ui.py`
- **프롬프트 템플릿**: `src/domains/infrastructure/services/detail_content_prompts.py`
- **초기화**: `src/domains/infrastructure/services/detail_content_initialization.py`
