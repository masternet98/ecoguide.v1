# 리스크 분석 및 대응 방안

## 🚨 주요 리스크 요소 분석

### 1. 높은 위험도 (Critical) 🔴

#### 1.1 순환 Import (Circular Import)
**위험도**: 🔴 Critical
**발생 가능성**: 중간
**영향도**: 앱 실행 불가

**상황**:
- `district_loader.py`에서 `district_validator.py`의 `_normalize_admin_field` import
- `district_api.py`에서 모든 모듈 import
- 모듈 간 상호 의존성 발생 가능

**대응 방안**:
```python
# ✅ 해결책 1: 지연 Import (Lazy Import)
def process_district_csv(...):
    from .district_validator import _normalize_admin_field  # 함수 내부에서 import
    return _normalize_admin_field(...)

# ✅ 해결책 2: 공통 유틸리티 분리
# district_utils.py 생성하여 공통 함수 배치

# ✅ 해결책 3: 엄격한 의존성 방향 설정
# validator ← cache ← loader ← api (단방향만 허용)
```

#### 1.2 기존 코드 호환성 파괴
**위험도**: 🔴 Critical
**발생 가능성**: 높음
**영향도**: 전체 앱 오류

**상황**:
- `pages/01_district_config.py`에서 직접 함수 import
- `src/services/location_service.py`에서 지연 import 사용
- Service Factory에서 모듈 경로 의존

**대응 방안**:
```python
# ✅ 해결책: 기존 district_service.py 유지 + 내용 교체
# 1. 새로운 모듈들 생성
# 2. district_service.py 내용을 모든 함수 re-export로 교체
# 3. 기존 import 구문 100% 호환성 유지

# district_service.py (교체 후)
from .district_api import *  # 모든 함수 re-export
```

### 2. 중간 위험도 (High) 🟠

#### 2.1 함수 이동 시 의존성 누락
**위험도**: 🟠 High
**발생 가능성**: 높음
**영향도**: 특정 기능 오류

**상황**:
- 함수 이동 시 필요한 import 누락
- 헬퍼 함수나 상수 이동 누락
- 내부 함수 호출 관계 파악 누락

**대응 방안**:
```bash
# ✅ 단계별 검증 프로세스
# 1. 함수 이동 후 즉시 문법 체크
python -m py_compile src/services/new_module.py

# 2. Import 테스트
python -c "from src.services.new_module import function_name"

# 3. 함수 실행 테스트 (간단한 호출)
```

#### 2.2 설정 의존성 문제
**위험도**: 🟠 High
**발생 가능성**: 중간
**영향도**: 기본값 작동 불가

**상황**:
- 모든 함수가 `DistrictConfig` 의존
- 설정 기본값 처리 누락
- 설정 검증 로직 분산

**대응 방안**:
```python
# ✅ 일관된 설정 처리 패턴
def function_name(config: Optional[DistrictConfig] = None):
    config = config or DistrictConfig()  # 항상 기본값 제공
    # 함수 로직...
```

### 3. 낮은 위험도 (Medium) 🟡

#### 3.1 성능 저하
**위험도**: 🟡 Medium
**발생 가능성**: 낮음
**영향도**: 앱 속도 저하

**상황**:
- 모듈 분리로 인한 import 오버헤드
- 함수 호출 체인 증가
- 메모리 사용량 증가

**대응 방안**:
```python
# ✅ 성능 최적화 방법
# 1. 지연 import로 필요시에만 로딩
# 2. 자주 사용되는 함수는 캐싱
# 3. 불필요한 중간 호출 제거
```

#### 3.2 로깅 분산
**위험도**: 🟡 Medium
**발생 가능성**: 중간
**영향도**: 디버깅 어려움

**상황**:
- 여러 모듈에 로깅 코드 분산
- 로그 메시지 일관성 부족
- 에러 추적 어려움

**대응 방안**:
```python
# ✅ 일관된 로깅 패턴
# 각 모듈마다 동일한 로깅 import
from src.core.logger import logger, log_info, log_warning, log_error

# 모듈명 포함한 로그 메시지
log_info(f"[district_loader] CSV 파싱 시작: {filename}")
```

## 🛡️ 단계별 리스크 완화 계획

### Phase 1: district_validator.py (가장 안전)
**리스크**: 최소 (독립적 유틸리티 함수)
**대응**:
- 외부 의존성 최소화
- 순수 함수로만 구성
- 즉시 단위 테스트 가능

