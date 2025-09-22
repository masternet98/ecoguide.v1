# 소스 폴더 구조 직관성 개선 리팩토링 계획

## 📋 개요
**목표**: 현재 src/ 폴더 구조를 더 직관적이고 이해하기 쉽게 재구성
**범위**: 폴더 구조 개선 (파일 내용 변경 없음)
**원칙**: 기능별 그룹핑, 계층적 구조, 명확한 네이밍

---

## 🔍 현재 구조 분석

### 📂 현재 src/ 구조 (75개 Python 파일)
```
src/
├── components/          # UI 컴포넌트 (21개 파일)
│   ├── analysis/        # 이미지 분석 관련 컴포넌트
│   ├── prompts/         # 프롬프트 관리 컴포넌트
│   ├── status/          # 상태 표시 컴포넌트
│   └── [기타 UI 파일들]  # 산발적으로 분산된 UI 컴포넌트들
├── core/               # 핵심 시스템 (13개 파일)
├── layouts/            # 레이아웃 (1개 파일)
├── pages/              # 페이지 로직 (1개 파일)
└── services/           # 비즈니스 서비스 (39개 파일)
```

### 🚨 현재 구조의 문제점

1. **services/ 폴더 비대함**: 39개 파일로 과도하게 집중됨
2. **도메인 혼재**: 서로 다른 도메인(행정구역, 프롬프트, 모니터링 등)이 services에 뭉쳐있음
3. **컴포넌트 분산**: UI 컴포넌트가 하위 폴더와 루트에 혼재
4. **기능별 응집도 부족**: 관련 파일들이 서로 다른 폴더에 분산
5. **네이밍 일관성 부족**: 일부 파일명이 직관적이지 않음

---

## 🎯 개선 목표

### 🏗️ 새로운 구조 설계 원칙

1. **도메인 기반 조직화**: 기능별로 관련 파일들을 그룹핑
2. **계층적 구조**: 상위 개념부터 하위 세부사항까지 논리적 배치
3. **명확한 책임 분리**: 각 폴더의 역할이 이름으로 직관적으로 파악 가능
4. **확장성 고려**: 새로운 기능 추가 시 명확한 위치 제공

---

## 📊 제안하는 새 구조

### 🔄 리팩토링 후 목표 구조
```
src/
├── app/                    # 애플리케이션 계층
│   ├── core/              # 핵심 시스템 (현재 core/ 이동)
│   ├── config/            # 설정 관련 (core에서 분리)
│   └── layouts/           # 레이아웃 (현재 layouts/ 이동)
│
├── domains/               # 도메인별 기능 모음
│   ├── district/          # 행정구역 도메인
│   │   ├── services/      # district_***.py 파일들
│   │   ├── components/    # 행정구역 관련 UI
│   │   └── types.py       # 도메인 타입 정의
│   │
│   ├── analysis/          # 이미지 분석 도메인
│   │   ├── services/      # vision_service.py, openai_service.py
│   │   ├── components/    # analysis 폴더 내용들
│   │   └── types.py       # vision_types.py
│   │
│   ├── prompts/           # 프롬프트 도메인
│   │   ├── services/      # prompt_***.py 파일들
│   │   ├── components/    # prompts 폴더 + prompt_admin_ui.py
│   │   └── types.py       # prompt_types.py
│   │
│   ├── monitoring/        # 모니터링 도메인
│   │   ├── services/      # monitoring_***.py, notification_***.py
│   │   ├── components/    # monitoring 관련 UI들
│   │   └── types.py
│   │
│   └── infrastructure/    # 인프라/유틸리티
│       ├── search/        # search_***.py
│       ├── tunnel/        # tunnel_service.py + tunnel_ui.py
│       ├── location/      # location_service.py + location_selector.py
│       └── batch/         # batch_service.py
│
├── shared/                # 공통 모듈
│   ├── components/        # 공통 UI 컴포넌트
│   │   ├── base/          # base.py, base_ui.py
│   │   ├── status/        # status 폴더 내용
│   │   └── common/        # 기타 공통 컴포넌트
│   ├── types/            # 공통 타입 정의
│   ├── utils/            # 유틸리티 함수들
│   └── validators/       # 공통 검증 로직
│
└── pages/                 # 페이지 진입점 (현재 pages/ 유지)
```

---

