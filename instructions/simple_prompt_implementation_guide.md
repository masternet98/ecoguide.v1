# Simple Prompt 패턴 구현 가이드

## 🎯 개요

**Simple Prompt 패턴**: Admin이 저장한 프롬프트에 화면에서 수집한 변수를 주입하여 LLM을 호출하는 간단한 방식

### 기존 복잡한 설계 → 새로운 Simple 설계

```
❌ 복잡: RAG 설계 → ScreenIntegratedPromptService
        → 각 화면별 별도 서비스 → 복잡한 오케스트레이션

✅ Simple: 프롬프트 로드 → 변수 치환 → LLM 호출
         (기존 서비스만 사용)
```

---

## 💻 핵심 패턴 (4단계)

### Step 1: 저장된 프롬프트 로드

```python
prompt_service = app_context.get_service('prompt_service')

# 방법 A: 기능별 기본 프롬프트 로드
prompt = prompt_service.get_default_prompt_for_feature('confirmation_analysis')

# 방법 B: 프롬프트 ID로 직접 로드
prompt = prompt_service.get_prompt('prompt_id_123')
```

### Step 2: 변수 준비

```python
variables = {
    'item_name': '소파',
    'category': '가구',
    'dimensions': '200cm x 100cm x 50cm',
    'confidence': '85%',
    'location_full': '서울시 강남구',
    'disposal_method': '신고 후 배출'
}
```

**변수명 규칙** (`prompt_variable_naming_guide.md` 참조):
- snake_case: `{item_name}`, `{location_context}`
- 영문만: `{category}` (❌ `{카테고리}`)
- 명사형: `{confidence}` (❌ `{get_confidence}`)
- 자체설명: `{location_context}` (❌ `{ctx}`)
- 3-15자: `{disposal_fee}` (✅) `{df}` (❌)

### Step 3: 프롬프트 렌더링 (변수 치환)

```python
# 템플릿: "물품명: {item_name}, 분류: {category}"
rendered_prompt = prompt_service.render_prompt(prompt.id, variables)

# 결과: "물품명: 소파, 분류: 가구"
```

### Step 4: LLM 호출

```python
openai_service = app_context.get_service('openai_service')

# ✨ 새로운 메서드: call_with_prompt()
result = openai_service.call_with_prompt(rendered_prompt)

# 결과: "당신이 선택하신 소파는 목재 재질로 만들어진 가구입니다..."
```

---

## 🔄 app_new.py 구현 사례

### 1️⃣ ConfirmationStep - AI 피드백 (line 481-535)

**사용자 흐름**:
```
분석 결과 표시
  ↓
💭 AI 의견 듣기 버튼 클릭
  ↓
변수 준비 (item_name, category, dimensions, confidence)
  ↓
프롬프트 로드 & 렌더링
  ↓
LLM 호출
  ↓
피드백 표시
```

**코드**:
```python
if st.button("💭 AI 의견 듣기", use_container_width=True, key="get_ai_feedback"):
    prompt_service = self.app_context.get_service('prompt_service')
    openai_service = self.app_context.get_service('openai_service')

    # Step 1: 저장된 프롬프트 로드
    confirmation_prompt = prompt_service.get_default_prompt_for_feature('confirmation_analysis')

    if confirmation_prompt:
        # Step 2: 변수 준비
        variables = {
            'item_name': normalized['object_name'],
            'category': normalized['primary_category'],
            'dimensions': f"{width}cm x {height}cm",
            'confidence': f"{normalized['confidence']:.0%}",
            'user_feedback': feedback_notes.strip() or '없음'
        }

        # Step 3: 렌더링
        rendered_prompt = prompt_service.render_prompt(
            confirmation_prompt.id,
            variables
        )

        # Step 4: LLM 호출
        feedback_result = openai_service.call_with_prompt(rendered_prompt)
        st.markdown(feedback_result)
```

### 2️⃣ CompleteStep - 배출 방법 안내 (line 654-734)

**특징**:
- ✅ RAG 선택적 (location_context 변수로 주입)
- ✅ RAG 실패해도 기본값으로 계속 진행
- ✅ 위치 정보 세션에서 가져옴

**코드**:
```python
# Step 1: 프롬프트 로드
disposal_prompt = prompt_service.get_default_prompt_for_feature('disposal_guidance_main')

# Step 2: 변수 준비 (RAG 선택적)
location_context = '일반 배출 규정'
if location_service and location_code:
    try:
        rag_service = self.app_context.get_service('rag_context_service')
        rag_result = rag_service.search_disposal_guidance(...)
        location_context = rag_result.get('location_context', location_context)
    except Exception as e:
        logger.warning(f"RAG 검색 실패: {e}")
        # RAG 실패해도 계속 진행

variables = {
    'location_full': location_full,
    'item_name': normalized['object_name'],
    'category': normalized['primary_category'],
    'dimensions': dimensions_str,
    'location_context': location_context,  # RAG 결과
    'waste_context': f"세분류: {normalized['secondary_category']}"
}

# Step 3 & 4: 렌더링 & 호출
rendered_prompt = prompt_service.render_prompt(disposal_prompt.id, variables)
disposal_result = openai_service.call_with_prompt(rendered_prompt)
```

---

## 🛠️ 새로운 메서드

### OpenAIService.call_with_prompt()

```python
def call_with_prompt(self, prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
    """
    텍스트 프롬프트를 OpenAI에 보내고 응답을 받습니다.

    Args:
        prompt: 렌더링된 프롬프트 텍스트
        model: 사용할 OpenAI 모델명 (기본값: gpt-4o-mini)

    Returns:
        str: LLM 응답 텍스트
    """
```

