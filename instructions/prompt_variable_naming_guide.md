# 프롬프트 변수 명명 규칙 가이드

## 🎯 핵심 원칙

프롬프트는 **Admin에 저장**되고, **화면에서 변수를 주입**합니다.
따라서 변수명은 **일관되고 명확**해야 합니다.

```
Admin (프롬프트 템플릿)         화면 (변수 제공)
물품명: {item_name}       ←→    variables = {'item_name': '소파'}
분류: {category}          ←→    variables = {'category': '가구'}
크기: {size}              ←→    variables = {'size': '200x100cm'}
```

---

## 📋 변수 명명 규칙

### 1️⃣ 기본 규칙

| 규칙 | 설명 | 예시 |
|------|------|------|
| **snake_case** | 소문자 + 언더스코어 | ✅ `item_name` / ❌ `ItemName`, `itemName` |
| **영문만** | 영어만 사용, 한글 금지 | ✅ `disposal_method` / ❌ `배출방법` |
| **명사형** | 동사 금지, 명사만 | ✅ `location` / ❌ `get_location` |
| **짧고 명확** | 3-15자 범위 권장 | ✅ `confidence` / ❌ `confidence_score_percentage` |
| **맥락 포함** | 단어 조합으로 의미 전달 | ✅ `location_context` / ❌ `ctx` |

### 2️⃣ 변수 카테고리별 명명 규칙

#### 🏘️ 위치정보 관련

```python
# 기본 위치
location              # "서울특별시 강남구" (전체 주소)
location_full         # "서울특별시 강남구 역삼동" (동 포함)
sido                  # "서울특별시" (시/도만)
sigungu               # "강남구" (시군구만)
dong                  # "역삼동" (동만)

# RAG 기반 컨텍스트
location_context      # RAG에서 가져온 지역 배출 규정 컨텍스트
location_rules        # 지역별 배출 규칙 정보
location_contact      # 지역 구청/센터 연락처
```

#### 🗑️ 폐기물 관련

```python
# 기본 정보
item_name             # "소파", "냉장고" (물품명)
category              # "가구", "가전", "전자제품" (대분류)
subcategory           # "패브릭소파", "냉동고" (소분류)
material              # "목재", "플라스틱", "금속" (재질)
condition             # "양호", "손상", "부분손상" (상태)

# 크기 정보
size                  # "200cm x 100cm x 50cm" (전체)
width                 # "200" (가로, 숫자만)
height                # "100" (세로, 숫자만)
depth                 # "50" (높이, 숫자만)
dimensions            # "200cm x 100cm x 50cm" (포맷된 문자열)
weight_kg             # "50.5" (무게, 단위 포함)

# RAG 기반 컨텍스트
waste_context         # RAG에서 가져온 폐기물 배출 방법 컨텍스트
waste_category_info   # 폐기물 카테고리별 특화 정보
waste_caution         # 폐기물 배출 주의사항

# 배출 정보
disposal_method       # "사전신고 후 지정 날짜 배출"
disposal_fee          # "10,000원", "소형 5,000원"
disposal_schedule     # "매주 월요일, 수요일"
disposal_contact      # "강남구청 청소과 02-XXXX-XXXX"
```

#### 📸 이미지/분석 관련

```python
# 분석 결과
object_name           # AI가 감지한 물품명
confidence            # 신뢰도 (0.0-1.0 또는 "85%")
primary_category      # AI 1차 분류
secondary_category    # AI 2차 분류
analysis_result       # 분석 전체 결과 요약
detected_features     # 감지된 특징 리스트

# 이미지 정보
image_id              # 이미지 UUID
image_url             # 이미지 경로/URL
image_size            # "1920x1080" (해상도)

# 사용자 확인/수정
user_confirmed_item   # 사용자가 확인한 물품명
user_confirmed_category # 사용자가 확인한 분류
user_notes            # 사용자 추가 메모
```

#### 🎯 분석/처리 관련

```python
# 프롬프트 실행 환경
prompt_context        # 프롬프트 실행 전체 컨텍스트
additional_context    # 추가 배경 정보
rag_context          # RAG 검색 결과 전체
combined_context     # location_context + waste_context 조합

# 사용자 정보
user_id               # 사용자 ID
user_location         # 사용자 선택 위치
session_id            # 세션 ID

# 메타정보
timestamp             # "2025-10-26T10:30:00"
language              # "ko" (한국어)
request_id            # 요청 ID
```

---

## 📐 변수 작성 형식

### 형식 1: 단순 값

