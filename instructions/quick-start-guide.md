# 🚀 AI 리팩토링 빠른 실행 가이드 (업데이트: Week 2 착수)

## ✅ Week 1 요약
- district 서비스 모듈 분해 및 고수준 API(`src/services/district_api.py`) 완성
- monitoring UI 분해(대시보드/데이터/차트)와 페이지 연동 업데이트 완료
- 강제 업데이트 플로우 복원 및 주요 NameError 정비

👉 이제 Week 2(알림/프롬프트 서비스 정리)로 전환합니다.

---

## 📚 Week 2 작업을 시작하기 전에 읽어야 할 문서
1. `instructions/practical-refactoring-plan.md` – 4주 전체 로드맵 (Week1 완료 표시 포함)
2. `instructions/week2-detailed-plan.md` – 2주차 일자별 세부 계획
3. `instructions/refactoring-checklist.md` – 안전 규칙 체크리스트
4. `instructions/safety-backup-guide.md` – 백업/복구 절차
5. `instructions/ai-refactoring-request.md` – AI 실행 요청서 (Week2 기준으로 업데이트 필요 시 참고)

---

## 🛡️ 변함없는 절대 안전 규칙
- ❌ 여러 파일 동시에 수정 금지 (단계적으로 진행)
- ❌ 백업 없이 변경 금지 (Git + 개별 파일 백업 유지)
- ❌ 테스트 없이 커밋 금지
- ✅ 변경 전 최신 Git 스냅샷 생성
- ✅ 변경 후 바로 모듈 테스트 또는 스모크 테스트 실행
- ✅ 문제 발생 시 `safety-backup-guide.md`에 따라 즉시 복원

---

## ▶️ Week 2 실행 요청
Week2는 `notification_service.py`와 `prompt_service.py` 리팩토링에 집중합니다. 아래 흐름을 따라 진행하세요.

### 1단계: 준비 및 현황 확인
```
1. 최신 코드 불러오기 및 Git 상태 확인
   - git status
   - streamlit run app_new.py (핵심 페이지 빠른 점검)

2. 백업 체계 정비
   - git add . && git commit -m "week2 start backup"
   - 필요한 주요 파일 백업 (notification_service.py 등)

3. Week1 완료 로그 / claude.20250921.md 확인
   - 지난주 작업 노트 확인 후 미해결 이슈 없는지 검토
```

### 2단계: 일자별 계획 수행 (Week2 세부 계획 참고)
- Day 8: `notification_service.py` 구조 분석 및 모듈 설계
- Day 9~11: sender/scheduler/config 모듈 순차 분리 및 통합 테스트
- Day 12~14: `prompt_service.py` 분석 → manager/renderer/validator 모듈화 → 흐름 검증
- 매일 체크리스트 완수 후 claude 로그에 결과 기록

### 3단계: 진행 보고 및 문서 업데이트
- 완료한 작업, 생성/수정 파일, 테스트 결과, 다음 단계 준비상황을 요약
- `practical-refactoring-plan.md`와 `claude.20250921.md`에 진행률 반영
- 문제가 발생하면 즉시 복구 후 원인과 해결 과정을 신속히 기록

---

## 🧾 진행 상황 체크 방법

### 일일 체크포인트
1. 오늘 계획 대비 달성률 (예: 80%)
2. 체크리스트 완료 항목 수 (예: 5/6)
3. 핵심 기능 스모크 테스트 여부 (✅/❌)
4. 발생한 문제와 대응 기록 여부

### 주간 마일스톤 (Week 2)
- **목표**: `notification_service.py`와 `prompt_service.py`의 모듈화 완료
- **성공 지표**: 6개 신규 모듈 도입, 기존 발송/프롬프트 기능 100% 유지
- **예상 완료일**: 2025-10-04

### 전체 진행률 참고
- Week1 ✅ 완료 → Week2 진행 중 → Week3(코어 정리) 준비
- 다음 마일스톤: Week2 완료 후 core 최적화 사전 분석 착수

---

## 🔧 문제 해결 빠른 참고
- **ImportError**: 새 모듈 경로 등록 여부 및 `__init__.py` 확인
- **TasK 실패**: 백업 복원 후 claude 로그에 원인/대응 기록
- **체계적 테스트**: `python -m py_compile` + 서비스별 수동 스모크 테스트 유지

---

## 📝 AI와의 소통 예시 (Week2)

**1. 실행 요청**
```
"Week2 계획에 따라 Day 8 작업을 시작해주세요. notification_service 분석과 모듈 설계를 완료해주세요."
```

**2. 진행 상황 보고 요청**
```
"현재 진행 상황을 week2-detailed-plan.md 기준으로 요약해 주세요."
```

**3. 문제 발생 시**
```
"강제 업데이트 도중 오류가 발생했습니다. safety-backup-guide.md에 따라 복구하고 원인과 조치를 보고해주세요."
```

---

## 🎯 핵심 메시지
Week1 기반 구조 작업은 완료되었습니다. 이제 알림/프롬프트 서비스 분해에 집중하며, 문서·체크리스트·백업 체계를 유지한 채 Week2의 세부 계획을 차근차근 진행해 주세요.
