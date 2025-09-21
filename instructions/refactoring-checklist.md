# 안전한 리팩토링 체크리스트

## 🚨 필수 안전 조치 (매 변경마다)

### 변경 전 체크리스트
- [ ] 현재 프로그램이 정상 동작하는지 확인
- [ ] `streamlit run app.py` 실행하여 메인 페이지 로딩 확인
- [ ] 주요 페이지 3-4개 정상 동작 확인
- [ ] Git 커밋으로 현재 상태 백업: `git add . && git commit -m "리팩토링 전 백업"`
- [ ] 변경할 파일의 `.backup` 복사본 생성
- [ ] 변경 계획 문서화 (어떤 함수를 어느 파일로 옮길지)

### 변경 중 체크리스트
- [ ] **한 번에 하나의 파일만** 수정
- [ ] 새 파일 생성 시 기본 import 구조 작성
- [ ] 함수 이동 시 의존성 import 같이 이동
- [ ] 변경 후 즉시 Python 문법 오류 체크: `python -m py_compile src/services/new_file.py`
- [ ] 변경 후 즉시 앱 실행 테스트 (메인 페이지만)

### 변경 후 체크리스트
- [ ] 전체 앱 실행: `streamlit run app.py`
- [ ] 메인 페이지 정상 로딩 확인
- [ ] 변경된 기능과 관련된 페이지 동작 확인
- [ ] 에러 로그 확인 (빨간색 에러 메시지 없어야 함)
- [ ] 기존 기능들이 여전히 작동하는지 확인
- [ ] 정상 동작 확인 후 Git 커밋: `git add . && git commit -m "기능명 리팩토링 완료"`

---

## 📋 1주차 실행 체크리스트

### Day 1: district_service.py 분석
- [ ] **시작 전 백업**
  - [ ] `git add . && git commit -m "Day 1 시작 전 백업"`
  - [ ] `cp src/services/district_service.py src/services/district_service.py.backup`

- [ ] **파일 분석**
  - [ ] `district_service.py` 파일 열어서 전체 구조 파악
  - [ ] 클래스와 주요 메서드 목록 작성
  - [ ] 각 메서드가 하는 일 간단히 정리
  - [ ] 외부에서 호출하는 public 메서드 식별

- [ ] **분해 계획 수립**
  - [ ] 4개 파일로 분해할 기능 그룹 정의
  - [ ] 각 새 파일의 책임 범위 명시
  - [ ] import 관계 설계
  - [ ] 기존 코드를 깨뜨리지 않을 방법 계획

### Day 2: district_loader.py 생성
- [ ] **파일 생성**
  - [ ] `src/services/district_loader.py` 생성
  - [ ] 기본 import 구조 작성
  - [ ] 데이터 로딩 관련 함수들만 이동

- [ ] **기능 이동**
  - [ ] 데이터 다운로드 관련 함수 이동
  - [ ] CSV 파싱 관련 함수 이동
  - [ ] JSON 변환 관련 함수 이동
  - [ ] 필요한 import 문 추가

- [ ] **테스트**
  - [ ] `python -m py_compile src/services/district_loader.py` 실행
  - [ ] 문법 오류 없는지 확인
  - [ ] 간단한 테스트 함수 작성하여 동작 확인

### Day 3: district_cache.py 및 district_validator.py 생성
- [ ] **district_cache.py 생성**
  - [ ] 캐시 관리 관련 함수들 이동
  - [ ] 메모리 캐시, 파일 캐시 로직 이동
  - [ ] 캐시 무효화 로직 이동

- [ ] **district_validator.py 생성**
  - [ ] 데이터 검증 관련 함수들 이동
  - [ ] 무결성 체크 로직 이동
  - [ ] 에러 처리 함수들 이동

- [ ] **각각 테스트**
  - [ ] 개별 파일 문법 오류 체크
  - [ ] 간단한 동작 테스트

### Day 4: district_api.py 생성 및 통합
- [ ] **district_api.py 생성**
  - [ ] 기존 district_service.py의 public 인터페이스 유지
  - [ ] 다른 3개 파일의 기능들을 조합하는 래퍼 클래스 생성
  - [ ] 기존 import 구조를 깨뜨리지 않도록 설계

