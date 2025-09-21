# 1주차 상세 실행 계획 - district_service.py 리팩토링

## 📅 일정 개요
- **기간**: 2025-09-21 ~ 2025-09-27 (7일)
- **목표**: district_service.py (2,217줄) → 4개 파일로 안전하게 분해
- **원칙**: 기존 기능 100% 보존, 프로그램 오류 절대 금지

---

## 🔍 Day 1 (2025-09-21): 분석 및 계획 수립

### 🎯 목표
district_service.py 파일을 완전히 이해하고 분해 전략 수립

### 📋 상세 작업 목록

#### 1. 현재 상태 백업 및 확인
```bash
# 1.1 Git 백업
git add .
git commit -m "리팩토링 1주차 시작 - district_service.py 분해 전 백업"

# 1.2 파일 백업
cp src/services/district_service.py src/services/district_service.py.backup

# 1.3 현재 앱 정상 동작 확인
streamlit run app.py
# → 메인 페이지 로딩 확인
# → 02_district_config.py 페이지 정상 동작 확인
# → 오류 없이 데이터 로딩되는지 확인
```

#### 2. district_service.py 파일 분석
```python
# 2.1 파일 구조 파악
# - 전체 라인 수: 2,217줄
# - 클래스 개수 및 이름
# - 주요 메서드 목록
# - import 의존성

# 2.2 기능별 그룹핑
# - 데이터 로딩 관련 함수들
# - 캐시 관리 관련 함수들
# - 데이터 검증 관련 함수들
# - 외부 API 인터페이스 함수들
```

#### 3. 분해 계획 문서 작성
`instructions/district-service-breakdown-plan.md` 파일 생성:
- 각 새 파일의 책임 범위
- 함수별 이동 계획
- import 구조 설계
- 기존 코드 호환성 유지 방법

#### 4. 리스크 분석
- 다른 파일에서 district_service를 사용하는 곳 식별
- 순환 import 가능성 검토
- 테스트 시나리오 작성

### ✅ Day 1 완료 체크리스트
- [ ] Git 백업 완료
- [ ] 파일 백업 완료
- [ ] 현재 앱 정상 동작 확인
- [ ] district_service.py 구조 분석 완료
- [ ] 분해 계획 문서 작성 완료
- [ ] 리스크 분석 완료
- [ ] 내일 작업 계획 확정

---

## 🏗️ Day 2 (2025-09-22): district_loader.py 생성

### 🎯 목표
데이터 로딩 관련 기능을 독립적인 모듈로 분리

### 📋 상세 작업 목록

#### 1. 작업 전 백업
```bash
git add .
git commit -m "Day 2 시작 - district_loader.py 생성 전 백업"
```

#### 2. district_loader.py 파일 생성
```python
# 2.1 기본 구조 생성
"""
src/services/district_loader.py

담당 기능:
- data.go.kr에서 행정구역 데이터 다운로드
- CSV 파일 파싱
- JSON 형식으로 변환
- 파일 시스템 관리
"""

# 2.2 이동할 함수들 (예상)
# - download_district_data()
# - parse_csv_data()
# - convert_to_json()
# - save_district_file()
# - load_district_file()
```

#### 3. 함수 이동 및 구현
```python
# 3.1 하나씩 단계적으로 이동
# Step 1: download_district_data 함수 이동
# Step 2: 관련 헬퍼 함수들 이동
# Step 3: import 구문 정리
# Step 4: 테스트 실행

# 3.2 각 단계마다 확인
python -m py_compile src/services/district_loader.py
```

#### 4. 간단한 테스트 작성
```python
# 4.1 테스트 파일 생성 (선택사항)
# test/test_district_loader.py

# 4.2 기본 동작 테스트
# - 파일 로딩 테스트
# - 데이터 파싱 테스트
```

### ✅ Day 2 완료 체크리스트
- [ ] district_loader.py 파일 생성
- [ ] 데이터 로딩 함수들 이동 완료
- [ ] 문법 오류 없음 확인
- [ ] 기본 동작 테스트 통과
- [ ] Git 커밋 완료
- [ ] 전체 앱 정상 동작 확인

---

## 📦 Day 3 (2025-09-23): district_cache.py 생성

