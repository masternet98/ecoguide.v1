# 소스 폴더 구조 직관성 개선 리팩토링 계획 (v2)

## 참고 문서
- [소스 구조 설계 가이드라인](./structure_guidelines.md)

## 1. 개요
- **목표**: `src/` 하위 모듈을 기능 중심으로 재배치해, 신규 인력도 코드 흐름을 빠르게 이해할 수 있도록 한다.
- **범위**: 디렉터리 구조 개편, 임포트 경로 수정, 래거시 경로 호환 레이어 구성. 비즈니스 로직 수정은 최소화한다.
- **원칙**: 가이드라인 문서를 준수하여 도메인별로 서비스·UI·타입을 묶고, 점진적 마이그레이션을 위해 호환 래퍼를 병행 유지한다.

## 2. 현행 구조 요약
```
src/
├─ components/   # Streamlit UI 및 도우미
├─ core/         # 앱 컨텍스트, 팩토리, 설정
├─ layouts/      # 공통 레이아웃
├─ pages/        # Streamlit 멀티 페이지
└─ services/     # 비즈니스 로직, 외부 API
```
- `services/`에 30개 이상 모듈이 집중되어 도메인 경계가 불분명하다.
- UI가 `components/` 루트에 혼재해 특정 기능에 속하는지 바로 파악하기 어렵다.
- `ServiceFactory`는 `src.services.*` 경로를 기준으로 동적 로딩한다.

## 3. 개선 방향 (가이드라인 반영)
1. `src/domains/<feature>/{services,ui,types.py}` 패턴으로 도메인 단위 그룹화.
2. 공통 서비스(`openai_service`, `prompt_service` 등)는 `src/domains/common/services`로 이동.
3. `src/app/` 계층을 도입해 핵심 팩토리·설정을 수용하고, 기존 `src/core/`는 호환 래퍼로 전환.
4. 기존 `src/components/`, `src/services/` 경로는 마이그레이션 동안 re-export 전용으로 유지.
5. `ServiceFactory` registry는 새 경로(`src.domains...`)를 1차 소스로 사용하되, 래거시 경로 fallback을 허용하지 않는다.

## 4. 목표 구조 개요
```
src/
├─ app/
│  ├─ core/
│  ├─ config/
│  └─ layouts/
├─ domains/
│  ├─ common/
│  │  ├─ services/
│  │  ├─ ui/
│  │  └─ types.py
│  ├─ analysis/
│  ├─ prompts/
│  ├─ district/
│  ├─ monitoring/
│  └─ infrastructure/
├─ components/ (래거시 래퍼)
└─ pages/
```

## 5. 실행 단계

### Phase 0: 정책 및 준비 (Day 0)
1. 가이드라인 문서 최종 검토 및 팀 합의.
2. 신규 디렉터리(`src/app`, `src/domains`, 하위 도메인 폴더) 생성 및 `__init__.py` 배치.
3. 코드 이동 전 `pytest -q`로 기준선 확인.

### Phase 1: 공통 서비스 마이그레이션 (Day 1)
1. `openai_service.py`, `prompt_service.py`, `vision_service.py` 등 다중 도메인에서 사용하는 파일을 `src/domains/common/services/`로 이동.
2. `ServiceFactory`의 `module_path`를 `src.domains.common.services.<module>`로 업데이트.
3. `src/services/`에는 `from src.domains.common.services.<module> import *` 형태의 래퍼 모듈 생성.
4. 관련 테스트·임포트 경로를 일괄 수정하고 `pytest -k service_factory -q` 등 핵심 테스트 실행.

### Phase 2: 도메인별 서비스 이동 (Day 1-2)
1. `district_*`, `monitoring_*`, `notification_*`, `search_*`, `location_*`, `batch_service.py` 등을 각 도메인 `services/` 폴더로 이동.
2. 이동 시 필요한 설정 객체(`Config`) 참조가 유지되는지 확인하고, 도메인 내부 `__all__`에 공개 API 기재.
3. `ServiceFactory` registry에 새 경로를 반영.
4. `src/services/`에 남긴 래퍼를 통해 기존 참조가 깨지지 않는지 확인.

