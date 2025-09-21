# 🚀 AI 리팩토링 빠른 시작 가이드

## 📋 AI에게 전달할 완성된 요청서

### 요청서 사용법
다음 텍스트를 그대로 복사하여 AI에게 전달하세요:

---

## 🎯 리팩토링 실행 요청

다음 리팩토링 작업을 안전하고 체계적으로 수행해주세요.

### 📚 필수 숙지 문서
실행 전 다음 문서들을 반드시 읽고 숙지해주세요:
1. `instructions/practical-refactoring-plan.md` - 전체 4주 계획
2. `instructions/refactoring-checklist.md` - 안전 체크리스트
3. `instructions/week1-detailed-plan.md` - 1주차 상세 계획
4. `instructions/safety-backup-guide.md` - 백업/복구 가이드
5. `instructions/ai-refactoring-request.md` - 종합 실행 요청서
6. `CLAUDE.md` - 프로젝트 구조 가이드

### 🚨 절대 안전 규칙
- ❌ 여러 파일 동시 수정 금지
- ❌ 백업 없는 변경 금지
- ❌ 테스트 없는 커밋 금지
- ✅ 매 변경 전 Git 백업 필수
- ✅ 변경 후 즉시 앱 테스트 필수
- ✅ 문제 시 즉시 백업 복원 필수

### 📋 실행 요청 사항

#### 1단계: 환경 준비
```
1. 현재 상태 확인:
   - `streamlit run app.py` 정상 실행 확인
   - 주요 페이지 3-4개 정상 동작 확인
   - `git status` 확인

2. 백업 시스템 구축:
   - `git add . && git commit -m "리팩토링 시작 전 전체 백업"`
   - `cp src/services/district_service.py src/services/district_service.py.backup`
   - `cp src/components/monitoring_ui.py src/components/monitoring_ui.py.backup`

3. 현황 분석 보고:
   - 파일별 라인 수 현황
   - 발견된 문제점 목록
   - 1주차 실행 준비 상태
```

#### 2단계: 1주차 실행 (Week 1)
`week1-detailed-plan.md`에 따라 Day 1부터 순차 실행:

**Day 1 (분석)**: district_service.py 완전 분석 및 4개 파일 분해 계획
**Day 2**: district_loader.py 생성 (데이터 로딩 기능)
**Day 3**: district_cache.py 생성 (캐시 관리 기능)
**Day 4**: district_validator.py 생성 (데이터 검증 기능)
**Day 5**: district_api.py 생성 및 통합
**Day 6-7**: monitoring_ui.py를 3개 파일로 분해

⚠️ 각 단계마다 `refactoring-checklist.md`의 체크리스트 100% 준수

#### 3단계: 진행 보고
각 작업 완료 후 다음을 보고:
1. 완료된 작업 상세 내역
2. 생성/수정된 파일 목록
3. 체크리스트 완료 상황
4. 발견된 문제점 및 해결방법
5. 다음 단계 준비 상태

**진행률 추적**: `progress-tracking-template.md` 양식 사용

### 🎯 성공 기준
- [ ] 모든 파일 500줄 이하
- [ ] 앱 시작 시간 2분 이내 유지
- [ ] 모든 기존 기능 100% 정상 동작
- [ ] 새로운 에러나 경고 0개

### 🚨 응급상황 대응
문제 발생 시 즉시:
```bash
# 전체 복원
git reset --hard HEAD~1

# 특정 파일 복원
cp src/services/파일명.py.backup src/services/파일명.py
```

**이제 1주차 Day 1부터 시작해주세요. 모든 안전 규칙을 준수하며 체크리스트를 하나씩 완료해주세요.**

---

## 📊 진행상황 확인 방법

### 일일 체크포인트
매일 다음을 확인하세요:
1. **오늘 계획 대비 달성률**: XX%
2. **완료된 체크리스트 항목**: XX/XX개
3. **앱 정상 동작 여부**: ✅/❌
4. **발생한 문제 및 해결**: 기록 필요

### 주간 마일스톤
- **Week 1 목표**: district_service.py + monitoring_ui.py 분해
- **성공 지표**: 7개 신규 파일 생성, 기존 기능 100% 유지
- **완료 예정일**: 2025-09-27

### 전체 진행률
- **4주 전체 계획**: 거대 파일 분해 → 중간 파일 정리 → 구조 최적화 → 안정화
- **현재 진행률**: 0% (준비 완료 상태)
- **다음 마일스톤**: 1주차 완료

---

## 🔧 문제 해결 빠른 참조

### 자주 발생하는 문제
1. **ImportError**: `__init__.py` 파일 추가
2. **함수 누락**: 백업 파일에서 확인 후 복원
3. **앱 실행 오류**: `git reset --hard HEAD~1`
4. **순환 import**: 지연 import 또는 공통 모듈 추출

### 즉시 사용할 명령어
```bash
# 현재 상태 확인
streamlit run app.py
git status

# 백업 생성
git add . && git commit -m "작업 전 백업"
cp 파일명.py 파일명.py.backup

# 문법 확인
python -m py_compile src/services/파일명.py

# 복원
cp 파일명.py.backup 파일명.py
git checkout HEAD -- 파일명.py
```

---

## 📝 사용 예시

### AI에게 요청하는 방법:

**1. 전체 요청서 전달**:
```
"위의 리팩토링 실행 요청에 따라 작업을 시작해주세요.
1주차 Day 1부터 체크리스트를 하나씩 완료해주세요."
```

**2. 진행상황 확인**:
```
"현재 진행상황을 progress-tracking-template.md 양식에 따라
보고해주세요."
```

**3. 문제 발생 시**:
```
"문제가 발생했습니다. safety-backup-guide.md에 따라
즉시 복원하고 상황을 보고해주세요."
```

### 예상 응답 형태:
```
✅ Day 1 작업 시작

1. 환경 준비 완료:
   - 현재 앱 정상 실행 확인 ✅
   - Git 백업 완료 ✅
   - 개별 파일 백업 완료 ✅

2. district_service.py 분석 중:
   - 총 2,217줄 확인
   - 주요 클래스 3개 식별
   - 분해 계획 수립 중...

[상세 진행사항 보고]
```

---

**🎯 핵심 포인트**:
이 가이드를 사용하면 AI가 모든 안전 조치를 준수하며
체계적으로 리팩토링을 진행할 수 있습니다.