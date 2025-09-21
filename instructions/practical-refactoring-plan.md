# 1인 개발자를 위한 실용적 리팩토링 계획 (업데이트: Week 2)

## ✅ 진행 현황 요약
- **Week 1 (완료)**: `district_service.py` 모듈 분리, `monitoring_ui.py` 3분화 및 강제 업데이트 플로우 복원
- **Week 2 (진행 중)**: `notification_service.py`, `prompt_service.py` 모듈화 및 설정 정리
- **Week 3~4 (예정)**: core 디렉터리 정돈, 구조 최적화 및 문서/품질 보강

---

## 🔑 공통 원칙
- 안정성 우선: 변경 후 즉시 스모크 테스트, 문제 시 즉시 복구
- 단계적 진행: 한 번에 하나의 책임 단위를 이동/검증
- 문서화 유지: `claude.20250921.md`에 일자별 로그와 테스트 결과 기록

---

## 📆 4주 리팩토링 로드맵

### Week 1 (완료) – 생존 단계
- [x] `district_service.py` → `district_loader.py`, `district_cache.py`, `district_validator.py`, `district_api.py`
- [x] `monitoring_ui.py` → `monitoring_dashboard.py`, `monitoring_data.py`, `monitoring_charts.py`
- [x] 강제 업데이트/모니터링 페이지 기능 회복 및 테스트 로그 확보

### Week 2 (진행 중) – 정리 단계
- [ ] `notification_service.py` 모듈화 (sender / scheduler / config)
- [ ] `prompt_service.py` 모듈화 (manager / renderer / validator)
- [ ] 관련 페이지/배치/발송 플로우 회귀 테스트 및 문서 업데이트

### Week 3 (예정) – 개선 단계
- [ ] `src/core` 하위 파일 정돈 및 의존성 단순화
- [ ] 공통 유틸 및 진입점 구조 개선 (필요 시 lazy import, 타입 힌트 정비)
- [ ] 반복적인 실행 시나리오 자동화 스크립트 초안 작성

### Week 4 (예정) – 안정화 단계
- [ ] 최종 문서/체크리스트/가이드 업데이트 및 중복 문서 정리
- [ ] 기본 코드 품질 검증(포매터, 린터, 간단 테스트) 도입
- [ ] 회귀 테스트 모음 정리 및 릴리스 체크리스트 확립

---

## 🛡️ 안전 체크리스트 (변경 전/중/후)
1. **변경 전**
   - Git 커밋으로 현재 상태 저장 (`weekX dayY backup`)
   - 핵심 파일 `.backup` 복사본 준비
   - 목표/리스크/테스트 항목 `claude` 로그에 메모
2. **변경 중**
   - 파일 이동은 책임 단위별로 수행
   - `python -m py_compile` 및 로컬 스모크 테스트 즉시 실행
   - 예상치 못한 오류는 즉시 중단하고 원인 분석 후 재시도
3. **변경 후**
   - Streamlit/배치/발송 등 영향을 받는 기능 스모크 테스트
   - 변경 내용과 테스트 결과 문서화 (`claude`, 커밋 메시지)
   - 체크리스트 항목 완료 여부 재확인 후 커밋

---

## 🆘 응급 복구 절차
```bash
# 파일 단위 복원
git checkout HEAD -- path/to/file.py
# 또는
cp path/to/file.py.backup path/to/file.py

# 전체 롤백 (주의)
git reset --hard HEAD~1
```

---

## 📌 참고 자료
- `week2-detailed-plan.md`: Day 8~14 일자별 수행 목록과 체크리스트
- `quick-start-guide.md`: Week2 기준 실행 순서 요약본
- `refactoring-checklist.md`: 단계별 안전 규칙
- `safety-backup-guide.md`: 백업/복구 대응 안내

---

**생성일**: 2025-09-21  
**최종 갱신**: 2025-09-27  
**검토 일정**: 매주 금요일