## 📋 상세 이동 계획

### 🚀 Phase 1: 도메인별 서비스 분리 (우선순위 높음)

#### 1️⃣ District 도메인 구성
```bash
src/domains/district/
├── services/
│   ├── __init__.py
│   ├── district_service.py      # 기존 파일 이동
│   ├── district_api.py          # 기존 파일 이동
│   ├── district_cache.py        # 기존 파일 이동
│   ├── district_loader.py       # 기존 파일 이동
│   └── district_validator.py    # 기존 파일 이동
├── components/
│   └── link_collector_ui.py     # 기존 components/에서 이동
└── types.py                     # 새로 생성 (필요시)
```

#### 2️⃣ Analysis 도메인 구성
```bash
src/domains/analysis/
├── services/
│   ├── __init__.py
│   ├── vision_service.py        # 기존 services/에서 이동
│   └── openai_service.py        # 기존 services/에서 이동
├── components/
│   ├── __init__.py
│   ├── analysis_interface.py    # 기존 components/analysis/에서 이동
│   ├── image_analysis.py        # 기존 components/analysis/에서 이동
│   ├── image_input.py          # 기존 components/analysis/에서 이동
│   ├── results_display.py      # 기존 components/analysis/에서 이동
│   ├── analysis_page.py        # 기존 components/에서 이동
│   └── measure_ui.py           # 기존 components/에서 이동
└── types.py                    # vision_types.py 이름 변경
```

#### 3️⃣ Prompts 도메인 구성
```bash
src/domains/prompts/
├── services/
│   ├── __init__.py
│   ├── prompt_service.py        # 기존 services/에서 이동
│   ├── prompt_manager.py        # 기존 services/에서 이동
│   ├── prompt_renderer.py       # 기존 services/에서 이동
│   └── prompt_validator.py      # 기존 services/에서 이동
├── components/
│   ├── __init__.py
│   ├── prompt_initializer.py    # 기존 components/prompts/에서 이동
│   ├── prompt_manager_ui.py     # 기존 components/prompts/에서 이동
│   ├── prompt_selector.py       # 기존 components/prompts/에서 이동
│   └── prompt_admin_ui.py       # 기존 components/에서 이동
└── types.py                     # core/prompt_types.py 이동
```

#### 4️⃣ Monitoring 도메인 구성
```bash
src/domains/monitoring/
├── services/
│   ├── __init__.py
│   ├── monitoring_service.py           # 기존 services/에서 이동
│   ├── monitoring_admin_integration.py # 기존 services/에서 이동
│   ├── notification_service.py         # 기존 services/에서 이동
│   ├── notification_sender.py          # 기존 services/에서 이동
│   ├── notification_scheduler.py       # 기존 services/에서 이동
│   └── notification_config.py          # 기존 services/에서 이동
├── components/
│   ├── __init__.py
│   ├── monitoring_ui.py          # 기존 components/에서 이동
│   ├── monitoring_dashboard.py   # 기존 components/에서 이동
│   ├── monitoring_charts.py      # 기존 components/에서 이동
│   └── monitoring_data.py        # 기존 components/에서 이동
└── types.py                      # 새로 생성 (필요시)
```

### 🚀 Phase 2: 공통 모듈 정리

#### 5️⃣ App 계층 구성
```bash
src/app/
├── core/                    # 기존 core/ 폴더 이동
│   ├── app_factory.py
│   ├── service_factory.py
│   ├── feature_registry.py
│   ├── session_state.py
│   ├── error_handler.py
│   ├── logger.py
│   ├── utils.py
│   └── ui.py
├── config/                  # core에서 설정 관련 분리
│   ├── __init__.py
│   ├── config.py           # core/config.py에서 이동
│   ├── config_validator.py # core/config_validator.py에서 이동
│   └── dependency_manager.py # core/dependency_manager.py에서 이동
└── layouts/                # 기존 layouts/ 폴더 이동
    ├── __init__.py
    └── main_layout.py
```

