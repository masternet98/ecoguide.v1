# 소스 구조 설계 가이드라인

## 1. 목적과 적용 범위
- 초보 개발자도 기능 단위로 코드를 빠르게 탐색할 수 있도록 디렉터리 구조를 명확히 정의한다.
- `src/` 하위 모듈 재구성을 위한 기준 문서로 사용하며, 신규 파일·모듈 생성 시 이 가이드라인을 우선 참조한다.

## 2. 기본 원칙
1. **도메인 우선 구성**: 기능(analysis, prompts 등)별로 서비스·UI·타입을 한 폴더에 묶는다.
2. **계층 분리**: 애플리케이션 부트스트랩(`app/`), 도메인 로직(`domains/`), 페이지 라우팅(`pages/`)을 명확히 구분한다.
3. **공유 자원 최소화**: 범용 유틸 성격의 코드는 `domains/common/` 또는 `app/` 계층에만 둔다. 필요 이상으로 추상화 계층을 늘리지 않는다.
4. **의존성 단방향**: `app/ → domains/common → domains/<feature>` 순으로 의존하며, 도메인 간 직접 참조는 금지한다. 서로 필요한 경우 `domains/common`을 통해 의존성을 노출한다.
5. **Streamlit 진입 규칙**: 화면 진입점(`pages/`, `app/app.py`)에서는 도메인 UI 모듈을 통해서만 컴포넌트를 사용한다.

## 3. 권장 디렉터리 구조
```
src/
├─ app/
│  ├─ core/              # 애플리케이션 컨텍스트, 팩토리, 로깅 등
│  ├─ config/            # 설정 로딩·검증 모듈
│  └─ layouts/           # 공용 레이아웃 컴포넌트
├─ domains/
│  ├─ common/
│  │  ├─ services/       # 다수 도메인이 공유하는 서비스 (예: openai_service)
│  │  ├─ ui/             # 공용 UI (필요 최소)
│  │  └─ types.py        # 공통 데이터 타입/DTO
│  ├─ analysis/
│  │  ├─ services/
│  │  ├─ ui/
│  │  └─ types.py
│  ├─ prompts/
│  │  ├─ services/
│  │  ├─ ui/
│  │  └─ types.py
│  ├─ district/
│  │  ├─ services/
│  │  ├─ ui/
│  │  └─ types.py
│  ├─ monitoring/
│  │  ├─ services/
│  │  ├─ ui/
│  │  └─ types.py
│  └─ infrastructure/
│     ├─ services/
│     ├─ ui/
│     └─ types.py
├─ components/           # 기존 Streamlit 컴포넌트 호환 계층 (재export 전용)
└─ pages/                # 멀티 페이지 라우트
```

### 3.1 app/
- `app/core/`: `ServiceFactory`, `AppContext`, 로깅, 에러 핸들러 등 애플리케이션 전역 객체를 배치한다.
- `app/config/`: 환경 변수 로딩과 검증 모듈. 도메인별 config 스키마는 여기에서 정의한다.
- `app/layouts/`: 레이아웃, 내비게이션, 공용 프레임을 담당한다.

### 3.2 domains/
- 각 도메인 폴더는 3종 하위 디렉터리를 가진다.
  - `services/`: 도메인 로직, 외부 API 호출, 캐시 처리 등 순수 Python 서비스.
  - `ui/`: 해당 도메인 전용 Streamlit 컴포넌트. 네이밍은 `<feature>_<widget>.py`를 권장한다.
  - `types.py`: 데이터 클래스·TypedDict 등 도메인 고유 타입 정의.
- 서브 도메인(예: `infrastructure/search`)이 필요하면 `domains/infrastructure/search/services/` 형태로 한 단계 더 분할한다.

### 3.3 domains/common/
- 여러 도메인이 공유하는 서비스(`openai_service`, `prompt_service` 등)는 `domains/common/services/`로 이동한다.
- UI도 반드시 공용성이 명확할 때만 배치한다. 과도한 추상화가 되지 않도록 주의한다.

