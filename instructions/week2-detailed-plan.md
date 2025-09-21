# 2주차 상세 실행 계획 - notification/prompt 서비스 리팩토링

## 📅 일정 개요
- **기간**: 2025-09-28 ~ 2025-10-04 (Week 2)
- **목표**: `notification_service.py`와 `prompt_service.py`를 모듈화하고, 공통 설정을 정돈하여 유지보수성 확보
- **원칙**: 기존 기능 온전 보존, 외부 API 호출 경로 변경 금지, 단계별 테스트 필수

---

## 🔍 Day 8 (2025-09-28): notification_service.py 분석 및 설계

### 🎯 목표
거대 파일 구조를 파악하고 3개 모듈 분리 설계를 완성한다.

### 작업 체크리스트
- [ ] Git 백업 (`git add . && git commit -m "week2 day8 backup"`)
- [ ] `notification_service.py` 라인 수/함수 목록 현황 정리
- [ ] 외부 의존성/환경 변수 여부 문서화
- [ ] 새 모듈 책임 초안 작성
  - `notification_sender.py`
  - `notification_scheduler.py`
  - `notification_config.py`
- [ ] 예상 리스크 및 테스트 항목 기록 (`instructions/claude.20250921.md` 업데이트)

---

## 📨 Day 9 (2025-09-29): notification_sender.py 생성

### 🎯 목표
발송 로직 관련 함수를 `notification_sender.py`로 이전해 독립 모듈을 만든다.

### 작업 체크리스트
- [ ] 백업 커밋 (`git commit -am "week2 day9 backup"`)
- [x] 새로운 모듈 생성 & 공용 로거/설정 import 구성
- [x] 메일/웹훅 발송 함수, 템플릿 렌더 함수 이전
- [x] 기존 서비스에서 새 모듈을 import하도록 수정
- [x] `python -m py_compile`로 문법 검증
- [ ] 주요 발송 시나리오 수동 테스트 기록

---

## ⏰ Day 10 (2025-09-30): notification_scheduler.py 분리

### 🎯 목표
배치 스케줄링과 큐 관리 코드를 전용 모듈로 이동한다.

### 작업 체크리스트
- [ ] 백업 커밋
- [ ] APScheduler/cron 관련 설정 함수 이전
- [ ] 모듈 간 순환 import 여부 점검
- [ ] 스케줄 등록/취소/상태 조회 함수 테스트 (가능 시 pytests 또는 수동 로그)
- [ ] 새 모듈 문서화 스니펫 작성 (`claude.20250921.md`)

---

## ⚙️ Day 11 (2025-10-01): notification_config.py 정리 및 통합

### 🎯 목표
설정/DTO/밸리데이션 로직을 정돈해 API 계층에서 재사용하도록 만든다.

### 작업 체크리스트
- [x] 설정 데이터 클래스/헬퍼 함수 이전
- [ ] `.env`/`secrets.toml` 참조 경로 확인
- [x] sender/scheduler 모듈에서 새 설정 모듈 사용하도록 리팩토링
- [ ] 통합 테스트 (발송 + 스케줄) 실행 및 결과 기록
- [ ] 단계별 커밋 (sender → scheduler → config → cleanup)

---

## ✉️ Day 12 (2025-10-02): prompt_service.py 분석 및 분해 설계

### 🎯 목표
프롬프트 관리 기능 구조를 분석하고 3분할 계획을 세운다.

### 작업 체크리스트
- [ ] Git 백업
- [ ] CRUD/렌더/검증 함수 목록화
- [ ] 새 모듈 책임 정의
  - `prompt_manager.py`
  - `prompt_renderer.py`
  - `prompt_validator.py`
- [ ] 관련 템플릿/캐시/외부 서비스 의존성 파악
- [ ] 테스트 전략 초안 수립

---

## 🧱 Day 13 (2025-10-03): prompt_manager & prompt_renderer 구현

### 🎯 목표
CRUD와 렌더링 로직을 각각의 모듈로 이동한다.

### 작업 체크리스트
- [ ] 백업 커밋
- [ ] CRUD 함수, 모델 변환 로직 `prompt_manager.py`로 이동
- [ ] 템플릿 렌더/프론트 변환 함수 `prompt_renderer.py`로 이동
- [ ] 서비스/프로세스들이 새 모듈을 참조하도록 수정
- [ ] UI 페이지/서비스 호출 수동 테스트 기록

---

## ✅ Day 14 (2025-10-04): prompt_validator 통합 및 주차 마감 점검

### 🎯 목표
검증 로직을 분리하고 Week2 전체 리팩토링을 안정화한다.

### 작업 체크리스트
- [ ] `prompt_validator.py` 작성 및 유효성 검사 함수 이동
- [ ] manager/renderer와의 상호 의존성 최소화
- [ ] 전체 프롬프트 흐름 테스트 (생성→검증→렌더)
- [ ] 회귀 테스트 또는 스모크 테스트 실행
- [ ] Week2 회고: 진행 현황 요약 (claude 로그) & 다음 주 준비

---

## 📋 공통 안전 수칙 요약
- 변경 전 Git 스냅샷과 핵심 파일 백업 유지
- 파일 이동 후 `python -m py_compile`로 즉시 문법 검증
- Streamlit/스케줄러/발송 기능은 가능한 한 단계별로 수동 확인
- 문제 발생 시 `safety-backup-guide.md`에 따라 즉시 복구 후 원인 문서화

---

## ✅ Week2 완료 조건
- [x] `notification_service.py` 3개 모듈로 분할 및 인터페이스 안정화
- [ ] `prompt_service.py` 3개 모듈로 분할 및 기존 기능 유지
- [ ] 모든 변경 건에 대한 테스트/검증 로그 존재
- [ ] 주요 문서(quick-start, practical-plan, claude 로그) 업데이트
- [ ] 다음 주(Week3) 착수에 필요한 사전 분석 항목 식별
