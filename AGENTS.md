# AI Agent Guidelines for EcoGuide.v1

## 🤖 AI 어시스턴트 작업 규칙
이 문서는 Claude, ChatGPT, GitHub Copilot 등 모든 AI 어시스턴트가 EcoGuide.v1에서 안전하고 일관되게 개발 작업을 수행하도록 돕는 필수 가이드다. 아래 규칙을 위반하면 즉시 작업을 중단하고 인간 담당자에게 확인해야 한다.

---

## 🚨 작업 전 필수 체크

### 1. 프로젝트 핵심 맥락
- EcoGuide.v1은 **AI 기반 대형폐기물 안내 도우미**다.
- 목표: 시민이 쉽게 폐기물을 식별·배출하고, 지자체 규정을 정확하게 안내한다.
- 주요 스택: Streamlit UI, OpenAI Vision API, 도메인 기반 아키텍처.

### 2. 필수 참조 문서
- `CLAUDE.md`: 5분 안에 읽는 핵심 요약(명령어, 금지사항, 체크리스트).
- `instructions/development_guidelines.md`: 설계 철학, 도메인 책임, 코드 패턴, 의사결정 가이드.
- `instructions/prd.md`: 제품 요구사항 및 사용자 시나리오.
- `instructions/done/structure_refactoring_completion_report.md`: 리팩토링 배경과 변경 내역.

### 3. 아키텍처 원칙 요약
- 모든 비즈니스 로직은 `src/domains/{domain}/services/`에 둔다.
- Streamlit 레이아웃은 `pages/`와 `src/components/`를 우선 사용한다. (도메인별 `ui/`는 레거시 호환 목적이며 신규 UI는 pages/components로 배치)
- 서비스 접근은 항상 ServiceFactory(`src/app/core/service_factory.py`)를 거친다.
- 설정은 `src/app/core/config.load_config()`로 로드하고, 비밀 값은 `.env` 또는 `.streamlit/secrets.toml`에서 관리한다.

---

## 🛠 실행·테스트 명령어

| 목적 | 명령 |
|------|------|
| 최신 Streamlit UI 실행 | `streamlit run app_new.py` |
| 레거시 UI 확인 | `streamlit run app.py` |
| Windows 단축 실행 | `run.bat` |
| 전체 테스트 | `pytest -q` |
| 선택 테스트 | `pytest -k <키워드> -q` |
| 기본 의존성 설치 | `pip install -r requirements.txt` |
| 비전 선택 의존성 | `pip install rembg mediapipe ultralytics opencv-python` |
| (필요 시) CPU 전용 PyTorch | `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu` |

---

## 📁 디렉터리 및 데이터 규칙

```
src/
├─ app/                # 앱 계층(팩토리, 설정, 로깅, 레이아웃)
├─ domains/            # 비즈니스 도메인
│  ├─ analysis/        # 이미지·AI 분석
│  ├─ prompts/         # 프롬프트 관리
│  ├─ district/        # 행정구역 데이터
│  ├─ monitoring/      # 모니터링/알림
│  └─ infrastructure/  # 검색, 파일, 배치 등 공통 인프라
├─ components/         # Streamlit 공용 컴포넌트
└─ pages/              # Streamlit 멀티 페이지 엔트리
```

- 실행 중 생성되는 파일은 `models/`, `uploads/`, `downloads/`, `temp/`에 저장한다. Git 추적 제외.
- 테스트 코드는 `test/` 아래 `test_*.py` 형식을 따른다. 도메인별 서브 디렉터리를 선호.
- `.streamlit/`, `.env`, `.gcloudignore` 등 환경 파일은 수정 시 각별히 확인.

---

## 🔴 절대 금지 (NEVER DO)

1. `src/services/` 또는 `src/core/`에 새 파일을 만들지 않는다.
2. `from src.core.config` 처럼 잘못된 import를 사용하지 않는다. (`from src.app.core.config`만 허용)
3. 도메인 간 직접 import로 순환 의존성을 만들지 않는다. ServiceFactory를 통해 접근한다.
4. 비즈니스 로직을 UI 파일에, UI 로직을 서비스 파일에 넣지 않는다.
5. 비밀 키·토큰을 코드에 하드코딩하지 않는다.
6. 기존 ServiceFactory 매핑을 삭제하거나 덮어쓰지 않는다.

---

## ✅ 필수 준수 (MUST DO)

