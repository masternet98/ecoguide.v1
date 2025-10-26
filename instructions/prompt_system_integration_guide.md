# 프롬프트 시스템 통합 가이드

## 🎯 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│  Admin UI (pages/04_prompt_admin.py)                        │
│  - 프롬프트 생성/수정/삭제                                  │
│  - 변수 명명 규칙 따라 작성                                │
│  - 카테고리/태그 설정                                       │
│  - 기능 매핑 (Feature → Prompt)                            │
│  - 사용 통계 모니터링                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓ (저장)
┌─────────────────────────────────────────────────────────────┐
│  PromptService & PromptManager                              │
│  uploads/prompts/                                            │
│  ├─ templates/*.json     (프롬프트 템플릿)                  │
│  ├─ mappings/*.json      (기능 매핑)                        │
│  └─ stats/*.json         (사용 통계)                        │
└─────────────────────────────────────────────────────────────┘
                        ↓ (로드)
┌─────────────────────────────────────────────────────────────┐
│  ScreenIntegratedPromptService 🆕                           │
│  - _load_stored_prompt(prompt_id)                           │
│  - render_and_execute(variables, stored_prompt_id)          │
│  - _update_prompt_stats()                                   │
│  - RAG 보강 (선택적)                                        │
└─────────────────────────────────────────────────────────────┘
                        ↓ (실행)
┌─────────────────────────────────────────────────────────────┐
│  LangChain → OpenAI API                                     │
│  - 프롬프트 렌더링                                          │
│  - LLM 호출                                                 │
│  - 응답 생성                                                │
└─────────────────────────────────────────────────────────────┘
                        ↓ (표시)
┌─────────────────────────────────────────────────────────────┐
│  화면 (UI)                                                  │
│  - ConfirmationUI                                           │
│  - DisposalGuidanceUI                                       │
│  - 기타 화면들                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 데이터 흐름 요약

### 1️⃣ Admin이 프롬프트 작성 (UI)

```
Admin UI 프롬프트 생성 폼
  ↓
프롬프트명: "분석 결과 확인"
카테고리: CONFIRMATION
템플릿:
  당신은 분류 전문가입니다.

  물품: {item_name}
  분류: {category}
  크기: {dimensions}

  확인해주세요.

변수 설정 (자동 감지):
  - {item_name}
  - {category}
  - {dimensions}
  ↓
저장 (PromptManager)
  ↓
uploads/prompts/templates/{uuid}.json
```

### 2️⃣ 기능과 매핑 (Admin)

```
Admin UI 기능 매핑 탭
  ↓
기능: confirmation_analysis
프롬프트: "분석 결과 확인"
우선순위: 0 (기본)
상태: ACTIVE
  ↓
저장 (PromptManager)
  ↓
uploads/prompts/mappings/feature_mappings.json
```

### 3️⃣ 화면에서 사용 (개발자)

```python
# 화면 코드 (ConfirmationUI)

# 1단계: 변수 수집
variables = {
    'item_name': confirmed_item,
    'category': confirmed_category,
    'dimensions': f"{width}cm x {height}cm"
}

# 2단계: 저장된 프롬프트 로드
# 방법 A: 기능별 기본 프롬프트
prompt_id = app_context.get_service('prompt_service')\
    .get_default_prompt_for_feature('confirmation_analysis').id

# 방법 B: 직접 지정
prompt_id = 'abc123'

# 3단계: 서비스 호출
service = app_context.get_service('confirmation_prompt_service')
result = service.render_and_execute(
    screen_variables=variables,
    use_rag=True,
    stored_prompt_id=prompt_id
)

# 4단계: 결과 표시
if result['success']:
    st.write(result['response'])
```

### 4️⃣ 서비스 실행 (백엔드)

```python
# ScreenIntegratedPromptService.render_and_execute()

1. validate_variables(variables)
   ↓
2. enrich_with_rag(variables)  # RAG 검색 (선택적)
   ↓
3. _load_stored_prompt(prompt_id)
   ↓ (uploads/prompts/templates/{prompt_id}.json 로드)
   ↓
4. _render_prompt(template, variables)
   ↓ (변수 치환: {item_name} → "소파")
   ↓
5. _execute_with_langchain(rendered_prompt)
   ↓ (OpenAI API 호출)
   ↓
6. _update_prompt_stats(prompt_id)
   ↓ (사용 통계 저장)
   ↓
7. 결과 반환
```

---

## 📋 변수 명명 규칙 요약

### 핵심 규칙

```
1️⃣ snake_case: {item_name}, {location_context}
2️⃣ 영문만: {category} (❌ {카테고리})
3️⃣ 명사형: {confidence} (❌ {get_confidence})
4️⃣ 자체설명: {location_context} (❌ {ctx})
5️⃣ 3-15자: {disposal_fee} (✅) {df} (❌)
```

### 카테고리별 변수명

| 카테고리 | 변수명 예시 |
|---------|-----------|
| 위치정보 | `location`, `location_full`, `location_context` |
| 폐기물 | `item_name`, `category`, `size`, `waste_context` |
| 분석 | `confidence`, `object_name`, `analysis_result` |
| 배출 | `disposal_method`, `disposal_fee`, `disposal_schedule` |

### 프롬프트 작성 예

```
❌ 나쁜 예:
  물품: {물품명}
  카테고리: {카테고리}

✅ 좋은 예:
  물품: {item_name}
  분류: {category}
  위치: {location_full}
  배출 정보: {disposal_method}
```

---

## 🏷️ 프롬프트 카테고리 목록

### 분석 관련

| 카테고리 | 설명 | 예시 |
|---------|------|------|
| `ANALYSIS` | 이미지 분석 결과 설명 | "이 소파는..." |
| `CONFIRMATION` | 분석 결과 확인 | "이 분류가 맞나요?" |
| `CLASSIFICATION` | 폐기물 분류 | "이것은 가구입니다" |

### 배출 관련

| 카테고리 | 설명 | 예시 |
|---------|------|------|
| `DISPOSAL` | 배출방법 안내 | "신고 후 배출하세요" |
| `LOCATION_INFO` | 지역 정보 | "강남구 규정은..." |
| `WASTE_HANDLING` | 폐기물 처리 | "분리배출 방법" |

---

## ✅ 체크리스트

### Admin이 프롬프트 작성할 때

```markdown
□ 프롬프트명이 명확한가?
□ 설명에 목적과 사용 화면을 명시했는가?
□ 카테고리를 올바르게 선택했는가?
□ 모든 변수가 {snake_case}인가?
□ 한글 변수명은 없는가? (영문만)
□ 변수의 형식/범위를 명시했는가?
□ 출력 형식이 명확한가?
□ Admin UI에서 미리보기 테스트를 했는가?
□ 기능과 매핑했는가? (또는 기본 프롬프트로 설정)
□ 태그를 5개 이상 추가했는가?
```

### 개발자가 화면 코드 작성할 때

```markdown
□ 화면에서 필요한 변수를 모두 수집했는가?
□ 변수명이 프롬프트의 변수명과 정확히 매칭되는가?
□ 데이터 타입이 맞는가? (문자열, 숫자 등)
□ 형식이 맞는가? (날짜, 통화 등)
□ 필수 변수는 모두 포함했는가?
□ RAG 보강이 필요한가? (use_rag=True/False)
□ stored_prompt_id를 올바르게 지정했는가?
□ 에러 처리를 했는가?
□ 결과의 metadata를 활용하는가?
```

---

## 🔧 실제 구현 예제

### 예제 1: 분석 결과 확인

**Admin이 작성한 프롬프트:**

```
프롬프트명: 분석 결과 확인
카테고리: CONFIRMATION
태그: analysis, confirmation, feedback

템플릿:
---
당신은 대형폐기물 분류 전문가입니다.

【감지된 물품】
물품명: {item_name}
분류: {category}
크기: {dimensions}
신뢰도: {confidence}

【폐기물 정보】
{waste_context}

사용자에게 다음을 제공하세요:
1. 감지 결과가 맞는지 확인
2. 수정 필요한 부분 제안
3. 친근한 톤 유지
---

필수 변수: item_name, category, dimensions, confidence
선택 변수: waste_context

기능 매핑: confirmation_analysis (우선순위 0)
```

**개발자가 작성한 화면 코드:**

```python
class ConfirmationUI:
    def render(self):
        # 분석 결과 표시...

        if st.button("AI 피드백"):
            # 변수 수집
            variables = {
                'item_name': st.session_state.object_name,
                'category': st.session_state.category,
                'dimensions': f"{width}cm x {height}cm x {depth}cm",
                'confidence': f"{confidence:.0%}",
                'waste_context': '폐기물 분류 정보'  # RAG에서 가져옴
            }

            # 프롬프트 실행
            service = self.app_context.get_service(
                'confirmation_prompt_service'
            )
            result = service.render_and_execute(
                screen_variables=variables,
                use_rag=True,
                stored_prompt_id=None  # 기본 프롬프트 사용
            )

            # 결과 표시
            if result['success']:
                st.success("✅ AI 피드백")
                st.write(result['response'])
                st.metric("신뢰도", f"{result['confidence']:.1%}")
```

### 예제 2: 배출방법 안내

**Admin이 작성한 프롬프트:**

```
프롬프트명: 배출방법 상세 안내
카테고리: DISPOSAL
태그: disposal, guidance, location-based

템플릿:
---
당신은 대형폐기물 배출 안내 전문가입니다.

【지역 정보】
지역: {location_full}

규정:
{location_context}

【폐기물 정보】
물품: {item_name}
분류: {category}
크기: {size}

【분류 정보】
{waste_context}

다음을 포함하여 안내하세요:
1. 배출 방법 (단계별)
2. 예상 수수료
3. 배출 일정
4. 주의사항
5. 문의처

마크다운으로 명확하게 작성하세요.
---

필수 변수: location_full, item_name, category, size
선택 변수: location_context, waste_context

기능 매핑: disposal_guidance_main (우선순위 0)
```

**개발자가 작성한 화면 코드:**

```python
def render_disposal_guidance():
    # 위치정보 입력...
    # 폐기물 정보 입력...

    if st.button("배출방법 안내"):
        # RAG 검색 (필수)
        rag_searcher = app_context.get_service('disposal_rag_searcher')
        rag_result = rag_searcher.search_disposal_guidance(
            location=location_data,
            waste_category=category
        )

        # 변수 준비
        variables = {
            'location_full': location_data['full_address'],
            'item_name': item_name,
            'category': category,
            'size': size,
            'location_context': rag_result['location_context'],
            'waste_context': rag_result['waste_context']
        }

        # 프롬프트 실행
        service = app_context.get_service(
            'disposal_guidance_prompt_service'
        )
        result = service.render_and_execute(
            screen_variables=variables,
            use_rag=False,  # RAG는 이미 변수에 포함
            stored_prompt_id=None
        )

        # 결과 표시
        if result['success']:
            st.markdown(result['response'])
        else:
            st.error(f"안내 생성 실패: {result['error']}")
```

---

## 🚀 구현 순서

### Phase 1: 기본 인프라 (1주)
1. ScreenIntegratedPromptService 구현
2. PromptService.get_default_prompt_for_feature() 완성
3. ServiceFactory 등록
4. 단위 테스트

### Phase 2: 분석 페이지 통합 (1주)
1. ConfirmationPromptService 구현
2. confirmation_ui.py 수정
3. Admin에 첫 프롬프트 작성 (분석 결과 확인)
4. 기능 매핑 설정
5. 통합 테스트

### Phase 3: 배출 페이지 통합 (1주)
1. DisposalGuidancePromptService 구현
2. 배출방법 안내 페이지 생성
3. Admin에 프롬프트 작성
4. 기능 매핑 설정
5. E2E 테스트

### Phase 4: 최적화 (지속)
1. 프롬프트 성능 모니터링
2. 사용자 피드백 반영
3. A/B 테스트
4. 버전 관리

---

## 📚 참고 문서

| 문서 | 용도 |
|------|------|
| `prompt_variable_naming_guide.md` | 변수명 명명 규칙 상세 |
| `prompt_category_guide.md` | 카테고리 및 기능 매핑 |
| `screen_integrated_prompt_design.md` | 아키텍처 상세 설계 |
| `screen_integrated_prompt_quick_guide.md` | 빠른 구현 가이드 |

---

## 🎯 핵심 정리

### Admin의 역할
✅ Admin UI에서 프롬프트 작성/관리
✅ 변수명 규칙 준수 (snake_case, 영문만)
✅ 기능과 매핑
✅ 사용 통계 모니터링

### 개발자의 역할
✅ 변수 수집 (화면에서)
✅ PromptService 호출
✅ 결과 표시
✅ 에러 처리

### 시스템의 역할
✅ 프롬프트 로드 및 변수 치환
✅ LangChain으로 LLM 실행
✅ 사용 통계 기록
✅ 응답 생성

**결과: Admin이 중심이 되어 프롬프트를 관리하고, 개발자는 UI만 신경 쓰면 됩니다!**