```
{변수명}

예:
  물품명: {item_name}
  분류: {category}
  신뢰도: {confidence}
```

### 형식 2: 포맷된 텍스트

```
텍스트 {변수명} 텍스트

예:
  크기: {width}cm x {height}cm x {depth}cm
  지역: {location_full}
  배출료: {disposal_fee}원
```

### 형식 3: 섹션 (컨텍스트)

```
【섹션 이름】
{variable_with_content}

예:
  【배출 규정】
  {location_context}

  【폐기물 정보】
  {waste_context}
```

### 형식 4: 조건부 변수 (선택적)

```
{variable_if_provided}가 있으면 표시, 없으면 기본값 제공

예:
  📝 참고: {additional_context}
  (만약 additional_context가 없으면: 추가 정보 없음)
```

---

## 🎨 프롬프트 작성 예제

### ❌ 나쁜 예

```
당신은 분류 전문가입니다.

사용자가 업로드한 이미지에서 감지된 물품 정보를 확인해주세요.

물품: {물품명}
카테고리: {카테고리}
크기: {가로} x {세로}
신뢰도: {점수}

설명해주세요.
```

**문제점:**
- ❌ 변수명이 한글 (`물품명`, `카테고리`)
- ❌ 변수명이 일관성 없음 (`물품` vs `물품명`)
- ❌ 변수명이 모호함 (`가로`, `세로` - `width`, `height`가 명확)
- ❌ 변수명이 축약됨 (`점수` - `confidence`가 명확)

### ✅ 좋은 예

```
당신은 대형폐기물 분류 전문가입니다.

사용자가 업로드한 이미지에서 감지된 물품 정보를 확인하세요.

【감지된 물품】
물품명: {item_name}
분류: {category}
크기: {width}cm x {height}cm x {depth}cm
신뢰도: {confidence}

【배출 정보】
위치: {location_full}

위 정보를 바탕으로:
1. 감지된 물품이 맞는지 확인
2. 필요시 수정 제안
3. 배출 방법 간단히 설명

친근한 톤으로 작성하세요.
```

**개선점:**
- ✅ 변수명 모두 영문 snake_case
- ✅ 명확하고 일관성 있음
- ✅ 섹션으로 구조화
- ✅ 변수 의도가 명확함

---

## 🔗 화면 ↔ 프롬프트 매핑 가이드

### 분석 결과 확인 화면 예

#### 프롬프트 (Admin에 저장)

```
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
```

#### 화면 코드 (ConfirmationUI)

```python
def render(self):
    # 화면에서 데이터 수집
    confirmed_item = st.text_input("물품명", value=self.analysis_result['object_name'])
    confirmed_category = st.selectbox("분류", categories)
    width = st.number_input("가로(cm)", value=self.analysis_result['width_cm'])
    height = st.number_input("세로(cm)", value=self.analysis_result['height_cm'])

    if st.button("AI 피드백 받기"):
        # 프롬프트에 맞게 변수 준비
        variables = {
            'item_name': confirmed_item,           # ✅ 프롬프트 {item_name}과 매칭
            'category': confirmed_category,         # ✅ 프롬프트 {category}과 매칭
            'dimensions': f"{width}cm x {height}cm",  # ✅ 프롬프트 {dimensions}과 매칭
            'confidence': f"{self.analysis_result['confidence']:.0%}",  # ✅ 프롬프트 {confidence}과 매칭
            'additional_context': '폐기물 분류 정보'  # ✅ 프롬프트 {additional_context}과 매칭
        }

        # 서비스 호출
        service = app_context.get_service('confirmation_prompt_service')
        result = service.render_and_execute(variables)
```

**확인사항:**
- ✅ 화면의 변수명 = 프롬프트의 {변수명}
- ✅ 데이터 타입 일치 (문자열, 숫자 등)
- ✅ 형식 일치 (날짜, 통화 등)

---

## 📊 변수명 체크리스트

### 프롬프트 작성 시

```
□ 모든 변수가 {snake_case} 형식인가?
□ 변수명이 영문만 사용하는가?
□ 변수명이 명확하고 자체 설명적인가? (주석 필요 없음)
□ 같은 개념의 변수명이 일관성 있는가? (width/가로 혼용 금지)
□ 변수 용도가 명확히 섹션으로 구분되어 있는가?
□ 필수 변수와 선택적 변수가 구분되는가?
```

### 화면 코드 작성 시

```
□ 변수명이 프롬프트의 변수명과 정확히 매칭되는가?
□ 데이터 타입이 올바른가? (문자열, 숫자, 리스트 등)
□ 형식이 올바른가? (날짜, 통화, 백분율 등)
□ 모든 필수 변수가 포함되는가?
□ 변수 딕셔너리 키가 프롬프트의 변수명과 같은가?
```

