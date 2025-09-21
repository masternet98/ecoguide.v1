# AI 리팩토링 실행 요청서 (Week 2 기준)

## 📦 프로젝트 개요
- **프로젝트명**: EcoGuide v1 리팩토링
- **기간**: 4주 (2025-09-21 ~ 2025-10-19)
- **현재 단계**: Week 2 (알림/프롬프트 서비스 정리)
- **최우선 원칙**: 프로그램 동작 오류 절대 금지, 문제 시 즉시 복구

## 📚 필수 참고 문서
1. `practical-refactoring-plan.md` – 4주 로드맵 (Week1 완료, Week2 진행 중)
2. `week2-detailed-plan.md` – 일자별 세부 작업 계획
3. `refactoring-checklist.md` – 안전 규칙
4. `safety-backup-guide.md` – 백업/복구 절차
5. `quick-start-guide.md` – 실행 순서 요약본 (Week2판)

## 🛡️ 핵심 안전 규칙
- **동시 수정 금지**: 한 번에 하나의 파일/책임 단위만 이동
- **백업 필수**: Git 스냅샷 + 주요 파일 `.backup` 유지
- **테스트 강제**: 기능 영향 범위에 따라 스모크 테스트 기록
- **문서화 유지**: `claude.20250921.md`에 진행 상황/테스트 결과 업데이트

## ▶️ Week 2 실행 요청 흐름

### 1단계 – 준비 및 현황 파악
```
1. git status / streamlit run app_new.py 로 기본 상태 확인
2. git add . && git commit -m "week2 start backup"
3. 주요 파일 백업 (notification_service.py 등)
```

### 2단계 – 일자별 계획 수행 (`week2-detailed-plan.md` 참조)
```
Day 8  : notification_service.py 분석 및 모듈 설계
Day 9-11: notification_sender/scheduler/config 모듈 분리 및 연동
Day 12 : prompt_service.py 구조 분석
Day 13-14: prompt_manager / prompt_renderer / prompt_validator 모듈화 및 테스트
```
각 Day 종료 시:
- 체크리스트 완료 여부 확인
- `claude.20250921.md`에 진행 로그 및 테스트 결과 기록
- git 커밋으로 스냅샷 보관

### 3단계 – 보고 및 회고
- 완료된 작업 요약, 생성/수정 파일, 테스트 결과 보고
- 문제 발생 시 즉시 복구 후 원인 및 해결 기록
- 다음 작업 준비 상태 (필요 리소스/테스트 계획) 정리

---

## ✅ 체크리스트 (Day별 반복)
- [ ] Git 백업 + 주요 파일 복사
- [ ] 한 책임 단위 이동 후 문법 검증 (`python -m py_compile`)
- [ ] 기능별 스모크 테스트 (Streamlit, 배치, 알림 등)
- [ ] `claude` 로그 업데이트
- [ ] 체크리스트 완료 여부 확인 후 커밋

---

## 🆘 문제 발생 시
- `safety-backup-guide.md`에 따라 즉시 복구
- 복구 과정과 원인을 `claude.20250921.md`에 기록
- 동일 이슈 재발 방지 조치 마련

---

**작성일**: 2025-09-27  
**적용 범위**: Week 2 (알림/프롬프트 서비스 리팩토링 단계)
