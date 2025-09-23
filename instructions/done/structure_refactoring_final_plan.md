# 소스 폴더 구조 리팩토링 최종 실행계획 (v3)

## 참고 문서
- [소스 구조 설계 가이드라인](./structure_guidelines.md)

## 1. 개요
- **목표**: `src/` 하위 모듈을 기능 중심으로 재배치해, 신규 인력도 코드 흐름을 빠르게 이해할 수 있도록 한다.
- **범위**: 디렉터리 구조 개편, 임포트 경로 수정, 래거시 경로 호환 레이어 구성. 비즈니스 로직 수정은 최소화한다.
- **원칙**: 가이드라인 문서를 준수하여 도메인별로 서비스·UI·타입을 묶고, 점진적 마이그레이션을 위해 호환 래퍼를 병행 유지한다.
- **실행 전략**: **복사 후 점진적 전환** 방식을 채택하여 안전성을 최우선으로 한다.

## 2. 현행 구조 요약
```
src/
├─ components/   # Streamlit UI 및 도우미 (21개 파일)
├─ core/         # 앱 컨텍스트, 팩토리, 설정 (13개 파일)
├─ layouts/      # 공통 레이아웃 (1개 파일)
├─ pages/        # Streamlit 멀티 페이지 (1개 파일)
└─ services/     # 비즈니스 로직, 외부 API (27개 파일)
```

**현재 문제점**:
- `services/`에 27개 모듈이 집중되어 도메인 경계가 불분명하다.
- UI가 `components/` 루트에 혼재해 특정 기능에 속하는지 바로 파악하기 어렵다.
- `ServiceFactory`는 `src.services.*` 경로를 기준으로 동적 로딩한다.

## 3. 목표 구조
```
src/
├─ app/
│  ├─ core/              # 애플리케이션 컨텍스트, 팩토리, 로깅
│  ├─ config/            # 설정 로딩·검증
│  └─ layouts/           # 공용 레이아웃
├─ domains/
│  ├─ analysis/
│  │  ├─ services/      # vision_service, openai_service
│  │  ├─ ui/           # 이미지 분석 관련 UI
│  │  └─ types.py      # vision_types
│  ├─ prompts/
│  │  ├─ services/     # prompt_*, 프롬프트 관련
│  │  ├─ ui/          # 프롬프트 관리 UI
│  │  └─ types.py     # prompt_types
│  ├─ district/
│  │  ├─ services/    # district_*, location_*
│  │  ├─ ui/         # 행정구역 관련 UI
│  │  └─ types.py    # 행정구역 타입
│  ├─ monitoring/
│  │  ├─ services/   # monitoring_*, notification_*
│  │  ├─ ui/        # 모니터링 대시보드 UI
│  │  └─ types.py   # 모니터링 타입
│  └─ infrastructure/
│     ├─ services/   # search_*, tunnel_*, batch_*, file_*
│     ├─ ui/        # 인프라 관리 UI
│     └─ types.py   # 인프라 타입
├─ components/          # 래거시 호환 계층 (re-export 전용)
├─ services/           # 래거시 호환 계층 (re-export 전용)
└─ pages/              # 멀티 페이지 라우트
```

## 4. 실행 단계 (총 7-8일)

### Phase 0: 준비 및 검증 (Day 0-1)
1. **가이드라인 문서 최종 검토** 및 도메인 분류 기준 합의
2. **신규 디렉터리 구조 생성**: `src/app`, `src/domains`, 하위 도메인 폴더
3. **모든 새 폴더에 `__init__.py` 배치**
4. **ServiceFactory 호환성 검증 스크립트 작성**:
   ```python
   def validate_service_loading():
       """기존 경로와 새 경로 모두에서 서비스 로딩 테스트"""
       # 의존성 체인 검증
       # 동적 로딩 메커니즘 확인
       pass
   ```
5. **기준선 테스트**: `pytest -v` 실행하여 현재 상태 기록
6. **Git 백업**: `git add . && git commit -m "Phase 0: 리팩토링 시작 전 백업"`

### Phase 0.5: 안전한 복사 시작 (Day 1-2)
1. **우선순위 서비스 복사** (이동 아님):
   - `vision_service.py`, `openai_service.py`를 `src/domains/analysis/services/`에 **복사**
   - `prompt_service.py`를 `src/domains/prompts/services/`에 **복사**
   - 기존 파일은 그대로 유지
2. **ServiceFactory 이중 경로 지원 추가**:
   ```python
   # ServiceFactory에서 새 경로를 1차로 시도, 기존 경로를 fallback으로 사용
   def _load_service_class(self, service_name: str):
       # Phase 0.5에서 복사된 서비스들의 새 경로 시도
       domain_map = {
           'vision_service': 'analysis',
           'openai_service': 'analysis',
           'prompt_service': 'prompts'
       }

       if service_name in domain_map:
           try:
               domain = domain_map[service_name]
               return importlib.import_module(f"src.domains.{domain}.services.{service_name}")
           except ImportError:
               pass  # fallback to legacy path

       # 기존 경로 fallback
       return importlib.import_module(f"src.services.{service_name}")
   ```