#### 6️⃣ Shared 모듈 구성
```bash
src/shared/
├── components/
│   ├── base/
│   │   ├── __init__.py
│   │   ├── base.py         # 기존 components/에서 이동
│   │   └── base_ui.py      # 기존 components/에서 이동
│   ├── status/
│   │   ├── __init__.py
│   │   ├── feature_status.py  # 기존 components/status/에서 이동
│   │   └── service_status.py  # 기존 components/status/에서 이동
│   └── common/
│       ├── __init__.py
│       └── log_viewer.py   # 기존 components/에서 이동
├── types/
│   ├── __init__.py
│   └── common_types.py     # 공통 타입 정의
├── utils/
│   ├── __init__.py
│   └── file_source_validator.py # 기존 services/에서 이동
└── validators/
    ├── __init__.py
    └── base_service.py     # 기존 core/에서 이동
```

#### 7️⃣ Infrastructure 도메인 구성
```bash
src/domains/infrastructure/
├── search/
│   ├── __init__.py
│   ├── search_manager.py    # 기존 services/에서 이동
│   ├── search_providers.py  # 기존 services/에서 이동
│   └── link_collector_service.py # 기존 services/에서 이동
├── tunnel/
│   ├── __init__.py
│   ├── tunnel_service.py    # 기존 services/에서 이동
│   └── tunnel_ui.py        # 기존 components/에서 이동
├── location/
│   ├── __init__.py
│   ├── location_service.py  # 기존 services/에서 이동
│   └── location_selector.py # 기존 components/에서 이동
└── batch/
    ├── __init__.py
    └── batch_service.py     # 기존 services/에서 이동
```

---

## 🛠️ 실행 단계

### 📅 Phase 1: 준비 작업 (Day 1)
1. **백업 생성**: 현재 상태 커밋
2. **새 폴더 구조 생성**: domains/, app/, shared/ 폴더 생성
3. **__init__.py 파일 생성**: 모든 새 폴더에 __init__.py 생성

### 📅 Phase 2: District 도메인 이동 (Day 1-2)
1. `src/domains/district/` 구조 생성
2. district 관련 서비스 파일들 이동
3. Import 경로 업데이트
4. 테스트 실행 및 검증

### 📅 Phase 3: Analysis 도메인 이동 (Day 2-3)
1. `src/domains/analysis/` 구조 생성
2. vision 관련 서비스 및 컴포넌트 이동
3. Import 경로 업데이트
4. 테스트 실행 및 검증

### 📅 Phase 4: 나머지 도메인 이동 (Day 3-4)
1. Prompts, Monitoring, Infrastructure 도메인 순차 이동
2. 각 단계별 Import 경로 업데이트
3. 단계별 테스트 실행

### 📅 Phase 5: 공통 모듈 정리 (Day 4-5)
1. App 계층 구성
2. Shared 모듈 구성
3. 최종 Import 경로 정리
4. 전체 테스트 실행

---

## ⚠️ 주의사항

### 🔒 안전 조치
1. **단계별 커밋**: 각 도메인 이동 후 반드시 커밋
2. **Import 경로 검증**: 이동 후 즉시 Import 오류 확인
3. **기능 테스트**: 각 단계별로 주요 기능 동작 확인
4. **롤백 준비**: 문제 발생 시 이전 커밋으로 롤백 가능

### 🎯 성공 기준
1. **Import 오류 없음**: 모든 파일이 정상적으로 Import됨
2. **기능 정상 동작**: 기존 모든 기능이 정상 작동
3. **구조적 개선**: 폴더별 역할이 명확해짐
4. **확장성 향상**: 새 기능 추가 시 배치할 위치가 명확함

---

## 📈 기대 효과

### 🎉 직관성 향상
- **도메인별 그룹핑**: 관련 기능을 한 곳에서 관리
- **명확한 네이밍**: 폴더명만으로 기능 파악 가능
- **계층적 구조**: 상위 개념부터 세부사항까지 논리적 배치

### 🔧 유지보수성 향상
- **응집도 증가**: 관련 파일들이 가까이 위치
- **결합도 감소**: 도메인 간 의존성 명확화
- **확장성 개선**: 새 기능 추가 시 명확한 배치 위치

### 👥 개발 생산성 향상
- **파일 찾기 용이**: 직관적 폴더 구조로 빠른 탐색
- **코드 이해도 향상**: 구조만으로도 아키텍처 파악 가능
- **팀 협업 개선**: 일관된 구조로 팀원 간 이해도 통일

---

**📝 작성일**: 2025-09-22
**📋 작성자**: Claude
**🎯 목표**: 직관적이고 확장 가능한 소스 구조 구현