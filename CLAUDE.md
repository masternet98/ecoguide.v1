# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# CLAUDE.md - EcoGuide.v1 빠른 참조 가이드

Claude Code가 이 프로젝트에서 작업할 때 **5분 내에 파악해야 할 핵심 사항**입니다.

## 🎯 프로젝트 핵심 이해

**EcoGuide.v1**: AI 기반 대형폐기물 관리 도우미
- 시민들의 폐기물 식별 및 배출 방법 안내
- 지자체별 배출 규정 연결
- Streamlit + OpenAI Vision API + 도메인 기반 아키텍처 (5개 도메인, 18개 서비스)

## 📚 세부 문서 가이드

| 상황 | 참조 문서 | 용도 |
|------|-----------|------|
| 🆕 **모든 개발 작업** | `instructions/development_guidelines.md` | 종합 개발 가이드 (시나리오, 코드 패턴, 아키텍처) |
| 🤖 **다른 AI 도구** | `agents.md` | ChatGPT, Copilot 등 타 AI용 |
| 📋 **빠른 확인** | 이 문서 | 핵심 규칙, 금지사항, 아키텍처 심화 |

## 개발 명령어

### 애플리케이션 실행
- **Streamlit 앱 시작**: `streamlit run app.py`
- **앱 실행 (Docker 호환)**: `streamlit run app_new.py`
- **디버그 모드**: `streamlit run app.py --logger.level=debug`
- **대안 실행 방법**: `bash run.sh` (Linux/Mac) 또는 `run.bat` (Windows)

### 테스트
- **모든 테스트 실행**: `pytest` (테스트는 `test/` 디렉토리에 위치)
- **특정 테스트 파일 실행**: `pytest test/test_vision_pipeline.py`
- **상세 출력으로 테스트 실행**: `pytest -v`
- **특정 테스트만**: `pytest -k vision -v` (이름에 "vision"이 포함된 테스트)
- **빠른 실행 (병렬)**: `pytest -n auto`

### 패키지 설치
- **핵심 의존성 설치**: `pip install -r requirements.txt`
- **비전 의존성 설치** (선택사항, CPU 전용): `pip install rembg mediapipe ultralytics opencv-python`
- **GPU 지원을 위한 PyTorch 설치**: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`

### 개발 환경 설정
- **가상환경 생성**: `python -m venv venv`
- **활성화 (Linux/Mac)**: `source venv/bin/activate`
- **활성화 (Windows)**: `venv\Scripts\activate`
- **환경변수 설정**: `.env` 파일에 `OPENAI_API_KEY` 등 설정

## 🚨 핵심 규칙 (5분 안에 숙지)

### 🔴 절대 금지 (NEVER DO)
- ❌ `src/services/`에 새 파일 생성 → `src/domains/{domain}/services/` 사용
- ❌ `from src.core.config` → `from src.app.core.config` 사용
- ❌ 도메인 간 직접 import → ServiceFactory 사용
- ❌ 설계서를 `claudedocs/`에 생성 → `instructions/` 사용

### ✅ 필수 준수 (MUST DO)
- ✅ 새 기능은 **도메인별 분류** 후 배치
  - 이미지/AI → `analysis`, 프롬프트 → `prompts`, 행정구역 → `district`
  - 모니터링 → `monitoring`, 시스템 → `infrastructure`
- ✅ 새 서비스는 `SERVICE_DOMAIN_MAP`에 등록
- ✅ Config는 `src.app.core.config.load_config()` 사용
- ✅ **설계서는 반드시 `instructions/` 폴더에 생성**

**💡 모르겠으면**: `instructions/comprehensive_development_guidelines.md` 확인

## 🏗️ 아키텍처 핵심 구조

**도메인 기반 아키텍처**: 5개 핵심 도메인으로 기능 분리
```
src/domains/
├─ analysis/      # 이미지/AI 분석
├─ prompts/       # 프롬프트 관리
├─ district/      # 행정구역 데이터
├─ monitoring/    # 시스템 모니터링
└─ infrastructure/ # 인프라 서비스
```

**각 도메인 구조**:
```
domain/
├─ services/   # 비즈니스 로직
├─ ui/        # UI 컴포넌트
└─ types.py   # 타입 정의
```

**📖 상세 구조**: `instructions/architecture_development_guidelines.md` 참조

## 🔧 빠른 시작 패턴

### 새 서비스 추가
```python
# 1. 도메인 결정 → src/domains/{domain}/services/
# 2. BaseService 상속
# 3. SERVICE_DOMAIN_MAP에 등록
```

### 새 UI 컴포넌트 추가
```python
# 1. src/domains/{domain}/ui/
# 2. BaseUIComponent 상속
# 3. self.get_service() 사용
```

### 설정 추가
```python
# src/app/core/config.py에 추가
# load_config()로 사용
```

**📖 상세 패턴**: `instructions/development_guidelines.md` 참조

## 🔧 Service Factory & 의존성 주입

### ServiceFactory 사용
모든 도메인 간 서비스 접근은 **ServiceFactory를 반드시 사용**:

```python
# ✅ 올바른 방법 (UI 컴포넌트에서)
class MyUI(BaseUIComponent):
    def __init__(self, app_context):
        super().__init__(app_context)
        # app_context 제공됨
        self.service = self.get_service('service_name')

