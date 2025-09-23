# CLAUDE.md - EcoGuide.v1 빠른 참조 가이드

Claude Code가 이 프로젝트에서 작업할 때 **5분 내에 파악해야 할 핵심 사항**입니다.

## 🎯 프로젝트 핵심 이해

**EcoGuide.v1**: AI 기반 대형폐기물 관리 도우미
- 시민들의 폐기물 식별 및 배출 방법 안내
- 지자체별 배출 규정 연결
- Streamlit + OpenAI Vision API + 도메인 기반 아키텍처

## 📚 세부 문서 가이드

| 상황 | 참조 문서 | 용도 |
|------|-----------|------|
| 🆕 **모든 개발 작업** | `instructions/development_guidelines.md` | 종합 개발 가이드 (시나리오, 코드 패턴, 아키텍처) |
| 🤖 **다른 AI 도구** | `agents.md` | ChatGPT, Copilot 등 타 AI용 |
| 📋 **빠른 확인** | 이 문서 | 핵심 규칙, 금지사항 |

## 개발 명령어

### 애플리케이션 실행
- **Streamlit 앱 시작**: `streamlit run app.py`
- **대안 실행 방법**: `run.bat` (Windows 배치 파일)

### 테스트
- **모든 테스트 실행**: `pytest` (테스트는 `test/` 디렉토리에 위치)
- **특정 테스트 파일 실행**: `pytest test/test_vision_pipeline.py`
- **상세 출력으로 테스트 실행**: `pytest -v`

### 패키지 설치
- **핵심 의존성 설치**: `pip install -r requirements.txt`
- **비전 의존성 설치** (선택사항, CPU 전용): `pip install rembg mediapipe ultralytics opencv-python`
- **GPU 지원을 위한 PyTorch 설치**: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`

## 🚨 핵심 규칙 (5분 안에 숙지)

### 🔴 절대 금지 (NEVER DO)
- ❌ `src/services/`에 새 파일 생성 → `src/domains/{domain}/services/` 사용
- ❌ `from src.core.config` → `from src.app.core.config` 사용
- ❌ 도메인 간 직접 import → ServiceFactory 사용

### ✅ 필수 준수 (MUST DO)
- ✅ 새 기능은 **도메인별 분류** 후 배치
  - 이미지/AI → `analysis`, 프롬프트 → `prompts`, 행정구역 → `district`
  - 모니터링 → `monitoring`, 시스템 → `infrastructure`
- ✅ 새 서비스는 `SERVICE_DOMAIN_MAP`에 등록
- ✅ Config는 `src.app.core.config.load_config()` 사용

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

## ⚡ 작업 체크리스트

### 시작할 때
- [ ] 어떤 도메인에 속하는 작업인가?
- [ ] 세부 가이드가 필요하면 `instructions/` 문서 확인

### 코드 작성 시
- [ ] 올바른 도메인에 배치했는가?
- [ ] `src.app.core.config` 경로 사용했는가?
- [ ] ServiceFactory에 등록했는가?

### 완료 전
- [ ] 기존 기능이 깨지지 않았는가?
- [ ] `streamlit run app.py`로 실행 확인

---

**📖 상세 가이드**: `instructions/development_guidelines.md` 참조