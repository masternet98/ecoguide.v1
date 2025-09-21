# 안전 백업 및 복구 가이드

## 🛡️ 백업 전략

### 1. 다중 백업 시스템
프로그램 오류를 절대 방지하기 위해 3단계 백업 시스템을 운영합니다.

#### Level 1: Git 백업 (가장 안전)
```bash
# 매일 작업 시작 전
git add .
git commit -m "Day X 작업 시작 전 백업"

# 각 파일 수정 완료 후
git add .
git commit -m "파일명 리팩토링 완료"

# 중요한 마일스톤
git tag week1-day1-complete
git tag week1-complete
```

#### Level 2: 파일 단위 백업
```bash
# 수정 전 개별 파일 백업
cp src/services/district_service.py src/services/district_service.py.backup
cp src/components/monitoring_ui.py src/components/monitoring_ui.py.backup

# 전체 폴더 백업 (중요한 변경 전)
cp -r src/services src/services.backup
cp -r src/components src/components.backup
```

#### Level 3: 프로젝트 전체 백업 (주간 단위)
```bash
# 프로젝트 루트에서 실행
cd ..
tar -czf ecoguide.v1.backup.$(date +%Y%m%d).tar.gz ecoguide.v1/
```

### 2. 백업 스케줄

#### 매일 백업
- **작업 시작 전**: Git 커밋
- **파일 수정 전**: 개별 파일 `.backup` 생성
- **파일 수정 후**: Git 커밋
- **작업 종료 전**: 전체 기능 테스트 후 Git 커밋

#### 주간 백업
- **매주 금요일**: 프로젝트 전체 압축 백업
- **각 주차 완료 시**: Git 태그 생성

---

## 🚨 응급 복구 절차

### 상황별 복구 방법

#### 🔥 심각: 앱이 실행되지 않음
```bash
# 1단계: 마지막 정상 상태로 즉시 복원
git log --oneline -5  # 최근 커밋 5개 확인
git reset --hard HEAD~1  # 바로 이전 커밋으로 복원

# 2단계: 앱 실행 테스트
streamlit run app.py

# 3단계: 여전히 안되면 더 이전 커밋으로
git reset --hard HEAD~2
```

#### 🟠 중간: 특정 기능이 동작하지 않음
```bash
# 1단계: 해당 파일만 복원
git checkout HEAD -- src/services/파일명.py

# 2단계: 백업 파일에서 복원
cp src/services/파일명.py.backup src/services/파일명.py

# 3단계: 앱 실행 테스트
streamlit run app.py
```

#### 🟡 경미: 문법 오류나 import 오류
```bash
# 1단계: Python 문법 체크
python -m py_compile src/services/파일명.py

# 2단계: import 오류 확인
python -c "import src.services.파일명"

# 3단계: 해당 부분만 수정하거나 백업에서 복원
```

### 복구 우선순위
1. **앱 실행 가능성 확보** (1순위)
2. **기존 기능 정상 동작** (2순위)
3. **신규 기능 추가** (3순위)

---

## 📋 매일 안전 체크리스트

### 작업 시작 전 체크리스트
- [ ] **현재 앱이 정상 실행되는가?**
  ```bash
  streamlit run app.py
  ```
- [ ] **어제 작업한 기능이 정상 동작하는가?**
- [ ] **Git 상태가 깨끗한가?**
  ```bash
  git status
  ```
- [ ] **백업이 준비되어 있는가?**
  ```bash
  git add . && git commit -m "작업 시작 전 백업"
  ```

### 파일 수정 전 체크리스트
- [ ] **수정할 파일의 현재 상태가 정상인가?**
- [ ] **개별 파일 백업을 생성했는가?**
  ```bash
  cp src/services/파일명.py src/services/파일명.py.backup
  ```
- [ ] **수정 계획이 명확한가?** (어떤 함수를 어느 파일로 옮길지)
- [ ] **예상되는 import 변경사항을 파악했는가?**

### 파일 수정 후 체크리스트
- [ ] **Python 문법 오류가 없는가?**
  ```bash
  python -m py_compile src/services/새파일.py
  ```
- [ ] **import 오류가 없는가?**
  ```bash
  python -c "import src.services.새파일"
  ```
- [ ] **앱이 정상 실행되는가?**
  ```bash
  streamlit run app.py
  ```
- [ ] **수정한 기능이 정상 동작하는가?**
- [ ] **기존 기능들이 여전히 동작하는가?**