---

## 🎯 카테고리별 기본 변수 세트

### 분석 결과 확인 (Confirmation)

```python
{
    'item_name': str,           # 물품명
    'category': str,             # 분류
    'subcategory': str,          # 소분류 (선택)
    'material': str,             # 재질 (선택)
    'dimensions': str,           # 크기
    'confidence': str,           # 신뢰도
    'additional_context': str    # RAG 컨텍스트 (선택)
}
```

### 배출방법안내 (DisposalGuidance)

```python
{
    'location': str,             # 위치
    'location_full': str,        # 위치 (동 포함)
    'item_name': str,            # 물품명
    'category': str,             # 분류
    'size': str,                 # 크기
    'location_context': str,     # RAG: 지역 배출 규정
    'waste_context': str         # RAG: 폐기물 배출 방법
}
```

### 커스텀 프롬프트

**프롬프트 작성 시:**
1. 필요한 변수들을 먼저 정의
2. 각 변수를 {snake_case}로 작성
3. Admin 프롬프트에 문서화

**변수 문서화 (프롬프트 설명 필드):**
```
프롬프트: 물품 배출 비용 추정
필수 변수: item_name, category, size
선택 변수: material, condition, location

변수 설명:
- item_name: 물품명 (예: "소파", "냉장고")
- category: 폐기물 분류 (예: "가구", "가전")
- size: 크기 정보 (예: "200cm x 100cm")
- material: 재질 (선택, 예: "목재", "금속")
- condition: 상태 (선택, 예: "양호", "손상")
- location: 위치 (선택, 예: "서울 강남구")
```

---

## 🚨 주의사항

### 1️⃣ 변수명 변경 시 주의

```
❌ 위험: 저장된 프롬프트에서 변수명 변경
  {item_name} → {item}  (화면 코드와 불일치)

✅ 안전: 새 프롬프트 작성 또는 모든 위치 동시 수정
  1. 프롬프트 변수명 변경
  2. 관련 Service의 validate_variables() 수정
  3. 화면 코드의 딕셔너리 키 수정
  4. 테스트 후 배포
```

### 2️⃣ 변수 타입 일관성

```
❌ 불일치:
  프롬프트: {confidence}  # "0.85" 또는 "85%"?
  화면: f"{confidence:.0%}"  # "85%"로 전달

✅ 일치:
  프롬프트: 신뢰도: {confidence}%  (백분율로 표시)
  화면: variables['confidence'] = f"{confidence:.0f}"  # "85"로 전달
```

### 3️⃣ 변수명 축약 금지

```
❌ 축약 (헷갈림):
  {loc}, {cat}, {sz}, {conf}, {ctx}

✅ 명확:
  {location}, {category}, {size}, {confidence}, {context}
```

---

## 📝 변수명 명명 체크 템플릿

프롬프트 작성 시 이 체크리스트를 사용하세요:

```markdown
### 프롬프트 변수 체크리스트

프롬프트명: ________________
카테고리: ________________

**필수 변수:**
- [ ] {변수명1} - 설명
- [ ] {변수명2} - 설명

**선택 변수:**
- [ ] {변수명3} - 설명 (선택)

**변수명 검토:**
- [ ] 모두 snake_case
- [ ] 모두 영문
- [ ] 명확한 의미
- [ ] 일관성 확인됨
- [ ] 화면 코드와 매칭 확인

**변수 형식:**
- [ ] 문자열 길이 제한 명시
- [ ] 날짜 형식 명시 (예: YYYY-MM-DD)
- [ ] 숫자 범위 명시 (예: 0.0-1.0)
- [ ] 단위 표시 (예: cm, 원, %)
```

---

## ✅ 최종 정리

| 항목 | 규칙 | 예시 |
|------|------|------|
| **형식** | snake_case | ✅ `item_name` |
| **언어** | 영문만 | ✅ `category` |
| **길이** | 3-15자 | ✅ `disposal_fee` |
| **의미** | 자체 설명적 | ✅ `location_context` |
| **일관성** | 같은 개념 같은 이름 | ✅ `width`, `height`, `depth` |
| **문서화** | 프롬프트 설명에 명시 | ✅ 필수/선택 변수 명시 |

이 가이드를 따르면 **프롬프트와 화면 코드 간의 혼동이 없어지고**,
**관리자도 쉽게 프롬프트를 편집**할 수 있습니다!
