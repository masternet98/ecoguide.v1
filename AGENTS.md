# Repository Guidelines
## 프로젝트 구조 및 모듈 구성
- `app_new.py`와 `app.py`는 Streamlit 진입점이며 Docker 이미지는 `app_new.py`를 사용합니다.
- 코어 로직은 `src/` 아래에 정리됩니다: `core/`는 앱 팩토리·설정·로깅, `services/`는 OpenAI·비전·검색, `components/`는 UI 컴포넌트, `pages/`는 멀티 페이지 라우트를 맡습니다.
- 실행 중 생성되는 데이터는 `models/`, `uploads/`, `downloads/`, `temp/`에 저장되며 테스트 코드는 `test/` 디렉터리에 `test_*.py` 패턴으로 둡니다.

## 빌드·테스트·개발 명령어
- `pip install -r requirements.txt`: Python 3.11 가상환경에 필수 의존성을 설치합니다.
- `streamlit run app_new.py`: 로컬에서 최신 Streamlit UI를 실행합니다. Windows 사용자는 동일 작업을 수행하는 `run.bat`을 활용할 수 있습니다.
- `pytest -q` / `pytest -k vision -q`: 전체 또는 선택 테스트를 빠르게 검증합니다.
- `docker build -t ecoguide .` / `docker run -e OPENAI_API_KEY=... -p 8501:8501 ecoguide`: 프로덕션 유사 환경이 필요할 때 사용합니다.

## 코딩 스타일 및 네이밍 규칙
- PEP 8을 기본으로 하며 들여쓰기는 공백 4칸을 유지합니다.
- 모듈·함수는 snake_case, 클래스는 CamelCase로 작성하고 공개 API에는 타입 힌트를 명확히 남깁니다.
- Streamlit 관련 코드는 `src/components`와 `pages`에 한정하고 `src/services`는 UI 의존성을 허용하지 않습니다.
- 의도가 모호한 경우에만 간결한 주석이나 docstring을 추가합니다.

## 테스트 가이드라인
- Pytest를 사용하며 새로운 기능 도입 시 관련 테스트를 `test/`에 함께 작성합니다.
- 테스트 함수 이름은 `test_` 접두사를 유지하고 공통 픽스처는 필요하면 `test/conftest.py`에 배치합니다.
- 커밋 전 `pytest -q`로 회귀를 확인하며 외부 서비스 호출은 mock/monkeypatch로 대체해 결정론을 확보합니다.

## 커밋 및 PR 가이드라인
- 커밋 메시지는 현재 시제의 Conventional Commit 형식을 권장합니다. 예: `feat(search): add bing fallback`.
- PR에는 변경 의도, 관련 이슈(`Closes #123`), UI 변경 시 스크린샷·GIF, 환경 변수 변경 사항, 테스트 통과 증빙을 포함합니다.
- 불필요한 revert를 피하고 기존 변경과 충돌하지 않도록 브랜치를 항상 최신으로 유지합니다.

## 보안 및 설정 팁
- 비밀 키는 로컬에서는 `.env`, 배포 환경에서는 `.streamlit/secrets.toml`에 보관하고 저장소에 커밋하지 않습니다.
- API 키는 `src/core/utils.resolve_api_key()`로 조회해 설정을 중앙에서 관리합니다.