### 🎯 목표
캐시 관리 관련 기능을 독립 모듈로 분리

### 📋 상세 작업 목록

#### 1. 작업 전 확인
```bash
# 1.1 어제 작업 결과 확인
streamlit run app.py
# → 행정구역 관련 기능 정상 동작 확인

# 1.2 백업
git add .
git commit -m "Day 3 시작 - district_cache.py 생성 전 백업"
```

#### 2. district_cache.py 파일 생성
```python
# 2.1 담당 기능 정의
"""
src/services/district_cache.py

담당 기능:
- 메모리 캐시 관리
- 파일 캐시 관리
- 캐시 무효화 정책
- 캐시 성능 최적화
"""

# 2.2 이동할 함수들
# - setup_cache()
# - get_cached_data()
# - set_cache_data()
# - invalidate_cache()
# - cache_cleanup()
```

#### 3. 함수 이동 및 테스트
```python
# 3.1 단계적 이동
# Step 1: 캐시 설정 함수들
# Step 2: 캐시 읽기/쓰기 함수들
# Step 3: 캐시 관리 함수들
# Step 4: 각 단계마다 테스트

# 3.2 의존성 확인
# - district_loader와의 연결점 확인
# - 순환 import 방지
```

### ✅ Day 3 완료 체크리스트
- [ ] district_cache.py 파일 생성
- [ ] 캐시 관련 함수들 이동 완료
- [ ] district_loader와 연동 확인
- [ ] 메모리 캐시 동작 테스트
- [ ] 파일 캐시 동작 테스트
- [ ] Git 커밋 완료

---

## 🔍 Day 4 (2025-09-24): district_validator.py 생성

### 🎯 목표
데이터 검증 관련 기능을 독립 모듈로 분리

### 📋 상세 작업 목록

#### 1. district_validator.py 파일 생성
```python
# 1.1 담당 기능 정의
"""
src/services/district_validator.py

담당 기능:
- 행정구역 데이터 무결성 검증
- 데이터 형식 검증
- 중복 데이터 체크
- 에러 처리 및 복구
"""

# 1.2 이동할 함수들
# - validate_district_data()
# - check_data_integrity()
# - validate_format()
# - handle_validation_errors()
```

#### 2. 함수 이동 및 구현
```python
# 2.1 검증 로직 이동
# 2.2 에러 처리 로직 이동
# 2.3 데이터 복구 로직 이동
```

#### 3. 통합 테스트
```python
# 3.1 3개 모듈 간 연동 테스트
# district_loader → district_validator → district_cache
```

### ✅ Day 4 완료 체크리스트
- [ ] district_validator.py 파일 생성
- [ ] 검증 관련 함수들 이동 완료
- [ ] 3개 모듈 간 연동 테스트 통과
- [ ] 에러 처리 로직 정상 동작
- [ ] Git 커밋 완료

---

## 🔗 Day 5 (2025-09-25): district_api.py 생성 및 통합

### 🎯 목표
기존 인터페이스를 유지하면서 4개 모듈을 통합하는 API 레이어 생성

### 📋 상세 작업 목록

#### 1. district_api.py 파일 생성
```python
# 1.1 담당 기능 정의
"""
src/services/district_api.py

담당 기능:
- 기존 district_service.py의 public 인터페이스 유지
- 4개 모듈의 조합 및 오케스트레이션
- 외부 호출자를 위한 단일 진입점
- 하위 호환성 보장
"""

# 1.2 구조 설계
class DistrictService:
    def __init__(self):
        self.loader = DistrictLoader()
        self.cache = DistrictCache()
        self.validator = DistrictValidator()

    # 기존 public 메서드들 유지
```

#### 2. 기존 district_service.py 정리
```python
# 2.1 이동된 코드 제거
# 2.2 필요시 district_api.py로 import 변경
# 2.3 또는 district_service.py를 district_api.py로 완전 교체
```

#### 3. 전체 통합 테스트
```bash
# 3.1 앱 전체 실행 테스트
streamlit run app.py

# 3.2 행정구역 관련 모든 기능 테스트
# - 데이터 다운로드
# - 캐시 동작
# - 검증 기능
# - 에러 처리
```