### Phase 3: 도메인 UI 재배치 (Day 2-3)
1. `analysis`, `prompts`, `monitoring`, `district`, `infrastructure` 관련 컴포넌트를 `domains/<feature>/ui/`로 이동.
2. `src/components/`에는 동일 모듈명을 유지하면서 도메인 UI를 임포트하는 thin wrapper 작성.
3. 페이지·레이아웃에서 도메인 경로를 직접 사용하도록 순차 수정, 후속 MR에서는 래퍼를 제거할 계획을 명시.
4. 화면 별 수동 테스트(Check 페이지 진입 및 핵심 기능 실행) 수행.

### Phase 4: app 계층 정리 (Day 3-4)
1. `src/core/`, `src/layouts/` 내용을 `src/app/core`, `src/app/layouts`로 이동.
2. 설정 및 검증 모듈을 `src/app/config`로 재구성하고, `src/core/__init__.py` 등 기존 경로에는 re-export만 남긴다.
3. `app.py`, `pages/*.py` 등에서 새 경로를 참조하도록 수정.
4. 전체 테스트 및 `streamlit run app.py` 수동 기동으로 회귀 확인.

### Phase 5: 정리 및 추적 (Day 4-5)
1. 래거시 래퍼 사용처를 정리한 TODO 리스트 작성.
2. `components/`, `services/` 내 래퍼에 `deprecated` 주석을 추가하고 제거 계획을 문서화.
3. 불필요해진 빈 디렉터리·`__init__.py` 정리.
4. 최종 `pytest -q` 실행 후 결과를 기록.

## 6. 위험 요소와 대응 전략
- **ImportError 발생 위험**: 각 단계에서 `ServiceFactory` 경로를 함께 수정하고, 래퍼 모듈을 즉시 검증한다.
- **도메인 간 결합 증가**: 공통 로직이 발견되면 `domains/common`에 우선 배치하고, 직접 참조가 필요한 경우에는 가이드라인에 따라 공개 API를 추가한다.
- **Streamlit UI 깨짐**: 이동 직후 `streamlit run app_new.py`로 수동 확인하며, 필요한 경우 도메인 UI에만 존재하는 상태값을 재점검한다.

## 7. 산출물
- 업데이트된 디렉터리 구조 및 래퍼 모듈.
- 가이드라인 문서 변경 이력.
- 리팩토링 로그 및 테스트 결과.
- 후속 TODO 리스트(래퍼 제거, 문서 추가 등).

## 8. 커뮤니케이션
- 단계 완료 시마다 진행 단계를 기록한다.

---

## 9. 추가 검토 의견 (2025-09-22)

### 9.1 개선된 점들
✅ **구체적인 실행 단계**: Phase별 명확한 작업 범위와 검증 방법 제시
✅ **레거시 호환성**: re-export 방식의 wrapper를 통한 점진적 마이그레이션
✅ **도메인 기반 구조**: 비즈니스 도메인별 응집도 향상
✅ **ServiceFactory 연동**: 기존 DI 패턴과의 호환성 고려

### 9.2 주요 우려사항 및 개선 제안

#### ⚠️ **Phase 1의 위험성**
**문제**: 공통 서비스 이동이 너무 빠른 단계에서 진행됨
- `openai_service`, `prompt_service`, `vision_service`는 현재 많은 곳에서 참조됨
- ServiceFactory의 `module_path` 변경이 전체 시스템에 즉시 영향

**제안**: Phase 0.5 추가
```bash
Phase 0.5: 안전한 복사 시작 (Day 1)
1. domains/common/services/에 복사본 생성 (이동 아님)
2. ServiceFactory에 이중 경로 지원 추가
3. wrapper 모듈 생성 및 검증
4. 점진적으로 참조 변경 후 기존 경로 제거
```

