# 세부내역 콘텐츠 추출 개선 가이드

## 개요

자동 추출 기능이 본문 내용을 제대로 가져오지 못하는 문제를 해결하기 위해 **강화된 HTML 파싱 로직**과 **상세한 로깅/디버깅 기능**을 추가했습니다.

## 주요 개선 사항

### 1. 강화된 HTML 파싱 로직

**파일**: `src/domains/infrastructure/services/detail_content_service.py`

#### 변경 사항:
- **타임아웃 증가**: 10초 → 20초 (정부 사이트 로딩 시간 고려)
- **인코딩 명시**: UTF-8 인코딩 보장
- **User-Agent 개선**: 더 현대적인 Chrome 브라우저 헤더

#### 파싱 프로세스 (6단계):

**1단계: HTML 파싱**
```python
soup = BeautifulSoup(response.content, 'html.parser')
# 전체 HTML 문서를 파싱
```

**2단계: 방해 요소 제거**
```python
# script, style, nav, header, footer, iframe, noscript 제거
for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
    element.decompose()
```

**3단계: 메인 콘텐츠 찾기 (우선순위 순서)**
```
1. CSS 선택자로 찾기 (13개 패턴):
   - 'main', 'article', '[role="main"]'
   - '.content', '.main-content', '.main_content'
   - '.article-content', '.post-content'
   - '.body-content', '.page-content'
   - '#content', '#main', '#article'
   - '.container > *:has(p)', '.wrapper > *:has(p)'

2. 선택자로 못 찾으면 가장 큰 텍스트 블록 찾기:
   - 모든 div, section, article 검사
   - 텍스트가 가장 긴 요소 선택
   - 네비게이션/메뉴/광고 요소 자동 건너뛰기
```

**4단계: 추가 방해 요소 제거**
```python
# aside, script, style, nav, footer 제거
for element in main_content(['aside', 'script', 'style', 'nav', 'footer']):
    if element.parent == main_content:
        element.decompose()
```

**5단계: 텍스트 추출**
```python
text = main_content.get_text(separator='\n', strip=True)
# 줄 구분자를 '\n'으로 사용하여 구조 유지
```

**6단계: 텍스트 정제**
```
1. 중복 공백 제거: " +" → " "
2. 중복 줄바꿈 제거: 2개 이상 연속 빈 줄 제거
3. 짧은 라인 필터링: 3글자 미만 제거
4. 최대 길이 제한: 8000자 (초과 시 "... [내용 생략]" 추가)
```

### 2. 상세 로깅 및 디버깅

**로깅 포인트**:

```
1단계: HTML 파싱 완료
  → 총 바이트 수

2단계: 방해 요소 제거
  → 제거된 요소 수

3단계: 메인 콘텐츠 찾기
  → 사용된 CSS 선택자 또는 "못 찾음 → 가장 큰 블록으로 전환" 메시지

5단계: 텍스트 추출 완료
  → 원본 텍스트 길이

6단계: 공백 정제
  → 정제 후 길이

줄바꿈 정제
  → 줄 수 및 길이

라인 필터링
  → 필터링 후 줄 수 및 길이

콘텐츠 추출 경고 (50자 미만)
  → 최종 길이 및 경고 메시지
```

**로그 확인 방법**:

Streamlit 서버 로그에서 다음과 같은 정보 확인:
```
[INFO] URL 콘텐츠 추출 성공
└─ 1단계: HTML 파싱 완료 | 총 문자 수: 256,324 바이트
└─ 2단계: 방해 요소 제거 | 제거된 요소 수: 45
└─ 3단계: 메인 콘텐츠 찾음 | 선택자: .content
└─ 5단계: 텍스트 추출 완료 | 원본 텍스트 길이: 25,432 자
└─ 6단계: 공백 정제 | 정제 후 길이: 25,102 자
└─ 줄바꿈 정제 | 줄 수: 428, 길이: 25,102 자
└─ 라인 필터링 | 필터링 후 줄 수: 398, 길이: 24,856 자
```

### 3. UI 디버그 정보 표시

**파일**: `src/domains/infrastructure/ui/detail_content_ui.py`

추출 실패 시 "🔍 디버그 정보" 확장 패널에 메타데이터 표시:

```json
{
  "url": "https://example.com/page",
  "title": "페이지 제목",
  "content_length": 24856,
  "extracted_at": "2024-10-27T12:34:56.789123",
  "method": "beautifulsoup_enhanced"
}
```

## 문제 해결 가이드

### 콘텐츠가 여전히 비어있을 경우

1. **URL 확인**
   - 페이지가 정상적으로 로드되는지 브라우저에서 확인
   - 로그에서 "바이트 수" 확인 (0이면 페이지 로드 실패)

2. **파싱 진행 상황 확인**
   - 로그에서 어느 단계에서 콘텐츠가 사라지는지 확인
   - 예: "원본 텍스트 길이: 24,000" → "필터링 후: 50" = 필터링에서 문제

3. **페이지 구조 확인**
   - 개발자 도구(F12)에서 페이지 HTML 구조 확인
   - `.content`, `#main` 등 일반적인 콘텐츠 컨테이너 확인
   - 만약 특이한 구조라면 `selector_patterns`에 추가 가능

4. **BeautifulSoup 대체 로직 시도**
   - BeautifulSoup이 설치되지 않은 경우 기본 정규식 파싱 사용
   - 로그에서 "BeautifulSoup 미설치" 메시지 확인

### 너무 많은 콘텐츠 추출되는 경우

1. **필터링 강화**
   - `selector_patterns`에서 더 구체적인 선택자 추가
   - 라인 필터링 임계값 증가 (3글자 → 5글자)

2. **최대 길이 제한**
   - `max_length` 값 조정 (기본값: 8000자)

### 특정 사이트 최적화

특정 정부 사이트의 구조가 일반적이지 않은 경우, `selector_patterns`를 확장할 수 있습니다:

```python
selector_patterns = [
    # 기존 패턴들...
    'div.site-content',      # 특정 사이트 A
    'section[data-content]', # 특정 사이트 B
    # ...
]
```

## 성능 최적화

### URL 요청
- **타임아웃**: 20초 (정부 사이트 고려)
- **재시도**: 현재는 단일 시도 (필요시 구현 가능)

### HTML 파싱
- **limit=50**: 가장 큰 텍스트 블록 찾을 때 처음 50개 div만 검사
- **캐싱**: 같은 URL 여러 번 추출 시 캐시 고려 가능

## 로그 시뮬레이션

디버깅을 위해 특정 URL에서 추출 테스트:

```python
from src.domains.infrastructure.services.detail_content_service import DetailContentService
from src.app.core.config import load_config

config = load_config()
service = DetailContentService(config)

# 테스트 URL
test_url = "https://example.com/large-waste-disposal"

# 추출 시도
content, metadata = service.extract_info_from_url(test_url)

print(f"추출 성공: {len(content)} 자")
print(f"메타데이터: {metadata}")
```

## 참고 문서

- `instructions/development_guidelines.md` - 일반 개발 가이드
- `src/domains/infrastructure/services/detail_content_service.py` - 서비스 구현
- `src/domains/infrastructure/ui/detail_content_ui.py` - UI 구현