### ✅ Day 5 완료 체크리스트
- [ ] district_api.py 파일 생성
- [ ] 기존 public 인터페이스 100% 유지
- [ ] 4개 모듈 통합 완료
- [ ] 전체 앱 정상 동작 확인
- [ ] 행정구역 관련 모든 기능 정상 동작
- [ ] Git 커밋 완료

---

## 🖥️ Day 6 (2025-09-26): monitoring_ui.py 분해 시작

### 🎯 목표
monitoring_ui.py (1,129줄)를 3개 파일로 분해 시작

### 📋 상세 작업 목록

#### 1. 분석 및 백업
```bash
# 1.1 백업
cp src/components/monitoring_ui.py src/components/monitoring_ui.py.backup

# 1.2 파일 구조 분석
# - UI 컴포넌트 부분 식별
# - 데이터 처리 로직 부분 식별
# - 차트 렌더링 부분 식별
```

#### 2. monitoring_dashboard.py 생성
```python
# 2.1 UI 컴포넌트 부분 이동
# - Streamlit UI 요소들
# - 레이아웃 관련 코드
# - 사용자 인터페이스 로직
```

### ✅ Day 6 완료 체크리스트
- [ ] monitoring_ui.py 분석 완료
- [ ] monitoring_dashboard.py 생성
- [ ] UI 컴포넌트 부분 이동 완료
- [ ] 모니터링 페이지 정상 동작 확인

---

## 📊 Day 7 (2025-09-27): monitoring_ui.py 분해 완료

### 🎯 목표
monitoring_ui.py 분해 완료 및 1주차 전체 검증

### 📋 상세 작업 목록

#### 1. 나머지 파일들 생성
```python
# 1.1 monitoring_data.py 생성
# - 데이터 처리 로직
# - 비즈니스 로직

# 1.2 monitoring_charts.py 생성
# - 차트 렌더링 로직
# - 시각화 관련 코드
```

#### 2. 1주차 전체 검증
```bash
# 2.1 모든 페이지 동작 확인
streamlit run app.py
# → 모든 페이지 정상 로딩 확인
# → 주요 기능들 정상 동작 확인

# 2.2 성능 확인
# → 앱 시작 시간 2분 이내 유지
# → 기존 대비 성능 저하 없음
```

#### 3. 1주차 완료 문서화
```markdown
# 1주차 완료 보고서 작성
- 분해된 파일 목록
- 라인 수 변화
- 기능별 테스트 결과
- 발견된 이슈 및 해결방법
```

### ✅ Day 7 완료 체크리스트
- [ ] monitoring_data.py 생성 완료
- [ ] monitoring_charts.py 생성 완료
- [ ] 모니터링 페이지 완전 정상 동작
- [ ] 전체 앱 모든 기능 정상 동작
- [ ] 1주차 완료 보고서 작성
- [ ] Git 커밋 및 태그: `git tag week1-complete`

---

## 🎯 1주차 성공 기준

### 정량적 목표
- [ ] `district_service.py` 2,217줄 → 4개 파일 각각 500줄 이하
- [ ] `monitoring_ui.py` 1,129줄 → 3개 파일 각각 400줄 이하
- [ ] 전체 앱 시작 시간 2분 이내 유지
- [ ] 모든 기존 기능 100% 정상 동작

### 정성적 목표
- [ ] 코드 가독성 향상 (파일당 기능 명확화)
- [ ] 새로운 에러나 경고 0개
- [ ] 기능별 책임 분리 명확화
- [ ] 향후 유지보수 편의성 개선

---

## 🚨 주의사항

### 절대 금지사항
- ❌ 여러 파일을 동시에 수정
- ❌ 기존 public 인터페이스 변경
- ❌ 의존성 구조 대폭 변경
- ❌ 테스트 없이 큰 변경사항 적용

### 필수 준수사항
- ✅ 매 변경 후 즉시 앱 실행 테스트
- ✅ 하루 종료 전 전체 기능 동작 확인
- ✅ 문제 발생 시 즉시 백업에서 복원
- ✅ 매일 Git 커밋으로 진행사항 백업

---

**작성일**: 2025-09-21
**실행 기간**: 2025-09-21 ~ 2025-09-27
**담당자**: 1인 개발자
**검토 주기**: 매일 종료 시점