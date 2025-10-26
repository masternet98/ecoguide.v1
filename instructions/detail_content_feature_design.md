# District Link 배출정보/수수료 세부내역 관리 기능 설계서

**작성일**: 2024-10-27
**목표**: 지역별 배출정보와 수수료에 대한 세부 내용을 자동 추출 또는 수동으로 등록·관리하는 기능

---

## 📋 목차

1. [개요](#개요)
2. [기능 요구사항](#기능-요구사항)
3. [데이터 모델](#데이터-모델)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [구현 계획](#구현-계획)
6. [기존 기능 영향도 분석](#기존-기능-영향도-분석)

---

## 개요

### 문제점
- 현재 District Links 페이지는 **URL/PDF 링크만 등록** 가능
- 실제 배출정보/수수료는 **링크 클릭 후 직접 확인**해야 함
- 지역별 정보가 **구조화되지 않아** 앱 내에서 활용 어려움

### 해결 방안
- **세부내역(Detail Content)** 저장 기능 추가
- **자동 추출 모드**: URL/PDF → OpenAI → 정리된 정보
- **수동 등록 모드**: 관리자가 직접 입력
- 저장된 정보는 **배출 안내 기능에서 활용** 가능

---

## 기능 요구사항

### FR-1: 세부내역 자동 추출
- **입력**: 배출정보 URL 또는 PDF 파일
- **처리**: OpenAI Vision/GPT 모델로 분석
- **출력**: 구조화된 JSON 형식의 세부내역

### FR-2: 세부내역 수동 등록
- **입력**: UI를 통한 직접 입력
- **저장**: 구조화된 형식으로 저장
- **수정**: 이미 저장된 내용 편집 가능

### FR-3: 세부내역 조회 및 관리
- **조회**: 저장된 세부내역 표시
- **편집**: 내용 수정 가능
- **삭제**: 불필요한 정보 삭제

### FR-4: 기존 배출 안내 기능 연동
- **활용**: 저장된 세부내역을 배출 안내 프롬프트에 포함
- **효과**: 더 정확한 배출 가이드 제공

---

## 데이터 모델

### 확장된 waste_links_manual.json 구조

```json
{
  "metadata": {
    "version": "1.2",
    "created_at": "2024-10-27T00:00:00",
    "last_updated": "2024-10-27T10:30:00",
    "monitoring_enabled": true
  },
  "links": {
    "서울특별시_강남구": {
      "info_url": "https://example.com/info",
      "system_url": "https://example.com/system",
      "fee_url": "https://example.com/fee",
      "appliance_url": "https://example.com/appliance",
      "description": "기존 설명 필드",

      "info_detail": {
        "source": "manual|ai_generated",
        "extracted_at": "2024-10-27T10:30:00",
        "배출_가능_물품": ["소파", "침대", "책장", "옷장"],
        "배출_불가능_물품": ["에어컨", "세탁기", "냉장고"],
        "배출_방법": "인터넷 신청 또는 전화 신청",
        "수거_일정": "매주 월요일, 수요일, 금요일",
        "신청_방법": {
          "온라인": "강남구 홈페이지 > 배출신청",
          "전화": "02-1234-5678",
          "방문": "강남구청 3층 환경과"
        },
        "기본_수수료": "10,000원~50,000원 (크기별)",
        "연락처": "02-1234-5678",
        "운영_시간": "평일 09:00~18:00",
        "추가_정보": "야간/휴일 신청은 불가능하며, 사전 신청 필수입니다.",
        "신뢰도": 0.95,
        "주석": "OpenAI로 추출된 정보"
      },

      "fee_detail": {
        "source": "manual|ai_generated",
        "extracted_at": "2024-10-27T10:30:00",
        "배출_기준": "물품의 최대 길이 또는 가로+세로+높이의 합",
        "요금_표": [
          {
            "카테고리": "소파",
            "기준": "길이 200cm 초과 또는 합 300cm 초과",
            "요금": "50,000원",
            "설명": "3인 이상 소파"
          },
          {
            "카테고리": "침대",
            "기준": "퀸/킹사이즈",
            "요금": "30,000원~40,000원",
            "설명": "프레임만 또는 매트리스 포함"
          }
        ],
        "예약_방법": "인터넷(강남구 홈페이지) 또는 전화(02-1234-5678)",
        "결제_방법": "현장 결제(신용카드, 현금)",
        "할인": "가능 경우 기재",
        "신뢰도": 0.92,
        "주석": "2024년 기준 요금표"
      },

      "managed_at": "2024-10-27T10:30:00",
      "managed_by": "admin_name",

      "monitoring": {
        "enabled": true,
        "created_at": "2024-01-15T10:30:00",
        "last_checked": "2024-10-27T08:00:00",
        "check_frequency": "daily",
        "priority": "medium",
        "failure_count": 0,
        "last_failure": null
      }
    }
  }
}
```

---

## 시스템 아키텍처

### 1. 서비스 계층

#### `DetailContentService` (새로 생성)
**위치**: `src/domains/infrastructure/services/detail_content_service.py`

**책임**:
- URL 콘텐츠 수집 및 파싱
- PDF 파일에서 텍스트 추출
- OpenAI를 활용한 자동 정리/요약
- 세부내역 CRUD

**메서드**:
```python
class DetailContentService(BaseService):
    # 자동 추출
    def extract_info_from_url(url: str) -> Dict[str, Any]
    def extract_info_from_pdf(file_path: str) -> Dict[str, Any]

    # AI 기반 정리
    def generate_detail_content(
        content: str,
        content_type: str  # 'info' or 'fee'
    ) -> Dict[str, Any]

    # CRUD
    def save_detail_content(
        district_key: str,
        content_type: str,  # 'info' or 'fee'
        detail_data: Dict[str, Any]
    ) -> bool

    def get_detail_content(
        district_key: str,
        content_type: str
    ) -> Optional[Dict[str, Any]]

    def delete_detail_content(
        district_key: str,
        content_type: str
    ) -> bool
```

#### `link_collector_service.py` (기존 - 확장)
- 기존 CRUD 함수 유지
- 새로운 detail_content 관련 함수 추가 (세부내역만 다루는 전용 함수)
- **변경 최소화**: 기존 함수는 수정 없음

---

### 2. UI 계층

#### `DetailContentUI` (새로 생성)
**위치**: `src/domains/infrastructure/ui/detail_content_ui.py`

**책임**:
- 세부내역 등록/수정/조회 UI
- 자동 추출 vs 수동 등록 모드 전환
- 추출 결과 검토 및 수정

**구성**:
```python
def show_detail_content_editor(
    district_key: str,
    content_type: str,  # 'info' or 'fee'
    registered_links: Dict,
    config: Config
) -> bool
    # 탭: 자동 추출 / 수동 등록 / 조회
    # 반환: 저장 여부

def show_auto_extract_mode(
    district_key: str,
    content_type: str,
    config: Config
) -> bool
    # URL/PDF 입력 → 추출 → 검토 → 저장

def show_manual_input_mode(
    district_key: str,
    content_type: str,
    config: Config
) -> bool
    # 직접 입력 → 저장

def show_detail_content_viewer(
    district_key: str,
    content_type: str,
    config: Config
)
    # 저장된 정보 조회/수정
```

#### `link_collector_ui.py` (기존 - 확장)
- **기존 탭 유지**: "📝 링크 관리", "🚨 오류 현황", "📤 데이터 내보내기"
- **새 탭 추가**: "📖 세부내역 관리" (선택 사항)
- 기존 UI 함수는 그대로 유지

---

### 3. OpenAI 프롬프트

#### 배출정보 추출 프롬프트
**타입**: `detail_extraction_info`

```
당신은 대형폐기물 배출 정보 분석 전문가입니다.

다음 URL/PDF 콘텐츠에서 배출정보를 추출하고 구조화하세요:

---
[콘텐츠]
---

다음 JSON 형식으로 응답하세요:

{
  "배출_가능_물품": ["물품1", "물품2", ...],
  "배출_불가능_물품": ["물품1", "물품2", ...],
  "배출_방법": "설명",
  "수거_일정": "설명",
  "신청_방법": {
    "온라인": "...",
    "전화": "...",
    "방문": "..."
  },
  "기본_수수료": "설명",
  "연락처": "전화번호 또는 이메일",
  "운영_시간": "시간",
  "추가_정보": "기타 중요 정보"
}

주의:
1. 명확하지 않은 정보는 포함하지 마세요
2. 모든 필드가 필요한 것은 아닙니다 (있는 것만 포함)
3. 신뢰도를 0.0~1.0으로 평가하세요
```

#### 수수료 정보 추출 프롬프트
**타입**: `detail_extraction_fee`

```
당신은 대형폐기물 수수료 정보 분석 전문가입니다.

다음 URL/PDF 콘텐츠에서 수수료 정보를 추출하고 구조화하세요:

---
[콘텐츠]
---

다음 JSON 형식으로 응답하세요:

{
  "배출_기준": "물품 크기 기준 설명",
  "요금_표": [
    {
      "카테고리": "소파",
      "기준": "크기 또는 조건",
      "요금": "금액",
      "설명": "추가 설명"
    },
    ...
  ],
  "예약_방법": "설명",
  "결제_방법": "결제 수단",
  "할인": "할인 정보 (없으면 빈 문자열)",
  "추가_정보": "기타 정보"
}

주의:
1. 요금표는 반드시 배열 형식으로
2. 금액은 한글 표기 유지 (예: "10,000원~20,000원")
3. 명확한 정보만 포함
```

---

## 구현 계획

### 🔵 Phase 1: 서비스 계층 구현
**파일**: `src/domains/infrastructure/services/detail_content_service.py`

```python
from typing import Dict, Any, Optional
from src.domains.analysis.services.openai_service import OpenAIService
from src.app.core.config import Config
from src.app.core.logger import log_info, log_error
import requests
import json
from datetime import datetime
```

**핵심 메서드**:
1. `extract_info_from_url()` - BeautifulSoup로 HTML 파싱
2. `extract_info_from_pdf()` - pypdf 또는 pdfplumber로 텍스트 추출
3. `generate_detail_content()` - OpenAI 호출
4. `save_detail_content()` - waste_links_manual.json에 저장

### 🟡 Phase 2: UI 컴포넌트 구현
**파일**: `src/domains/infrastructure/ui/detail_content_ui.py`

**탭 구성**:
- 탭1: 자동 추출
  - URL/PDF 입력
  - 추출 버튼
  - 결과 검토
  - 저장 버튼

- 탭2: 수동 입력
  - 폼 입력 필드
  - 저장 버튼

- 탭3: 조회
  - 저장된 정보 표시
  - 수정/삭제 버튼

### 🟢 Phase 3: 통합
**수정 파일**: `src/domains/infrastructure/ui/link_collector_ui.py`

**변경 사항**:
- `link_collector_ui()` 함수 내 탭 추가
- 새 탭: "📖 세부내역 관리"
- 지역 선택 후 세부내역 관리 UI 호출

---

## 기존 기능 영향도 분석

### ✅ 영향 없음 (안전성 확보)

| 항목 | 현재 상태 | 변경 내역 | 영향도 |
|------|---------|---------|--------|
| `load_registered_links()` | 기존 | 없음 | ✅ 안전 |
| `save_link()` | 기존 | 없음 | ✅ 안전 |
| `delete_link()` | 기존 | 없음 | ✅ 안전 |
| `link_collector_ui()` | 기존 탭 | 새 탭만 추가 | ✅ 안전 |
| `show_sigungu_editor()` | 기존 | 없음 | ✅ 안전 |
| waste_links_manual.json | 기존 필드 | 새 필드 추가 | ✅ 역호환 (신규 필드만 추가) |

### ⚠️ 주의사항

1. **JSON 마이그레이션**
   - 기존 데이터는 `info_detail`, `fee_detail` 필드 없음
   - 처음 세부내역 추출 시 자동으로 생성

2. **버전 관리**
   - metadata.version을 "1.2"로 업그레이드
   - 읽기 시 구 버전도 호환 처리

3. **테스트 필수**
   - 기존 링크 데이터 로드 테스트
   - 새로운 세부내역 추가 후 기존 기능 동작 확인

---

## 구현 순서

1. **DetailContentService** 구현
   - URL 콘텐츠 수집 함수
   - PDF 텍스트 추출 함수
   - OpenAI 호출 함수
   - CRUD 함수

2. **OpenAI 프롬프트** 등록
   - Prompt Manager에 프롬프트 추가
   - 또는 설정 파일에 직접 정의

3. **DetailContentUI** 구현
   - 자동 추출 탭
   - 수동 입력 탭
   - 조회 탭

4. **link_collector_ui.py** 통합
   - 새 탭 추가
   - DetailContentUI 호출

5. **테스트**
   - 기존 기능 회귀 테스트
   - 새로운 기능 테스트
   - 통합 테스트

---

## 의존성 추가 필요 여부

```python
# 기존 requirements.txt에 있는지 확인
- requests           # ✅ 보통 설치됨
- beautifulsoup4     # ✅ 보통 설치됨
- pypdf             # ⚠️ 설치 필요 시 추가
# 또는
- pdfplumber        # ⚠️ 설치 필요 시 추가
```

---

## 다음 단계

1. DetailContentService 구현 시작
2. OpenAI 프롬프트 정의
3. DetailContentUI 컴포넌트 작성
4. 통합 및 테스트