### 1. 새 기능 개발 순서
```python
def classify_domain(feature_description: str) -> str:
    keywords = feature_description.lower()
    if any(word in keywords for word in ["이미지", "ai 분석", "vision", "openai"]):
        return "analysis"
    if any(word in keywords for word in ["프롬프트", "prompt", "텍스트", "템플릿"]):
        return "prompts"
    if any(word in keywords for word in ["행정구역", "지역", "위치", "district"]):
        return "district"
    if any(word in keywords for word in ["모니터링", "알림", "로깅", "monitoring"]):
        return "monitoring"
    if any(word in keywords for word in ["검색", "터널", "배치", "인프라", "system"]):
        return "infrastructure"
    raise ValueError("도메인 분류 실패: 아키텍트와 상의 필요")
```

1. **Step 1**: 위 분류 로직 또는 도메인 키워드를 기반으로 위치를 결정한다.
2. **Step 2**: `src/domains/{domain}/services/`에 비즈니스 로직 파일을 생성하고 BaseService를 상속한다.
3. **Step 3**: UI가 필요하면 `pages/` 또는 `src/components/`에 Streamlit 컴포넌트를 만든다. (레거시 `src/domains/{domain}/ui/`를 수정할 때는 반드시 호환성 여부 확인)
4. **Step 4**: `SERVICE_DOMAIN_MAP`에 서비스를 반드시 등록한다.
5. **Step 5**: 설정 값은 `config = load_config()`로 받아 사용한다.

```python
# 서비스 템플릿 예시
from typing import Any, Dict
from src.app.core.base_service import BaseService
from src.app.core.config import Config

class SampleService(BaseService):
    """도메인 비즈니스 로직을 담당."""
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.options = config.analysis  # 해당 도메인 설정 사용

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 비즈니스 로직만 작성
        return {}
```

```python
# ServiceFactory 등록 예시 (src/app/core/service_factory.py)
SERVICE_DOMAIN_MAP = {
    **EXISTING_DOMAIN_MAP,
    "sample_service": "analysis",
}
```

### 2. 기존 코드 개선 원칙
- 가능한 기존 클래스/함수에 메서드나 옵션을 추가하는 방식으로 확장한다.
- 동일 도메인 내 새 파일을 추가할 때에는 유지보수 책임자를 명시하거나 주석을 남긴다.
- 타 도메인과의 연동은 ServiceFactory에서 제공하는 accessor를 활용한다.

### 3. UI 작성 규칙
- 새 Streamlit UI는 `pages/`에서 엔트리를 만들고, 복잡한 컴포넌트는 `src/components/`에 캡슐화한다.
- 도메인 내부 `ui/` 디렉터리를 수정할 때는 pages/components와 역할이 중복되지 않는지 검토한다.

### 4. 테스트 작성
- 새 기능에는 대응 테스트를 `test/` 이하에 추가한다.
- 외부 서비스 호출은 mock/patch로 대체하여 결정론을 확보한다.

---

## 📋 작업 절차 & 체크리스트

### 코딩 전
- [ ] 도메인 분류 및 파일 위치 결정.
- [ ] 관련 참조 문서(특히 `development_guidelines.md`) 숙독.
- [ ] 기존 유사 기능 확인 후 재사용 여부 판단.

### 구현 중
- [ ] BaseService/BaseUIComponent를 상속했는가?
- [ ] `src.app.core.config` 경로를 사용했는가?
- [ ] 주석·문서화는 한글 우선으로 작성했는가?
- [ ] 타입 힌트를 명시했는가?

### 마무리 단계
- [ ] `SERVICE_DOMAIN_MAP`에 새 서비스를 등록했는가?
- [ ] `pytest -q`로 테스트를 통과했는가?
- [ ] `streamlit run app_new.py`로 주요 페이지가 정상 렌더링되는가?
- [ ] 변경된 파일에서 하드코딩된 비밀 키가 없는가?

---

## 🧭 의사결정 가이드

### 도메인 식별 질문
- 이 기능의 주된 비즈니스 가치는 무엇인가?
- 어떤 데이터/입출력을 다루는가?
- 기존 어느 도메인과 가장 밀접한가?
- 다른 도메인이 의존하게 될 가능성이 있는가?

### 파일 유형 판단
```python
def decide_file_bucket(purpose: str) -> str:
    use = purpose.lower()
    if "비즈니스" in use or "api" in use:
        return "services/"
    if "ui" in use or "streamlit" in use:
        return "pages/ or src/components/"
    if "타입" in use or "상수" in use:
        return "types.py / constants.py"
    return "재검토 필요"
```

