# EcoGuide 리팩토링 계획 (2025-09)

## 1. 현재 진단
- `src/core`는 앱 부트스트랩, 설정 검증, 기능 토글, 로깅, 세션 상태를 15개 이상의 고밀도 모듈에 몰아넣어 횡단 관심사와 도메인 로직이 강하게 결합돼 있습니다.
- `src/services`는 외부 연동(LLM, 검색, VWorld), 도메인 로직(프롬프트, 행정구역, 모니터링), 배치 유틸리티를 한데 섞고 있으며 `district_service.py`(~91 KB), `prompt_service.py`(~31 KB)처럼 단일 파일이 비대해 단일 책임 원칙을 위반하고 단위 테스트가 어렵습니다.
- `src/components`의 Streamlit 컴포넌트는 UI 렌더링, 상태 관리, 서비스 오케스트레이션을 동시에 처리(`monitoring_ui.py` 약 47 KB)해 재사용성과 테스트 용이성을 떨어뜨립니다.
- 기능 확장 대비 테스트 커버리지가 부족하고(`qdrant_test.py`는 비어 있음, 외부 API 목 부재) 핵심 플로우에 회귀 안전망이 없습니다.
- 문서와 엔트리 포인트가 어긋나 있고(`app_new.py` 언급이나 파일 부재) 한글 인코딩 문제도 반복돼 온보딩과 배포 신뢰도를 낮춥니다.

## 2. 리팩토링 목표
- 프레젠테이션, 애플리케이션 오케스트레이션, 도메인 로직이 독립적으로 진화할 수 있도록 계층 경계를 확립합니다.
- 비전, 지리, 프롬프트, 모니터링 흐름 전반에 결정론적 단위·통합 테스트 지점을 마련합니다.
- 설정·로깅·에러 처리·기능 토글을 재사용 가능한 코어 패키지로 격리해 도메인 결합도를 최소화합니다.
- 외부 연동(OpenAI, VWorld, 검색)을 인프라 어댑터 뒤로 추상화해 일관된 에러 처리·재시도 정책을 제공합니다.
- Streamlit UI를 컴포넌트 + 뷰모델 패턴으로 단순화해 향후 멀티 페이지 확장을 지원합니다.

## 3. 목표 아키텍처 (North Star)
- 프레젠테이션 계층: `app.py`, `src/presentation`에서 Streamlit 페이지·레이아웃·뷰모델을 담당.
- 애플리케이션 계층: `src/application`에서 서비스 조합과 유즈케이스 오케스트레이션을 담당.
- 도메인 계층: `src/domain/<context>`에 순수 도메인 모델·정책·서비스 인터페이스를 배치.
- 인프라 계층: `src/infrastructure`에서 외부 클라이언트(LLM, 지리, 검색), 스토리지, 스케줄러, 메시징 어댑터를 제공.
- 코어 계층: `src/core`는 앱 컨텍스트, 설정, 로깅, 에러 처리, 세션 상태, 기능 토글만 담당하도록 축소.

### 도메인 패키지 후보
- `domain/vision`: 프롬프트 연계 이미지 분석, 응답 파싱, 모델 선택 정책.
- `domain/prompts`: 템플릿 CRUD, 기능 매핑, 사용량 분석, 백업 정책.
- `domain/geospatial`: 행정구역 데이터 로딩, 캐시 무효화, 좌표 검증.
- `domain/monitoring`: 이벤트 규칙, 알림 정책, 터널 라이프사이클 관리.
- `domain/search`: 링크 수집, 프로바이더 랭킹, 중복 제거.

### 인프라 추상화
- `infrastructure/llm/openai_client.py`, `infrastructure/geo/vworld_client.py`, `infrastructure/search/*`에서 API 접근과 공통 재시도/백오프 헬퍼 제공.
- `infrastructure/storage/local_fs.py`(향후 클라우드 어댑터 포함)로 모든 파일 IO를 중재.
- `infrastructure/scheduling`으로 배치 작업과 백그라운드 태스크 관리.

### 코어 패키지 분할
- `core/app/context.py`, `core/app/factory.py`, `core/app/di.py`에서 애플리케이션 라이프사이클 관리.
- `core/config/loader.py`, `core/config/schema.py`에 Pydantic 기반 설정 검증 도입.
- `core/logging/*`에 구조화 로깅·트레이싱 헬퍼 배치.
- `core/errors/*`에 에러 분류와 UI 어댑터 구성.
- `core/session/*`으로 Streamlit 세션 상태 격리.
- `core/feature_toggle/*`로 기능 레지스트리와 데코레이터 관리.

## 4. 디렉터리 개편 초안
```
Current                            -> Proposed
-----------------------------------  ---------------------------------------------
src/core/app_factory.py             -> src/core/app/context.py, factory.py
src/core/service_factory.py         -> src/core/app/di.py
src/services/prompt_service.py      -> src/domain/prompts/service.py, repository.py, models.py
src/services/district_service.py    -> src/domain/geospatial/district_loader.py, cache.py, validators.py
src/services/openai_service.py      -> src/infrastructure/llm/openai_client.py + src/domain/vision/providers/openai.py
src/components/*                    -> src/presentation/components/* + src/presentation/viewmodels/*
test/*                              -> tests/unit, tests/integration, tests/e2e
```

