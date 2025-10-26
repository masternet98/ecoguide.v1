# 프롬프트 카테고리 및 기능 매핑 가이드

## 🎯 프롬프트 카테고리 정의

현재 시스템에는 기본 카테고리가 있지만, 새 설계에 맞게 업데이트되어야 합니다.

### 📋 현재 카테고리 (prompt_types.py)

```python
class PromptCategory(Enum):
    VISION_ANALYSIS = "vision_analysis"          # 이미지 분석용
    OBJECT_DETECTION = "object_detection"        # 객체 탐지용
    SIZE_ESTIMATION = "size_estimation"          # 크기 추정용
    WASTE_CLASSIFICATION = "waste_classification" # 폐기물 분류용
    GENERAL_ANALYSIS = "general_analysis"        # 일반 분석용
    CUSTOM = "custom"                            # 사용자 정의
```

### ✅ 추천하는 업데이트 카테고리

```python
class PromptCategory(Enum):
    # 분석 단계
    ANALYSIS = "analysis"                        # 이미지 분석 결과 설명
    CONFIRMATION = "confirmation"                # 분석 결과 확인

    # 배출 안내
    DISPOSAL = "disposal"                        # 배출방법 안내
    DISPOSAL_GUIDANCE = "disposal_guidance"      # 상세 배출 안내

    # 지역별 정보
    LOCATION_INFO = "location_info"             # 지역 정보 안내

    # 분류 및 처리
    CLASSIFICATION = "classification"            # 폐기물 분류 처리
    WASTE_HANDLING = "waste_handling"           # 폐기물 처리 방법

    # 기타
    CUSTOM = "custom"                           # 사용자 정의
```

---

## 🔌 기능(Feature) 정의 및 매핑

### 📊 주요 기능 정의

| 기능 ID | 기능명 | 설명 | 권장 카테고리 | 필수 변수 |
|---------|--------|------|--------------|----------|
| `confirmation_analysis` | 분석 결과 확인 | 이미지 분석 후 결과 확인 | CONFIRMATION | item_name, category, dimensions |
| `disposal_guidance_main` | 배출방법 안내 | 위치 기반 배출방법 안내 | DISPOSAL | location, item_name, category |
| `quick_analysis` | 빠른 분석 | 간단한 물품 분석 | ANALYSIS | item_name |

### 🔗 기능-프롬프트 매핑 구조

```
기능 (Feature)
  ├─ 기능ID: "confirmation_analysis"
  ├─ 기본 프롬프트: prompt_id_1 (우선순위 0)
  ├─ 대체 프롬프트: prompt_id_2 (우선순위 1)
  └─ 조건부 프롬프트: prompt_id_3 (우선순위 2, 조건: {...})

기능 (Feature)
  ├─ 기능ID: "disposal_guidance_main"
  ├─ 기본 프롬프트: prompt_id_4 (우선순위 0)
  └─ ...
```

---

## 💻 Admin UI에서 설정하기

### Step 1: 프롬프트 생성

1. Admin 페이지 → "프롬프트 관리" → "프롬프트 생성" 탭
2. 다음 정보 입력:

```
프롬프트명: "분석 결과 확인"
설명: "이미지 분석 결과를 사용자에게 설명하고 확인 받는 프롬프트"
카테고리: "CONFIRMATION" ← 드롭다운에서 선택
상태: "ACTIVE"
태그: ["analysis", "confirmation", "user-facing"]

프롬프트 템플릿:
---
당신은 대형폐기물 분류 전문가입니다.

【감지된 물품】
물품명: {item_name}
분류: {category}
크기: {dimensions}
신뢰도: {confidence}

【추가 정보】
{additional_context}

【요청사항】
1. 감지된 물품이 맞는지 간단히 설명
2. 수정이 필요하면 제안
3. 친근한 톤으로
---
```

### Step 2: 기능 매핑

1. Admin 페이지 → "프롬프트 관리" → "기능 매핑" 탭
2. 매핑 정보 입력:

```
기능: "confirmation_analysis" ← 드롭다운 (또는 텍스트 입력)
프롬프트: "위에서 생성한 프롬프트" ← 드롭다운
이 프롬프트를 기본으로 설정: ✓ 체크
우선순위: 0 (낮은 숫자가 높은 우선순위)

[추가 조건] (선택)
조건명: temperature
값: 0.3
```

### Step 3: 검증 및 테스트