#### ⚠️ **도메인 분류의 모호성**
**문제**: 일부 서비스의 도메인 소속이 불분명
- `batch_service.py`: infrastructure vs common?
- `file_source_validator.py`: 어느 도메인에 속할지 애매

**제안**: 도메인 분류 매트릭스
```markdown
## 도메인 분류 기준
- **analysis**: vision_service, openai_service, 이미지 관련 UI
- **district**: district_*, location_*
- **prompts**: prompt_*, AI 프롬프트 관련
- **monitoring**: monitoring_*, notification_*
- **infrastructure**: search_*, tunnel_*, batch_*, file_*
- **common**: 3개 이상 도메인에서 사용하는 서비스

분류 우선순위:
공통성 높음 → domains/common/
특정 도메인 전용 → domains/<domain>/
인프라/유틸리티 → domains/infrastructure/
```

#### ⚠️ **ServiceFactory 호환성 세부사항 부족**
**문제**: 현재 ServiceFactory의 동적 로딩 메커니즘과의 충돌 가능성

**제안**: Phase 0에 다음 추가
```python
# ServiceFactory 호환성 검증 스크립트 작성
def validate_service_loading():
    """기존 경로와 새 경로 모두에서 서비스 로딩 테스트"""
    # 의존성 체인 검증
    # 동적 로딩 메커니즘 확인
    pass
```

#### ⚠️ **실행 타임라인의 현실성**
**문제**: 5일 계획이 너무 빡빡함
- 27개 서비스 파일 + UI 컴포넌트 이동
- 각 단계별 테스트 및 검증 시간 부족

**제안**: 7-10일로 연장하거나 더 세분화된 단계 구성

### 9.3 구체적 개선 권장사항

#### A. 수정된 Phase 계획
```markdown
Phase 0: 준비 및 검증 (Day 0-1)
- 가이드라인 합의
- 새 디렉터리 구조 생성
- ServiceFactory 호환성 스크립트 작성
- 기준선 테스트 (pytest -v)

Phase 0.5: 안전한 복사 시작 (Day 1-2)
- 공통 서비스를 새 위치에 복사 (이동 아님)
- ServiceFactory에 이중 경로 지원 추가
- wrapper 모듈 생성 및 검증

Phase 1: 도메인별 서비스 이동 (Day 2-4)
- 독립성 높은 도메인부터 순차 이동
- 각 도메인별로 완전히 검증 후 다음 단계 진행
```

#### B. 추가 위험 완화 전략
```markdown
1. **롤백 계획**: 각 Phase별 롤백 시나리오 상세 기술
2. **점진적 검증**: 이동 후 즉시 관련 페이지/기능 수동 테스트
3. **의존성 매핑**: 사전에 서비스 간 의존성 그래프 작성
4. **Streamlit 캐시 클리어**: UI 변경 후 .streamlit/config.toml 확인
5. **백업 전략**: 각 단계 시작 전 git stash 또는 branch 생성
```

### 9.4 최종 평가

| 항목 | 점수 | 설명 |
|------|------|------|
| 구조 설계 | 9/10 | 도메인 기반 설계가 매우 우수 |
| 실행 가능성 | 7/10 | 일부 위험 요소 있으나 실행 가능 |
| 호환성 고려 | 8/10 | wrapper 방식이 적절함 |
| 리스크 관리 | 6/10 | 추가 완화 전략 필요 |

**종합 의견**: 전반적으로 잘 설계된 계획이지만, **Phase 1의 속도 조절**과 **더 상세한 위험 관리**가 필요합니다. 특히 ServiceFactory 변경 부분에서 신중한 접근이 권장됩니다.

### 9.5 다음 단계 권장사항
1. **Phase 0.5 추가**: 안전한 복사 단계를 통한 점진적 마이그레이션
2. **도메인 분류 가이드 구체화**: 애매한 서비스들의 명확한 배치 기준 수립
3. **타임라인 조정**: 현실적인 일정으로 재조정 (7-10일)
4. **검증 스크립트 작성**: ServiceFactory 호환성 및 의존성 검증 도구 개발