### 수정 vs 신규
- 기존 함수/클래스를 확장하면 되는가? → 기존 파일 수정.
- 독립 테스트가 필요한가? → 새 파일 생성 가능 (도메인 합의 필수).
- 코드가 과도하게 비대해지는가? → 책임 분리를 고려.

### 의존성 원칙
- 도메인 내부: 직접 import 허용.
- 도메인 간: `app_context.get_service()` 또는 ServiceFactory로 접근.
- 외부 라이브러리: 한 곳에서 추상화하여 재사용.

---

## 🛡 보안·운영 & 품질

### API 키 관리
- 로컬: `.env` 사용 (Git 커밋 금지).
- 배포: `.streamlit/secrets.toml`.
- 코드 예시:
```python
from src.app.core.config import load_config
config = load_config()
openai_key = config.openai_api_key
```

### 에러 처리
```python
try:
    result = service.call()
except ExternalAPIError as exc:
    st.error("일시적인 문제로 AI 응답을 가져오지 못했습니다. 잠시 후 다시 시도해주세요.")
    logger.error("External API failed", exc_info=exc)
```

### 로깅 권장 레벨
```python
logger.debug("디버그 정보")      # 개발 중
logger.info("정상 흐름")        # 운영 모니터링
logger.warning("주의 필요")     # 잠재적 문제
logger.error("오류 발생")       # 즉시 대응
```

### 성능 및 확장
- 자주 요청되는 데이터는 `@st.cache_data(ttl=3600)`으로 캐싱.
- 무거운 리소스(모델 등)는 `@st.cache_resource` 사용.
- 대용량 처리는 `src/domains/infrastructure/services/batch_service.py` 패턴 참고.

---

## 🧪 디버깅 & 문제 해결

1. **Import 오류**
   ```bash
   python -c "from src.app.core.config import load_config"
   ```
   - 실패 시 파일 위치, `__init__.py`, ServiceFactory 매핑 순으로 점검.

2. **ServiceFactory 등록 누락**
   - `SERVICE_DOMAIN_MAP`에 키가 존재하는지 확인.
   - 클래스명과 파일명이 일치하는지 재확인.

3. **Streamlit 페이지 미표시**
   - `pages/0*_*.py` 네이밍 확인.
   - `st.set_page_config()` 호출 여부 확인.
   - `streamlit run app_new.py --logger.level=debug`로 로그 확인.

---

## 🧰 실용적 개발 시나리오

### 1. 새 기능 추가 (예: 음성 인식)
- 도메인: Analysis.
- 작업: `speech_service.py` 작성, 관련 컴포넌트 `pages/`에 추가.
- 체크: OpenAI 호출 mock 테스트 작성.

### 2. 성능 개선 (예: 이미지 분석 속도)
- 기존 서비스에 `analyze_image_fast` 메서드 추가.
- Monitoring 도메인에 성능 추적 메서드 연동.

### 3. 외부 API 연동 (예: 신규 AI 모델)
- Config에 키/모델 정보 추가.
- Infrastructure 또는 Analysis 서비스에서 API 추상화.
- 예외 처리 및 폴백 로직 구현.

---

## 🎯 AI 작업 목표

### Primary Goals
1. 사용자 가치 극대화 (정확한 배출 안내 제공).
2. 도메인 기반 아키텍처 100% 준수.
3. 유지보수 가능한 코드와 테스트 확보.
4. 기능 확장성을 고려한 설계.

### Success Metrics
- 모든 신규 파일이 올바른 도메인에 배치.
- Import 오류 0건.
- 기존 기능 회귀 0건.
- 코드 리뷰 시 아키텍처 위반 지적 0건.

### 작업 우선순위
1. 사용자 영향도 높은 기능 또는 버그.
2. 아키텍처 일관성 보존.
3. 테스트와 문서화.
4. 성능 및 운영 최적화.

---

## 📅 문서 메타
- 📝 작성일: 2025-09-23
- 🔄 버전: 4.1 (CLAUDE.md · development_guidelines.md 반영)
- 🎯 적용 대상: Claude, ChatGPT, GitHub Copilot 등 모든 AI 어시스턴트
- ⚡ 중요도: CRITICAL – 위 지침 미준수 시 즉시 보고