1. "프롬프트 목록" 탭에서 프롬프트 조회
2. "미리보기" 버튼으로 렌더링 테스트:

```
샘플 변수:
{
  "item_name": "소파",
  "category": "가구",
  "dimensions": "200cm x 100cm x 50cm",
  "confidence": "85%",
  "additional_context": "패브릭 재질, 부분 손상"
}

[미리보기] 버튼 클릭
```

---

## 🎯 프롬프트 수명 관리

### 버전 관리 워크플로우

```
1️⃣ 프롬프트 생성 (v1.0)
   ├─ 상태: DRAFT
   └─ 설명: 초안

2️⃣ 테스트 완료
   ├─ 상태: ACTIVE
   └─ 설명: 프로덕션 배포

3️⃣ 개선점 발견 (새 버전)
   ├─ 기존: ACTIVE → DEPRECATED
   └─ 신규: ACTIVE (우선순위 높음)

4️⃣ 사용 중단
   ├─ 상태: INACTIVE
   └─ 설명: 더 이상 사용 안 함
```

### 상태 의미

| 상태 | 사용 가능 | 설명 |
|------|---------|------|
| **ACTIVE** | ✅ 가능 | 실제 서비스에서 사용 중 |
| **DRAFT** | ❌ 불가 | 개발 중, 테스트 전 |
| **DEPRECATED** | ⚠️ 주의 | 더 나은 버전 있음, 곧 제거 예정 |
| **INACTIVE** | ❌ 불가 | 더 이상 사용하지 않음 |

---

## 📊 프롬프트 사용 통계

### 모니터링할 지표

Admin UI의 "통계" 탭에서 확인:

| 지표 | 의미 | 목표 |
|------|------|------|
| **사용 횟수** | 프롬프트가 얼마나 자주 사용되는가 | 많을수록 좋음 |
| **성공률** | LLM이 원하는 형식으로 응답한 비율 | > 90% |
| **평균 응답시간** | 프롬프트 실행 평균 시간 | < 3초 |
| **사용자 만족도** | 사용자 평점 평균 | > 4/5 |

### 성능 분석

```
프롬프트: "분석 결과 확인"
└─ 사용 횟수: 254회
└─ 성공률: 92%
└─ 평균 응답시간: 2.3초
└─ 사용자 평점: 4.2/5.0

→ 분석: 잘 작동 중이며, 응답 시간 개선 가능
```

---

## 🔄 프롬프트 업데이트 가이드

### 언제 업데이트하나?

1. **기본 내용 변경** (상단 섹션 수정)
   - 역할 변경
   - 지시사항 변경
   - 출력 형식 변경

2. **변수 추가/제거**
   - 새 변수 필요
   - 불필요한 변수 제거

3. **성능 개선**
   - 사용자 피드백 반영
   - 결과 품질 향상

### 업데이트 절차

```
1️⃣ 새 프롬프트 생성 (새 버전)
   버전: 2.0
   이름: "분석 결과 확인 (v2)"
   상태: DRAFT

2️⃣ 기본 프롬프트로 설정하지 않음
   우선순위: 10 (낮음)
   테스트 완료 후 업데이트

3️⃣ 기능 매핑 수정
   confirmation_analysis
   ├─ 우선순위 0: 새 프롬프트 (v2)
   └─ 우선순위 1: 기존 프롬프트 (v1, DEPRECATED)

4️⃣ 롤백 가능하도록 유지
   최소 3개 버전 유지
   이전 버전: DEPRECATED
```

---

## 🏠 실제 예제: 배출방법안내 프롬프트

### 프롬프트 정의

```
프롬프트명: "배출방법 상세 안내"
카테고리: DISPOSAL
상태: ACTIVE
버전: 1.0

템플릿:
---
당신은 대형폐기물 배출 안내 전문가입니다.

【지역 정보】
지역: {location_full}
규정: {location_context}

【폐기물 정보】
물품: {item_name}
분류: {category}
크기: {size}

【분류 정보】
{waste_context}

【요청사항】
1. 배출 방법: 신고부터 배출까지의 단계별 안내
2. 수수료: 예상 배출 비용 (없으면 "구청 문의")
3. 배출 일정: 가능한 배출 요일/시간
4. 주의사항: 분리배출, 안전주의사항
5. 문의처: 관할 구청 정보

마크다운 형식으로 명확하게 작성하세요.
---
```

### 기능 매핑