### 3.4 components/
- 기존 코드 호환을 위해 유지하며, 각 파일은 새 도메인 UI를 임포트해 thin wrapper 혹은 re-export 역할만 수행한다.
- 점진적 코드 정리 후 최종적으로 `components/` 계층을 제거할 수 있도록 TODO를 남긴다.

### 3.5 pages/
- 페이지 파일에서는 가능한 한 `from src.domains.<feature>.ui...`로 직접 임포트한다.
- 과도한 비즈니스 로직이 들어가지 않도록 하고, UI 렌더링과 도메인 서비스 호출만 담당한다.

### 3.6 도메인 분류 기준
파일 배치 시 다음 기준을 따라 도메인을 결정한다:

| 도메인 | 포함 모듈 | 분류 기준 |
|--------|-----------|-----------|
| **analysis** | vision_service, openai_service, 이미지 관련 UI | 이미지 분석 및 AI 비전 처리 |
| **district** | district_*, location_* | 행정구역 데이터 및 위치 관련 |
| **prompts** | prompt_*, AI 프롬프트 관련 | 프롬프트 관리 및 생성 |
| **monitoring** | monitoring_*, notification_* | 시스템 모니터링 및 알림 |
| **infrastructure** | search_*, tunnel_*, batch_*, file_* | 인프라, 유틸리티, 외부 연동 |
| **common** | 3개 이상 도메인에서 사용하는 서비스 | 범용 공통 서비스 (현재 해당 서비스 없음) |

**분류 우선순위**:
1. **공통성 높음** → `domains/common/`
2. **특정 도메인 전용** → `domains/<domain>/`
3. **인프라/유틸리티** → `domains/infrastructure/`

**판단 기준**:
- 3개 이상 도메인에서 사용 → common
- 특정 비즈니스 기능에 특화 → 해당 도메인
- 시스템 지원/유틸리티 성격 → infrastructure

## 4. 네이밍 및 임포트 규칙
- 모듈 및 함수 이름은 snake_case, 클래스는 PascalCase를 유지한다.
- 도메인 간 의존이 필요하면 `domains.common`에서 public API를 노출하고, `__all__`로 공개 범위를 명시한다.
- `ServiceFactory`에서 사용하는 `module_path`는 `src.domains.<domain>.services.<module>` 패턴을 따른다.
- 마이그레이션 단계에서는 `src/services/<legacy>.py`와 `src/components/<legacy>.py`에 `from src.domains... import ...` 식의 re-export를 두어 기존 경로도 일시적으로 유지한다.

## 5. 마이그레이션 가이드
1. **새 디렉터리 생성**: 위 구조에 맞춰 빈 디렉터리 및 `__init__.py`를 만든다.
2. **서비스 이동**: 도메인 서비스 파일을 이동하고, `ServiceFactory`의 `module_path`와 테스트 임포트를 동시에 수정한다.
3. **UI 이동**: Streamlit 컴포넌트를 `domains/<feature>/ui/`로 옮기고, `src/components`에는 `from ... import *` 형태의 래퍼를 남긴다.
4. **타입 통합**: 관련 타입 정의를 `types.py`로 이동시키고, 기존 모듈에서는 새 경로를 재사용한다.
5. **검증**: 각 단계마다 `pytest -q`와 주요 페이지 핸드 오프 테스트를 수행한다.
6. **래퍼 제거**: 모든 호출부 수정이 끝나면 `components/` 및 `services/`의 임시 래퍼를 삭제한다.

## 6. 문서 유지보수
- 구조 변경 시 이 문서를 먼저 업데이트하고, 수정 사유·예시 구조를 추가한다.
- 리팩토링 계획서(`structure_refactoring_plan.md`)에는 항상 최신 버전의 이 가이드라인을 참조하도록 링크 혹은 문구를 유지한다.