- [ ] **기존 파일 정리**
  - [ ] district_service.py에서 이동된 코드들 제거
  - [ ] 필요하면 district_api.py로 import 구조 변경

- [ ] **전체 통합 테스트**
  - [ ] `streamlit run app.py` 실행
  - [ ] 행정구역 관련 페이지 정상 동작 확인
  - [ ] 데이터 로딩, 캐시, 검증 모든 기능 동작 확인

### Day 5: monitoring_ui.py 분해
- [ ] **백업 및 분석**
  - [ ] `cp src/components/monitoring_ui.py src/components/monitoring_ui.py.backup`
  - [ ] 파일 구조 분석 및 분해 계획 수립

- [ ] **3개 파일로 분해**
  - [ ] `monitoring_dashboard.py` (UI 컴포넌트)
  - [ ] `monitoring_data.py` (데이터 처리)
  - [ ] `monitoring_charts.py` (차트 렌더링)

- [ ] **모니터링 페이지 테스트**
  - [ ] 03_district_monitoring.py 페이지 정상 동작 확인
  - [ ] 모든 차트와 대시보드 요소 정상 표시 확인

---

## 🆘 응급 복구 가이드

### 문제 발생 시 즉시 실행할 명령어

#### 1. 파일 단위 복구
```bash
# 백업에서 특정 파일 복원
cp src/services/filename.py.backup src/services/filename.py

# Git에서 특정 파일 복원
git checkout HEAD -- src/services/filename.py
```

#### 2. 전체 복구 (심각한 문제 발생 시)
```bash
# 마지막 커밋으로 전체 복원
git reset --hard HEAD

# 특정 커밋으로 복원 (커밋 ID 확인 후)
git log --oneline  # 커밋 목록 보기
git reset --hard [커밋ID]
```

#### 3. 앱이 실행되지 않을 때
1. **Python 문법 오류 확인**
   ```bash
   python -m py_compile src/services/*.py
   python -m py_compile src/components/*.py
   ```

2. **Import 오류 확인**
   ```bash
   python -c "import src.services.district_service"
   python -c "import src.components.monitoring_ui"
   ```

3. **Streamlit 실행 시 오류 확인**
   ```bash
   streamlit run app.py 2>&1 | grep -i error
   ```

### 문제별 대응 방법

#### Import 오류가 발생할 때
- [ ] 새로 생성한 파일에 `__init__.py` 추가했는지 확인
- [ ] 상대 import 경로가 올바른지 확인
- [ ] 순환 import가 발생하지 않았는지 확인

#### 함수를 찾을 수 없다는 오류가 발생할 때
- [ ] 함수가 올바른 파일로 이동했는지 확인
- [ ] 함수 이름이 변경되지 않았는지 확인
- [ ] 해당 함수를 import하는 부분이 업데이트되었는지 확인

#### Streamlit 페이지가 로딩되지 않을 때
- [ ] 페이지에서 사용하는 컴포넌트가 올바르게 import되는지 확인
- [ ] 컴포넌트의 생성자나 메서드 시그니처가 변경되지 않았는지 확인

---

## 🎯 매일 종료 전 체크리스트

### 작업 종료 전 필수 확인사항
- [ ] 전체 앱이 정상적으로 실행되는가?
- [ ] 오늘 변경한 기능이 정상 동작하는가?
- [ ] 기존 기능들이 여전히 작동하는가?
- [ ] 새로운 에러나 경고가 발생하지 않는가?
- [ ] Git 커밋으로 오늘 작업 내용 저장했는가?

### 다음날 작업 준비
- [ ] 내일 작업할 파일 및 기능 확인
- [ ] 예상되는 리스크 요소 점검
- [ ] 필요한 백업 파일 준비

---

**⚠️ 중요 알림**:
- 절대로 여러 파일을 동시에 수정하지 마세요
- 변경 후 반드시 즉시 테스트하세요
- 문제 발생 시 즉시 백업에서 복원하세요
- 하루에 너무 많은 변경을 시도하지 마세요