**사용 예**:
```python
openai_service = app_context.get_service('openai_service')
response = openai_service.call_with_prompt(
    "당신은 분류 전문가입니다. 이 소파를 분류해주세요.",
    model="gpt-4o-mini"  # 생략 시 기본값
)
```

---

## 📋 필수 설정 (Admin 작업)

각 기능별로 Admin UI에서 프롬프트를 생성하고 기능에 매핑해야 합니다.

### 1️⃣ 분석 결과 확인 프롬프트

**기능**: `confirmation_analysis`
**카테고리**: CONFIRMATION
**필수 변수**: `item_name`, `category`, `dimensions`, `confidence`
**선택 변수**: `user_feedback`

**템플릿 예**:
```
당신은 대형폐기물 분류 전문가입니다.

【감지된 물품】
물품명: {item_name}
분류: {category}
크기: {dimensions}
신뢰도: {confidence}

【사용자 피드백】
{user_feedback}

【요청】
1. 감지 결과가 맞는지 확인
2. 수정 필요한 부분 제안
3. 친근한 톤 유지
```

### 2️⃣ 배출 방법 안내 프롬프트

**기능**: `disposal_guidance_main`
**카테고리**: DISPOSAL
**필수 변수**: `location_full`, `item_name`, `category`
**선택 변수**: `location_context`, `waste_context`, `dimensions`

**템플릿 예**:
```
당신은 대형폐기물 배출 안내 전문가입니다.

【지역 정보】
지역: {location_full}
규정: {location_context}

【폐기물 정보】
물품: {item_name}
분류: {category}
크기: {dimensions}

【요청】
1. 배출 방법 (단계별)
2. 예상 수수료
3. 배출 일정
4. 주의사항
5. 문의처

마크다운으로 명확하게 작성하세요.
```

---

## ✅ 체크리스트

### Admin이 프롬프트 작성할 때

- [ ] 프롬프트명이 명확한가?
- [ ] 설명에 목적과 사용 화면을 명시했는가?
- [ ] 올바른 카테고리를 선택했는가?
- [ ] 모든 변수가 `{snake_case}`인가?
- [ ] 한글 변수명은 없는가? (영문만)
- [ ] 프롬프트를 기능에 매핑했는가?
  - `map_feature_to_prompt(feature_id, prompt_id, is_default=True)`

### 개발자가 화면 코드 작성할 때

- [ ] 필요한 변수를 모두 수집했는가?
- [ ] 변수명이 프롬프트의 변수명과 정확히 매칭되는가?
- [ ] 서비스를 올바르게 가져왔는가? (`app_context.get_service()`)
- [ ] 에러 처리를 했는가? (프롬프트 없음, 렌더링 실패, LLM 호출 실패)
- [ ] RAG는 필요한가? (선택적)
- [ ] RAG 실패 시 기본값을 설정했는가?

---

## 🎯 순차 프롬프트 호출 흐름

현재 `app_new.py`에서 구현된 순차 호출:

```
Step 1: ImageUploadStep
  └─ 이미지 업로드/캡처

Step 2: AnalysisStep
  └─ 프롬프트 1: 이미지 분석 (Vision API)
  └─ 결과: 물품명, 분류, 크기 등

Step 3: ConfirmationStep
  ├─ 사용자가 분류 선택/수정 (UI)
  ├─ [선택] 💭 AI 의견 듣기
  │  └─ 프롬프트 2: 결과 확인 (LLM)
  │  └─ 피드백: "이 분류가 맞습니다" 등
  └─ 사용자 피드백 입력

Step 4: CompleteStep
  ├─ 최종 결과 표시
  ├─ 데이터 저장
  ├─ [선택] 💡 배출 방법 확인
  │  ├─ RAG 검색 (지역별 배출 정보)
  │  └─ 프롬프트 3: 배출 안내 (LLM)
  │  └─ 결과: 배출 방법, 수수료, 일정 등
  └─ 초기화/재시작
```

---

## 🔗 참고 문서

- `prompt_variable_naming_guide.md` - 변수명 명명 규칙
- `prompt_category_guide.md` - 카테고리 및 기능 매핑
- `prompt_system_integration_guide.md` - 통합 아키텍처

---

## 📌 핵심 정리

### Simple Prompt 패턴의 장점

✅ **간단함**: 4단계만 따르면 됨 (로드 → 준비 → 렌더링 → 호출)
✅ **유연성**: Admin이 프롬프트를 자유롭게 수정 가능
✅ **확장성**: 새 프롬프트 추가 시 화면 코드 수정 불필요
✅ **유지보수성**: 순차 호출로 인한 복잡성 없음
✅ **선택적 RAG**: 필요시만 사용, 실패해도 계속 진행

### 기존 복잡한 설계와의 차이

| 항목 | 기존 복잡 | Simple 패턴 |
|------|---------|-----------|
| 서비스 구조 | ScreenIntegratedPrompt + 별도 서비스들 | 기존 PromptService + OpenAIService |
| RAG | 강제 | 선택적 |
| 화면별 구현 | 각 화면마다 별도 서비스 필요 | 동일한 패턴 사용 |
| 복잡도 | ⭐⭐⭐⭐⭐ | ⭐ |
| 학습곡선 | 가파름 | 완만함 |
| 프롬프트 관리 | 복잡함 | 간단함 |

---

**결론**: Simple Prompt 패턴으로 깔끔하고 확장 가능한 프롬프트 시스템을 구축할 수 있습니다! 🎉