## 5. 단계별 실행 계획
### Phase 0 (1주차): 베이스라인 & 안전망 구축
- 엔트리 포인트(`app_new.py` vs `app.py`)를 정리하고 문서·Docker 빌드 컨텍스트를 일치시킵니다.
- `.env` 및 설정 기본값을 인벤토리화하고 필수 키에 대한 검증·폴백을 정의합니다.
- 프롬프트 초기화와 위치 조회에 대한 스냅샷 기반 회귀 테스트를 추가합니다.
- 로깅 설정을 표준화하고 대표 운영 로그 샘플을 확보합니다.

### Phase 1 (2주차): 코어 플랫폼 정비
- `src/core`를 서브패키지로 재구성하고 `ApplicationContext`·세션 매니저를 경량 dataclass로 단순화합니다.
- `dependency_manager.py`, `service_factory.py`의 동적 임포트를 명시적 레지스트리·인터페이스 구조로 교체합니다.
- `config_validator.py`를 Pydantic 스키마로 대체하고 커버리지 테스트를 작성합니다.
- `core/error_handler.py`에서 Streamlit 전용 UI 헬퍼를 추출하여 프레젠테이션 계층 어댑터로 분리합니다.

### Phase 2 (3~4주차): 프롬프트·비전 도메인 분리
- `prompt_service.py`를 CRUD, 매핑, 사용량, 백업 모듈로 분할하고 파일 IO는 인프라 스토리지 어댑터를 경유하도록 변경합니다.
- 프롬프트 도메인 모델을 dataclass/Pydantic으로 정형화하고 단위 테스트를 추가합니다.
- 이미지 분석 응답 파싱을 도메인 로직으로 이동시키고 뷰모델에서 활용할 결정론적 유즈케이스를 제공합니다.
- `tests/unit/domain/prompts`, `tests/unit/domain/vision`에 샘플 데이터·모의 LLM 응답 픽스처를 포함한 단위 테스트를 추가합니다.

### Phase 3 (5~6주차): 지리·모니터링 도메인 재구성
- `district_service`를 로더, 캐시, 조회 모듈로 분해하고 파일 워처 또는 스케줄러 훅을 도입합니다.
- `location_service`가 플러그형 VWorld·캐시 어댑터를 주입받도록 리팩터링하고 폴백 전략을 구성합니다.
- 모니터링·알림·터널 로직을 `domain/monitoring`으로 이동시키고 외부 연동부를 인프라 어댑터로 전환합니다.
- 위치 조회→분석→알림까지 아우르는 통합 테스트를 구현합니다.

### Phase 4 (7주차): 인프라 강화
- HTTP 클라이언트를 `httpx` 기반으로 통일하고 공통 재시도/백오프·구조화된 에러 전파를 적용합니다.
- 파일 시스템 추상화를 도입해 테스트·향후 클라우드 스토리지 대응을 위한 의존성 주입을 지원합니다.
- `batch_service.py`를 스케줄러 인터페이스로 추상화하고 CLI 트리거를 분리합니다.

### Phase 5 (8주차): 프레젠테이션 정리
- Streamlit 컴포넌트와 애플리케이션 유즈케이스 사이에 뷰모델을 도입합니다.
- 대형 UI 모듈(`monitoring_ui.py`, `analysis_interface.py`)을 기능 단위 서브컴포넌트로 분해하고 책임을 문서화합니다.
- 멀티 페이지 조정을 위한 단순 네비게이션/라우터 모듈을 구축하고 상태 스코프를 정의합니다.

### Phase 6 (지속): 품질 게이트 & 배포 준비
- `pytest -q`, `ruff`, `mypy`, 포맷팅 검사를 GitHub Actions에 구성합니다.
- `docs/adr`에 ADR 템플릿을 추가해 아키텍처 결정을 기록합니다.
- Docker 이미지에 헬스체크와 관측 가능성 훅을 강화합니다.

## 6. 테스트 & 품질 전략
- 도메인 순수 단위 테스트, 인프라 어댑터 목 기반 테스트, 계층 간 통합 테스트, Playwright를 활용한 경량 Streamlit 스모크 테스트로 테스트 피라미드를 구축합니다.
- 프롬프트·비전 응답은 JSON 스냅샷 검증을 활용하고 픽스처는 `tests/conftest.py`에서 관리합니다.
- pytest-recording 또는 커스텀 스텁으로 외부 API 상호작용을 녹화/대체해 결정론을 확보합니다.

## 7. 위험 요소 및 선행 과제
- 대규모 모듈 이동은 브랜치 조율·머지 프리즈가 필요하므로 사전 커뮤니케이션이 필수입니다.
- 엔트리 포인트 불일치(`app_new.py`)를 Docker/배포 변경 전에 해결해야 합니다.
- 한글 인코딩 불일치를 해소하려면 저장소 전반 UTF-8 유지와 Windows 개발자 대상 `chcp 65001` 안내가 필요합니다.
- 운영 데이터셋(district JSON, 프롬프트 저장소) 마이그레이션 시 백업·롤백 계획을 마련해야 합니다.

## 8. 즉시 실행 체크리스트
- [ ] 표준 Streamlit 엔트리 파일을 확정하고 문서·Docker·실행 스크립트를 일치시킵니다.
- [ ] `src/core` 서브패키지 경계와 네이밍 컨벤션 초안을 작성합니다.
- [ ] 도메인 분리 우선순위(프롬프트 vs 지리)를 정하고 담당자를 지정합니다.
- [ ] 프롬프트 기본값·좌표→행정구역 변환용 회귀 테스트를 구현합니다.
- [ ] 통합할 로깅·설정 공통 유틸 목록을 정리합니다.
- [ ] 리팩토링 가이드를 팀 코딩 규칙·리뷰 체크리스트에 반영합니다.