### Phase 2: district_cache.py (안전)
**리스크**: 낮음 (파일 시스템 의존성만 있음)
**대응**:
- 파일 시스템 에러 처리 강화
- 기본값 제공으로 안전성 확보

### Phase 3: district_loader.py (중간 위험)
**리스크**: 중간 (복잡한 로직, 외부 API 의존)
**대응**:
- 단계별 함수 이동 (1-2개씩)
- 각 함수마다 즉시 테스트
- 백업에서 즉시 복원 가능 상태 유지

### Phase 4: district_api.py (위험)
**리스크**: 높음 (모든 모듈 통합, 기존 호환성)
**대응**:
- 모든 함수 재export 확인
- 전체 앱 테스트 필수
- 롤백 계획 준비

## 🚨 응급 상황 대응 절차

### Level 1: 문법 오류 (즉시 해결 가능)
```bash
# 증상: Python 문법 오류
# 대응: 백업에서 해당 파일 복원
cp src/services/filename.py.backup src/services/filename.py
```

### Level 2: Import 오류 (5분 내 해결)
```bash
# 증상: ModuleNotFoundError, ImportError
# 대응 1: 누락된 import 추가
# 대응 2: __init__.py 파일 확인
touch src/services/__init__.py

# 대응 3: 파일 복원
cp src/services/filename.py.backup src/services/filename.py
```

### Level 3: 앱 실행 오류 (즉시 복원)
```bash
# 증상: Streamlit 앱이 실행되지 않음
# 대응: 전체 롤백
git reset --hard HEAD~1

# 또는 특정 변경사항만 롤백
git checkout HEAD -- src/services/
```

### Level 4: 기능 오류 (점진적 복원)
```bash
# 증상: 앱은 실행되지만 특정 기능 오류
# 대응 1: 해당 모듈만 백업에서 복원
# 대응 2: 함수별로 점진적 롤백
# 대응 3: 문제 함수만 임시로 원본에서 복사
```

## 📊 리스크 모니터링 체크리스트

### 매 단계 후 확인사항
- [ ] **문법 체크**: `python -m py_compile` 통과
- [ ] **Import 체크**: `python -c "import module"` 성공
- [ ] **앱 실행**: `streamlit run app.py` 정상 로딩
- [ ] **기본 기능**: 메인 페이지 정상 동작
- [ ] **관련 페이지**: 행정구역 페이지 정상 동작

### 일일 종료 전 확인사항
- [ ] **전체 기능 테스트**: 모든 주요 페이지 동작 확인
- [ ] **에러 로그**: 새로운 에러나 경고 없음
- [ ] **Git 상태**: 안전한 상태로 커밋 완료
- [ ] **백업 확인**: `.backup` 파일들 최신 상태 유지

## 🎯 성공 지표 및 중단 기준

### 성공 지표
- ✅ 모든 기능 100% 정상 동작
- ✅ 앱 시작 시간 2분 이내 유지
- ✅ 새로운 에러 또는 경고 0개
- ✅ 기존 import 구문 100% 호환

### 중단 기준 (즉시 롤백)
- ❌ 앱이 실행되지 않음
- ❌ 핵심 기능 오류 (행정구역 데이터 로딩 실패)
- ❌ 복구에 1시간 이상 소요 예상
- ❌ 순환 import로 인한 구조적 문제

## 📝 리스크 학습 및 개선

### 발생한 문제 기록 양식
```markdown
## 문제 발생 보고서
- **날짜**: YYYY-MM-DD
- **단계**: Phase X
- **문제 유형**: Import 오류 / 문법 오류 / 기능 오류
- **증상**: 구체적인 에러 메시지
- **원인**: 근본 원인 분석
- **해결 방법**: 적용한 해결책
- **소요 시간**: X분
- **예방 방법**: 향후 동일 문제 방지책
```

### 위험 요소 업데이트
매일 작업 후 새로 발견된 위험 요소나 대응 방법을 이 문서에 추가하여 지속적으로 개선합니다.

---

**결론**: 리스크는 존재하지만 모든 주요 위험 요소에 대한 대응 방안이 준비되어 있으며, 단계별 안전 장치와 즉시 롤백 가능한 백업 시스템으로 안전하게 진행할 수 있습니다.