# ✅ 올바른 방법 (페이지에서)
from src.app.core.app_factory import ApplicationFactory
app_context = ApplicationFactory.create_application()
service = app_context.get_service('vision_service')

# ❌ 절대 금지 (직접 import)
from src.domains.analysis.services.vision_service import VisionService
```

### 등록된 18개 서비스 및 위치

| 도메인 | 서비스명 | 경로 |
|--------|----------|------|
| **analysis** | vision_service | `src/domains/analysis/services/vision_service.py` |
| | openai_service | `src/domains/analysis/services/openai_service.py` |
| | confirmation_service | `src/domains/analysis/services/confirmation_service.py` |
| | accuracy_tracking_service | `src/domains/analysis/services/accuracy_tracking_service.py` |
| | waste_classification_service | `src/domains/analysis/services/waste_classification_service.py` |
| | ai_classification_mapper | `src/domains/analysis/services/ai_classification_mapper.py` |
| **prompts** | prompt_service | `src/domains/prompts/services/prompt_service.py` |
| | prompt_manager | `src/domains/prompts/services/prompt_manager.py` |
| | prompt_renderer | `src/domains/prompts/services/prompt_renderer.py` |
| | prompt_validator | `src/domains/prompts/services/prompt_validator.py` |
| **district** | district_service | `src/domains/district/services/district_service.py` |
| | district_api | `src/domains/district/services/district_api.py` |
| | district_cache | `src/domains/district/services/district_cache.py` |
| | district_loader | `src/domains/district/services/district_loader.py` |
| | location_service | `src/domains/district/services/location_service.py` |
| | rag_context_service | `src/domains/district/services/rag_context_service.py` |
| **infrastructure** | search_manager | `src/domains/infrastructure/services/search_manager.py` |
| | tunnel_service | `src/domains/infrastructure/services/tunnel_service.py` |
| **monitoring** | monitoring_service | `src/domains/monitoring/services/monitoring_service.py` |

📍 **ServiceFactory 정의**: `src/app/core/service_factory.py:144-179`

## ⚙️ 설정(Configuration) 패턴

### Config 로드 및 사용
```python
# ✅ 올바른 방법
from src.app.core.config import load_config