3. **Wrapper 모듈 생성 및 검증**: `src/services/`에 기존 import 경로 유지용 wrapper 생성
4. **핵심 테스트 실행**: `pytest -k service_factory -v`

### Phase 1: 도메인별 서비스 복사 (Day 2-4)
1. **도메인 우선순위**에 따라 순차 복사:
   - **1순위**: `district` (독립성 높음)
   - **2순위**: `infrastructure` (유틸리티 성격)
   - **3순위**: `monitoring` (의존성 중간)
   - **4순위**: `analysis` (다른 도메인과 연관)

2. **각 도메인별 작업**:
   - 해당 도메인 `services/` 폴더에 파일 **복사**
   - `__all__` 리스트에 공개 API 명시
   - ServiceFactory의 `domain_map`에 새 서비스 추가:
     ```python
     # Phase 1 완료 후 domain_map 확장 예시
     domain_map = {
         'vision_service': 'analysis',
         'openai_service': 'analysis',
         'prompt_service': 'prompts',
         'district_service': 'district',
         'monitoring_service': 'monitoring',
         'notification_service': 'monitoring',
         'search_manager': 'infrastructure',
         'tunnel_service': 'infrastructure',
         'batch_service': 'infrastructure'
     }
     ```
   - 도메인별 wrapper 생성 및 검증

3. **단계별 검증**:
   - 각 도메인 완료 후 관련 페이지 수동 테스트
   - `pytest -q` 실행으로 회귀 없음 확인

### Phase 2: 도메인 UI 복사 및 재배치 (Day 4-6)
1. **UI 컴포넌트 복사**:
   - `analysis`, `prompts`, `monitoring`, `district`, `infrastructure` 관련 컴포넌트를 `domains/<feature>/ui/`로 **복사**
   - 기존 `src/components/` 파일들은 유지

2. **Thin wrapper 작성**:
   - `src/components/`에서 새 도메인 UI를 import하는 wrapper 작성
   - 기존 import 경로가 깨지지 않도록 보장

3. **페이지별 점진적 수정**:
   - 새 프로젝트 요구사항에 맞춰 페이지에서 도메인 경로 직접 사용
   - 기존 wrapper 경로도 병행 지원

4. **수동 테스트**: 모든 페이지 진입 및 핵심 기능 동작 확인

### Phase 3: App 계층 구성 (Day 6-7)
1. **핵심 모듈 복사**:
   - `src/core/` 내용을 `src/app/core`로 **복사**
   - `src/layouts/` 내용을 `src/app/layouts`로 **복사**
   - 설정 모듈을 `src/app/config`로 재구성

2. **기존 경로 re-export**:
   - `src/core/__init__.py`에 새 경로 re-export 추가
   - 기존 import 경로 호환성 유지

3. **진입점 업데이트**:
   - `app.py`에서 새 경로 참조
   - `pages/*.py`에서 새 경로 사용

4. **전체 검증**:
   - `streamlit run app.py` 수동 기동 테스트
   - 모든 페이지 기능 동작 확인
   - `pytest -v` 전체 테스트 실행

### Phase 4: 점진적 전환 및 정리 (Day 7-8)
1. **서비스별 점진적 전환**:
   - 새 경로 사용처를 하나씩 전환
   - 기존 파일 사용이 0이 된 서비스부터 제거

2. **Import 경로 정리**:
   - ServiceFactory에서 기존 경로 fallback 제거
   - 새 경로만 사용하도록 단순화

3. **래거시 정리**:
   - 사용하지 않는 기존 파일 제거
   - 불필요한 wrapper 제거
   - 빈 디렉터리 정리

4. **최종 검증**:
   - `pytest -v` 최종 테스트
   - 전체 애플리케이션 기능 검증
   - 성능 회귀 체크

## 5. ServiceFactory 변경 전략

### 5.1 현재 메커니즘
```python
# 현재: src.services.* 경로만 지원
module_path = f"src.services.{service_name}"
```

### 5.2 Phase 0.5 이후 (이중 경로 지원)
```python
def _load_service_class(self, service_name: str):
    # 1차: 새 도메인 경로 시도
    domain_paths = [
        f"src.domains.analysis.services.{service_name}",
        f"src.domains.district.services.{service_name}",
        f"src.domains.prompts.services.{service_name}",
        f"src.domains.monitoring.services.{service_name}",
        f"src.domains.infrastructure.services.{service_name}",
    ]

    for path in domain_paths:
        try:
            return importlib.import_module(path)
        except ImportError:
            continue

    # 2차: 기존 경로 fallback
    try:
        return importlib.import_module(f"src.services.{service_name}")
    except ImportError:
        raise ImportError(f"Service {service_name} not found")
```