```
기능: disposal_guidance_main
매핑:
  ├─ 우선순위 0 (기본)
  │  └─ 프롬프트: "배출방법 상세 안내"
  │
  ├─ 우선순위 1 (대체)
  │  └─ 프롬프트: "배출방법 간단 안내"
  │
  └─ 우선순위 2 (조건: RAG 실패 시)
     └─ 프롬프트: "기본 배출 안내"
```

### 화면 코드에서 사용

```python
# Option A: 기능별 기본 프롬프트 자동 사용
prompt_id = self.prompt_service.get_default_prompt_for_feature(
    'disposal_guidance_main'
).id  # 우선순위 0 프롬프트

# Option B: 명시적으로 프롬프트 선택
result = service.render_and_execute(
    variables=variables,
    use_rag=True,
    stored_prompt_id=prompt_id
)
```

---

## ✅ 프롬프트 생성 체크리스트

```markdown
### 새 프롬프트 생성 시 확인사항

□ **기본 정보**
  □ 프롬프트명이 명확한가? (예: "배출방법 상세 안내")
  □ 설명이 충분한가? (목적, 사용 화면 명시)
  □ 적절한 카테고리를 선택했는가?
  □ 태그를 5개 이상 추가했는가?

□ **템플릿 작성**
  □ 역할이 명확하게 정의되어 있는가?
  □ 모든 변수가 {snake_case}로 정의되었는가?
  □ 변수 개수가 합리적인가? (3-10개 권장)
  □ 출력 형식이 명확한가? (마크다운, JSON 등)
  □ 섹션으로 구조화되어 있는가?

□ **변수 관리**
  □ 필수 변수와 선택 변수가 구분되는가?
  □ 각 변수의 형식이 명시되어 있는가?
  □ 변수가 화면 코드와 매칭되는가?

□ **테스트**
  □ Admin UI의 미리보기로 테스트했는가?
  □ 모든 필수 변수가 제공되었는가?
  □ 렌더링 결과가 예상과 같은가?
  □ 한글 표시가 정상인가?

□ **배포 준비**
  □ 상태를 ACTIVE로 설정했는가?
  □ 기능에 매핑했는가?
  □ 기본 프롬프트로 설정할 것인가?
  □ 이전 버전을 DEPRECATED로 설정했는가?
```

---

## 🎯 권장 프롬프트 목록

현재 시스템에서 필요한 필수 프롬프트:

### Phase 1: 분석

| 이름 | 카테고리 | 목적 | 우선순위 |
|------|---------|------|---------|
| 분석 결과 확인 | CONFIRMATION | 이미지 분석 결과 설명 | P0 |
| 빠른 분류 | CLASSIFICATION | 간단한 물품 분류 | P1 |

### Phase 2: 배출 안내

| 이름 | 카테고리 | 목적 | 우선순위 |
|------|---------|------|---------|
| 배출방법 상세 안내 | DISPOSAL | 위치 기반 배출 방법 | P0 |
| 배출방법 간단 안내 | DISPOSAL | 간단한 배출 정보 | P1 |
| 기본 배출 안내 | DISPOSAL | 폴백용 기본 안내 | P2 |

### Phase 3: 고급 기능

| 이름 | 카테고리 | 목적 | 우선순위 |
|------|---------|------|---------|
| 요금 계산 | WASTE_HANDLING | 배출 요금 추정 | P1 |
| 맞춤형 분류 | CLASSIFICATION | A/B 테스트용 | P2 |

---

## 📝 프롬프트 문서화 템플릿

Admin UI에서 각 프롬프트의 "설명" 필드에 다음과 같이 작성:

```
목적:
  이미지 분석 결과를 사용자에게 설명하고 사용자의 피드백을 유도합니다.

사용 화면:
  - ConfirmationUI (분석 결과 확인 페이지)

필수 변수:
  - item_name: 물품명 (예: "소파")
  - category: 분류 (예: "가구")
  - dimensions: 크기 (예: "200cm x 100cm x 50cm")
  - confidence: 신뢰도 (예: "85%")

선택 변수:
  - additional_context: 추가 컨텍스트 (폐기물 분류 정보)

출력 형식:
  마크다운 형식의 자연스러운 문장

버전 이력:
  v1.0 (2025-10-26): 초기 생성
```

---

이 가이드를 따르면 **Admin이 중심이 되어 프롬프트를 관리**할 수 있고,
**개발자는 단순히 변수를 준비하는 역할**만 하면 됩니다!