config = load_config()
# 하위 설정 접근
api_key = config.openai_api_key
vision_config = config.vision_config  # VisionConfig 객체
```

### Config 계층 구조
```python
Config (root)
├─ openai_api_key          # API 키
├─ vision_config           # VisionConfig
│  ├─ enable_background_removal
│  ├─ hand_detection_threshold
│  └─ object_detection_model
├─ district_config         # DistrictConfig
├─ search_config           # SearchProviderConfig
├─ location_config         # LocationConfig
└─ prompt_config           # PromptConfig
```

### 환경변수 설정
```bash
# .env 파일 (개발용)
OPENAI_API_KEY=sk-...
VWORLD_API_KEY=...
NOTIFICATION_EMAIL_USER=...
NOTIFICATION_EMAIL_PASSWORD=...

# Streamlit Secrets (.streamlit/secrets.toml - 배포용)
[general]
OPENAI_API_KEY = "sk-..."
```

📍 **Config 정의**: `src/app/core/config.py`

## 🚩 Feature Flags 활용

애플리케이션은 기능을 선택적으로 활성화/비활성화할 수 있음:

```python
# ✅ 기능 확인
app_context = ApplicationFactory.create_application()
if app_context.is_feature_enabled('vision_enabled'):
    # 비전 기능 사용
    pass

if app_context.is_feature_enabled('tunnel_enabled'):
    # 터널 기능 사용
    pass
```

**주요 Feature Flags:**
- `vision_enabled` - 로컬 비전 파이프라인
- `tunnel_enabled` - SSH 터널 기능
- `district_enabled` - 행정구역 데이터
- `prompt_enabled` - 프롬프트 관리
- `location_enabled` - 위치 기능

📍 **Feature Registry**: `src/app/core/feature_registry.py`

## 🗂️ Session State 패턴

```python
# ✅ Session state 접근 (Streamlit 재실행 간 유지)
from src.app.core.session_state import SessionStateManager

session_manager = SessionStateManager()
session_manager.ensure_initialized()

# 이미지 상태 접근
image_state = st.session_state.image_session_state
image_state.original_image = uploaded_image
```

## ⚡ 작업 체크리스트

### 시작할 때
- [ ] 어떤 도메인에 속하는 작업인가?
- [ ] 세부 가이드가 필요하면 `instructions/development_guidelines.md` 확인
- [ ] 서비스는 ServiceFactory 등록 필요한가?

### 코드 작성 시
- [ ] 올바른 도메인에 배치했는가?
- [ ] `src.app.core.config` 경로 사용했는가?
- [ ] 새로운 서비스는 `SERVICE_DOMAIN_MAP`에 등록했는가?
- [ ] 도메인 간 접근은 ServiceFactory를 통했는가?

### 테스트 및 완료 전
- [ ] `pytest` 또는 `pytest test/test_vision_pipeline.py`로 테스트 실행
- [ ] `streamlit run app.py`로 전체 기능 확인
- [ ] 기존 기능이 깨지지 않았는가?

## 🐛 일반적인 문제 해결

### ServiceFactory에서 서비스 못 찾음
1. `src/app/core/service_factory.py`에서 SERVICE_DOMAIN_MAP 확인
2. 서비스 클래스명이 파일명과 일치하는가? (예: `vision_service.py` → `VisionService`)
3. 서비스 __init__ 파라미터 확인

### Import 경로 오류
```bash
# 올바른 경로 확인
from src.app.core.config import load_config  ✅
from src.core.config import load_config      ❌ (경로 오류)

from src.domains.analysis.services.vision_service import VisionService  ✅ (직접 import 가능)
from src.services.vision_service import VisionService                    ❌ (폐지된 경로)
```

### Streamlit 페이지 안 보임
1. 파일명이 `pages/01_page_name.py` 형식인가?
2. `st.set_page_config()` 호출했는가?
3. `streamlit run app.py`로 실행했는가? (app_new.py 아님)

---

**📖 상세 가이드**: `instructions/development_guidelines.md` 참조
**📍 설정 검증**: `src/app/core/config_validator.py`
**🔧 에러 처리**: `src/app/core/error_handler.py`