### 5.3 Phase 4 이후 (새 경로만 지원)
```python
# 최종: 도메인 경로만 지원, fallback 제거
SERVICE_DOMAIN_MAP = {
    'openai_service': 'analysis',
    'vision_service': 'analysis',
    'district_service': 'district',
    'prompt_service': 'prompts',
    'monitoring_service': 'monitoring',
    'notification_service': 'monitoring',
    'search_manager': 'infrastructure',
    'tunnel_service': 'infrastructure',
    'batch_service': 'infrastructure',
    # 공통 서비스들 (3개 이상 도메인에서 사용)
    # 현재는 해당하는 서비스 없음
}

def _load_service_class(self, service_name: str):
    domain = SERVICE_DOMAIN_MAP.get(service_name)
    if not domain:
        raise ValueError(f"Unknown service: {service_name}")

    module_path = f"src.domains.{domain}.services.{service_name}"
    return importlib.import_module(module_path)
```

## 6. 진입점 테스트 전략

현재 저장소 실태: **app.py만 존재** (app_new.py 없음)

### 6.1 테스트 진입점
- **개발/테스트**: `streamlit run app.py`
- **배포 확인**: 동일하게 `streamlit run app.py`

### 6.2 각 Phase별 검증
- **Phase 0-2**: 백엔드 변경이므로 `streamlit run app.py`로 UI 정상 동작 확인
- **Phase 3**: `app.py` 수정 후 즉시 기동 테스트
- **Phase 4**: 최종 전체 기능 검증

## 7. 위험 요소와 완화 전략

### 7.1 주요 위험 요소
1. **ServiceFactory 동적 로딩 실패**
2. **Streamlit UI 컴포넌트 참조 깨짐**
3. **도메인 간 순환 의존성 발생**
4. **테스트 경로 불일치**

### 7.2 완화 전략
1. **롤백 계획**: 각 Phase별 Git 커밋으로 즉시 롤백 가능
2. **점진적 검증**: 파일 복사 후 즉시 관련 기능 수동 테스트
3. **의존성 매핑**: 사전에 서비스 간 의존성 그래프 작성
4. **Streamlit 캐시 클리어**: UI 변경 후 캐시 초기화
5. **백업 전략**: 각 단계 시작 전 `git stash` 또는 branch 생성
6. **이중 경로 지원**: 마이그레이션 기간 동안 기존/새 경로 모두 지원

### 7.3 응급 대응 절차
```bash
# 단계별 롤백
git log --oneline -5  # 최근 커밋 확인
git reset --hard <이전_커밋_해시>

# 캐시 클리어
rm -rf .streamlit/
streamlit cache clear

# 서비스 로딩 테스트
python -c "from src.core.service_factory import ServiceFactory; sf = ServiceFactory(); sf.validate_all_services()"
```

## 8. 도메인 분류 상세 가이드

가이드라인 문서([./structure_guidelines.md](./structure_guidelines.md))의 3.6절 참조

**빠른 분류 체크리스트**:
- [ ] 이미지/AI 분석 관련? → `analysis`
- [ ] 행정구역/위치 관련? → `district`
- [ ] 프롬프트/AI 텍스트 관련? → `prompts`
- [ ] 모니터링/알림 관련? → `monitoring`
- [ ] 시스템 지원/유틸리티? → `infrastructure`

**참고**: 현재 프로젝트에서는 3개 이상 도메인에서 공유하는 서비스가 없어 `common` 도메인을 사용하지 않습니다.

## 9. 산출물

### 9.1 최종 디렉터리 구조
- 도메인 기반으로 재구성된 `src/` 구조
- 기능별로 명확히 분리된 서비스/UI/타입

### 9.2 호환 계층
- `src/components/` 및 `src/services/`의 re-export wrapper
- ServiceFactory의 이중 경로 지원 (Phase 4까지)

### 9.3 문서
- 업데이트된 가이드라인 문서
- 리팩토링 로그 및 테스트 결과
- 후속 정리 작업 TODO 리스트

### 9.4 검증 결과
- 전체 테스트 통과 결과
- 성능 회귀 체크 결과
- 수동 기능 테스트 결과

## 10. 후속 계획

1. **래거시 wrapper 제거**: 모든 참조가 새 경로로 전환된 후 점진적 제거
2. **문서 업데이트**: 개발자 가이드 및 온보딩 문서 갱신
3. **성능 최적화**: 새 구조에서의 import 성능 최적화
4. **확장성 검증**: 새 기능 추가 시 배치 위치 명확성 확인

---

**📝 작성일**: 2025-09-22
**📋 버전**: v3 (최종)
**🎯 목표**: 안전하고 점진적인 도메인 기반 구조 전환