### 작업 종료 전 체크리스트
- [ ] **전체 앱이 정상적으로 실행되는가?**
- [ ] **모든 페이지가 로딩되는가?**
- [ ] **주요 기능 3-4개가 정상 동작하는가?**
- [ ] **새로운 에러나 경고가 없는가?**
- [ ] **Git 커밋으로 작업 내용을 저장했는가?**
  ```bash
  git add . && git commit -m "Day X 작업 완료"
  ```

---

## 🔧 문제 해결 가이드

### 자주 발생하는 문제와 해결책

#### 1. ImportError 발생
```
ModuleNotFoundError: No module named 'src.services.새파일'
```

**해결책**:
```bash
# 1. __init__.py 파일 확인
touch src/services/__init__.py

# 2. import 경로 확인
# 상대 import: from .새파일 import 함수명
# 절대 import: from src.services.새파일 import 함수명

# 3. Python 경로 확인
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 2. 함수를 찾을 수 없음
```
AttributeError: module has no attribute '함수명'
```

**해결책**:
```python
# 1. 함수가 올바른 파일에 있는지 확인
# 2. 함수명이 변경되지 않았는지 확인
# 3. import 구문이 업데이트되었는지 확인

# 백업에서 확인
grep -n "함수명" src/services/파일명.py.backup
```

#### 3. Streamlit 페이지 오류
```
StreamlitAPIException: st.sidebar only works in the main Streamlit app
```

**해결책**:
```python
# 1. 컴포넌트 구조 확인
# 2. 상태 관리 코드 확인
# 3. 백업에서 정상 동작하던 코드 비교

# 즉시 복원
cp src/components/파일명.py.backup src/components/파일명.py
```

#### 4. 순환 import 오류
```
ImportError: cannot import name '함수명' from partially initialized module
```

**해결책**:
```python
# 1. import 구조 재설계
# 2. 지연 import 사용: from . import 모듈명 (함수 내부에서)
# 3. 공통 모듈로 추출

# 임시 해결: 백업 복원
git checkout HEAD -- src/services/
```

---

## 🎯 안전 수칙

### 절대 원칙 (NEVER)
1. **❌ 절대로 여러 파일을 동시에 수정하지 마세요**
2. **❌ 절대로 백업 없이 큰 변경을 하지 마세요**
3. **❌ 절대로 테스트 없이 커밋하지 마세요**
4. **❌ 절대로 에러가 있는 상태로 하루를 마무리하지 마세요**

### 항상 원칙 (ALWAYS)
1. **✅ 항상 변경 전에 백업하세요**
2. **✅ 항상 변경 후에 즉시 테스트하세요**
3. **✅ 항상 문제 발생 시 즉시 복원하세요**
4. **✅ 항상 작업 종료 전에 전체 확인하세요**

### 의심 원칙 (WHEN IN DOUBT)
- 확신이 없으면 → **백업에서 복원**
- 복잡해 보이면 → **작은 단위로 나누어 진행**
- 시간이 오래 걸리면 → **일단 백업 상태로 복원 후 계획 재수립**

---

## 📞 응급 상황 대응

### 즉시 실행할 명령어 (응급 시)

#### 🚨 모든 것이 망가졌을 때
```bash
# 1. 패닉하지 말고 침착하게
# 2. 즉시 마지막 정상 상태로 복원
git reset --hard HEAD~1

# 3. 앱 실행 테스트
streamlit run app.py

# 4. 여전히 안되면 더 이전으로
git reset --hard HEAD~2
```

#### 🆘 특정 파일만 문제일 때
```bash
# 1. 해당 파일만 복원
cp src/services/파일명.py.backup src/services/파일명.py

# 2. 또는 Git에서 복원
git checkout HEAD -- src/services/파일명.py
```

#### 📱 도움 요청 전 체크리스트
- [ ] 어떤 작업을 하고 있었는가?
- [ ] 어떤 에러 메시지가 나타나는가?
- [ ] 마지막 정상 동작은 언제였는가?
- [ ] 어떤 파일을 수정했는가?
- [ ] 백업 파일들이 존재하는가?

---

**⚠️ 기억하세요**:
완벽한 리팩토링보다는 **동작하는 프로그램**이 더 중요합니다.
문제가 생기면 즉시 백업에서 복원하고, 천천히 다시 시작하세요.