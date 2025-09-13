# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소의 코드를 작업할 때 참고하는 가이드라인을 제공합니다.

## 개발 명령어

### 애플리케이션 실행
- **Streamlit 앱 시작**: `streamlit run app.py`
- **대안 실행 방법**: `run.bat` (Windows 배치 파일)

### 테스트
- **모든 테스트 실행**: `pytest` (테스트는 `test/` 디렉토리에 위치)
- **특정 테스트 파일 실행**: `pytest test/test_vision_pipeline.py`
- **상세 출력으로 테스트 실행**: `pytest -v`

### 패키지 설치
- **핵심 의존성 설치**: `pip install -r requirements.txt`
- **비전 의존성 설치** (선택사항, CPU 전용): `pip install rembg mediapipe ultralytics opencv-python`
- **GPU 지원을 위한 PyTorch 설치**: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`

## 아키텍처 개요

이것은 **Streamlit 기반의 멀티모달 AI 애플리케이션**으로, OpenAI Vision API와 로컬 컴퓨터 비전 모델을 결합하여 이미지 분석, 대형폐기물 관리, 행정구역 데이터 관리를 수행합니다. 컴포넌트 기반 아키텍처와 의존성 주입 패턴을 사용하여 확장성과 유지보수성을 제공합니다.

### 핵심 컴포넌트

**메인 애플리케이션 구조**:
- `app.py` - 새로운 아키텍처 기반 메인 애플리케이션 진입점
- `pages/` - Streamlit 다중 페이지 구조 (01_district_links.py, 02_district_config.py, 03_district_monitoring.py, 04_prompt_admin.py, 04_tunnel_management.py, 99_logs.py)
- `src/` - 모듈화된 소스 코드 (책임별 조직화)

**애플리케이션 초기화 계층** (`src/core/`):
- `app_factory.py` - 애플리케이션 컨텍스트 및 의존성 주입 관리
- `service_factory.py` - 서비스 인스턴스 생성 및 등록
- `feature_registry.py` - 동적 기능 활성화/비활성화 관리
- `config.py` - 중앙화된 설정 관리 (Config, DistrictConfig, SearchProviderConfig 등)
- `session_state.py` - Streamlit 세션 상태 체계적 관리
- `error_handler.py` - 전역 에러 처리 및 사용자 친화적 메시지

**서비스 계층** (`src/services/`):
- `openai_service.py` - OpenAI Vision API 통합 이미지 분석
- `vision_service.py` - 로컬 컴퓨터 비전 파이프라인 (YOLO, MediaPipe, rembg)
- `vision_types.py` - 비전 파이프라인 결과를 위한 데이터 클래스들
- `district_service.py` - 행정구역 데이터 다운로드 및 관리
- `link_collector_service.py` - 시군구별 대형폐기물 배출신고 링크 자동 수집
- `search_manager.py` & `search_providers.py` - 검색 제공자 관리 (Google CSE, Bing, HTML 파싱)
- `prompt_service.py` - 동적 프롬프트 관리 시스템
- `tunnel_service.py` - Cloudflared 터널 관리
- `monitoring_service.py` & `notification_service.py` - 시스템 모니터링 및 알림
- `batch_service.py` - 대량 작업 처리

**컴포넌트 계층** (`src/components/`):
- `base.py` & `base_ui.py` - 컴포넌트 기반 아키텍처 기반 클래스
- `analysis/` - 이미지 분석 관련 컴포넌트 (image_input.py, image_analysis.py, results_display.py)
- `prompts/` - 프롬프트 관리 컴포넌트 (prompt_manager.py, prompt_selector.py, prompt_initializer.py)
- `status/` - 상태 표시 컴포넌트 (service_status.py, feature_status.py)
- 개별 UI 컴포넌트들 (measure_ui.py, tunnel_ui.py, monitoring_ui.py, log_viewer.py 등)

**레이아웃 계층** (`src/layouts/`):
- `main_layout.py` - 메인 레이아웃 및 사이드바 관리

**페이지 계층** (`src/pages/`):
- `camera_analysis.py` - 카메라 분석 페이지 비즈니스 로직

### 핵심 아키텍처 패턴

**컴포넌트 기반 아키텍처**:
- `BaseComponent` 및 `BaseUIComponent` 상속을 통한 일관된 컴포넌트 구조
- 의존성 주입을 통한 서비스 접근 (`self.get_service('service_name')`)
- 컴포넌트별 독립적인 렌더링 및 상태 관리

**Feature Registry 시스템**:
- 런타임 기능 활성화/비활성화 (`FeatureRegistry`)
- 의존성 체크 및 자동 기능 가용성 확인
- 환경별 선택적 기능 로딩 (무거운 AI 모델 등)

**Service Factory 패턴**:
- 서비스 인스턴스의 중앙화된 생성 및 관리
- 설정 기반 서비스 초기화
- 의존성 주입을 통한 느슨한 결합

### 비전 파이프라인 아키텍처

애플리케이션은 이중 분석 접근법을 구현합니다:
1. **OpenAI Vision 분석**: 클라우드 기반 객체 식별 및 설명
2. **로컬 비전 파이프라인**: 컴퓨터 비전 기반 크기 추정:
   - 배경 제거 (`rembg`)
   - 손 검출 (`MediaPipe Hands`)
   - 객체 검출 (`YOLOv8`)
   - 손-객체 비율 기반 크기 계산

### 설정 관리

**계층적 설정 구조** (`src/core/config.py`):
- `Config` - 메인 애플리케이션 설정
- `DistrictConfig` - 행정구역 데이터 관리 설정
- `SearchProviderConfig` - 검색 제공자 설정 (Google CSE, Bing 등)
- `PromptConfig` - 프롬프트 관리 설정
- `VisionConfig` - 비전 파이프라인 설정

**환경 변수**:
- `OPENAI_API_KEY` - OpenAI Vision API용
- `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_SEARCH_ENGINE_ID` - Google Custom Search용
- `BING_SEARCH_API_KEY` - Bing Search API용
- 설정은 `.env` 파일 또는 Streamlit secrets에서 로드

### 상태 관리

**체계화된 세션 상태** (`SessionStateManager`):
- `ImageSessionState` - 이미지 및 분석 결과 상태
- `UISessionState` - UI 전환 및 상호작용 상태
- 타입 안전한 상태 업데이트 및 접근
- 탭 전환 시 자동 데이터 정리

**애플리케이션 컨텍스트** (`ApplicationContext`):
- 전역 애플리케이션 상태 관리
- 서비스 및 기능 레지스트리 접근
- 초기화 상태 추적

### 모델 및 데이터 관리

**로컬 AI 모델**:
- `models/yolov8n.pt` - 일반 객체 검출
- `models/yolov8n-hand-pose.pt` - 손 자세 검출
- ultralytics 첫 사용 시 모델 자동 다운로드

**GPU/CPU 유연성**:
- `VisionConfig.use_gpu`를 통한 GPU 사용 설정 가능
- CPU 전용 동작으로의 우아한 폴백
- 무거운 모델 의존성 없이 테스트를 위한 Mock 구현

**행정구역 데이터 관리**:
- data.go.kr에서 자동 행정구역 데이터 다운로드
- CSV 형식 데이터 파싱 및 JSON 변환
- 대형폐기물 배출신고 홈페이지 링크 자동 수집

## 개발 실천사항

### 코드 조직 원칙
- **관심사의 분리**: UI (컴포넌트), 비즈니스 로직 (서비스), 설정 (코어)
- **의존성 주입**: 전역 접근보다는 설정 객체를 명시적으로 전달
- **모듈러 설계**: 각 서비스는 단일 책임 처리
- **타입 안전성**: 데이터클래스 및 타입 힌트 광범위 사용
- **컴포넌트 기반**: BaseComponent 상속을 통한 일관된 구조

### 테스트 전략
- **무거운 의존성 Mock**: 모델 다운로드 피하기 위한 비전 모델 Mock
- **단위 테스트**: 통제된 입력으로 개별 함수 테스트
- **통합 테스트**: 외부 의존성을 Mock한 완전한 파이프라인 테스트
- **테스트 데이터**: 수동 검증을 위한 `test/` 디렉토리 샘플 이미지

### 에러 처리
- **우아한 기능 저하**: 모델 사용 불가 시 비전 기능 비활성화
- **사용자 친화적 메시지**: API 키 누락이나 모델 실패에 대한 명확한 오류 메시지
- **폴백 모드**: 선택적 기능 실패 시에도 애플리케이션 지속 동작
- **중앙화된 에러 처리**: `ErrorHandler` 클래스를 통한 일관된 에러 관리

## 주요 구현 세부사항

### 이미지 처리 플로우
1. **입력**: Streamlit을 통한 카메라 캡처 또는 파일 업로드
2. **전처리**: 설정 가능한 품질/크기 제한으로 JPEG 변환
3. **분석 옵션**:
   - 의미론적 분석을 위한 OpenAI Vision API 호출
   - 차원 측정을 위한 로컬 비전 파이프라인
4. **결과**: 신뢰도 점수 및 측정값을 포함한 JSON 구조화 출력

### API 키 보안
- API 키는 코드나 버전 관리에 절대 저장되지 않음
- 직접 API 키 입력 UI 제거 (최근 커밋에서 보안 개선)
- 환경 변수 또는 Streamlit secrets에서만 키 로드

### 동적 프롬프트 관리
- `PromptService`를 통한 런타임 프롬프트 생성 및 관리
- 카테고리별 프롬프트 템플릿 시스템
- 관리자 UI를 통한 프롬프트 수정 및 업데이트
- 프롬프트 이력 및 버전 관리

### 검색 제공자 시스템
- 여러 검색 API의 계층적 폴백 시스템 (Google CSE → Bing → HTML 파싱)
- Circuit breaker 패턴으로 실패한 제공자 일시 비활성화
- Rate limiting 및 API 사용량 관리
- 결과 통합 및 중복 제거

### 행정구역 및 링크 관리
- 대한민국 행정구역 데이터의 자동 다운로드 및 업데이트
- 시군구별 대형폐기물 배출신고 홈페이지 자동 발견
- 링크 유효성 검증 및 모니터링
- 배치 작업을 통한 대량 데이터 처리

### 멀티 페이지 아키텍처
- Streamlit 네이티브 멀티페이지 구조 활용
- 페이지별 독립적인 기능 및 권한 관리
- 공통 레이아웃 및 사이드바 컴포넌트
- 페이지 간 상태 공유 및 데이터 전달

### 비전 파이프라인 특성
- 손 기반 스케일 추정은 ~1m 촬영 거리를 가정
- 사용자 설정 가능한 손 너비 및 거리 매개변수
- 거리 기반 스케일링을 위한 원근 보정 적용
- YOLO 라벨에서 폐기물 관리 카테고리로의 매핑

## 작업 기록 관리

**일일 작업 기록 시스템**:
- 매일 작업 시작시 `instructions/claude.YYYYMMDD.md` 파일 확인/생성
- 작업 완료시 해당 파일에 진행사항 업데이트
- 지시사항, 완료 작업, 미완료 작업, 다음 작업 계획 기록

**작업 기록 형식**:
```markdown
# Claude 작업 기록 - YYYY년 MM월 DD일
## 작업 요청사항
## 완료된 작업  
## 진행중인 작업
## 다음 작업 예정
```

**파일 관리**:
- 파일명: `claude.YYYYMMDD.md` (예: claude.20250911.md)
- 위치: `instructions/` 폴더
- 매일 새 파일 생성, 이전 기록 보존

## 페이지별 기능 개요

### 메인 페이지 (app.py)
- 카메라/갤러리를 통한 이미지 입력
- OpenAI Vision API를 통한 이미지 분석
- 동적 프롬프트 선택 및 분석 실행

### 01_district_links.py - 행정구역 링크 관리
- 시군구별 대형폐기물 배출신고 홈페이지 링크 수집
- 검색 제공자를 통한 자동 링크 발견
- 링크 유효성 검증 및 업데이트

### 02_district_config.py - 행정구역 설정
- data.go.kr에서 행정구역 데이터 다운로드
- CSV 파일 파싱 및 JSON 변환
- 행정구역 계층 구조 관리

### 03_district_monitoring.py - 시스템 모니터링
- 배치 작업 상태 모니터링
- 시스템 성능 및 오류 추적
- 알림 및 로그 관리

### 04_prompt_admin.py - 프롬프트 관리
- 동적 프롬프트 생성 및 수정
- 프롬프트 템플릿 관리
- 카테고리별 프롬프트 설정

### 91_tunnel_management.py - 터널 관리
- Cloudflared 터널 상태 관리
- 터널 시작/중지/재시작 기능
- 터널 설정 및 모니터링

### 99_logs.py - 로그 뷰어
- 애플리케이션 로그 실시간 조회
- 로그 레벨별 필터링
- 로그 다운로드 및 분석 도구

## 개발자 가이드라인

### 새 컴포넌트 추가 시
1. `src/components/base.py`의 `BaseComponent` 상속
2. `app_context`를 통한 서비스 접근: `self.get_service('service_name')`
3. `render()` 메서드 구현으로 UI 렌더링
4. 타입 힌트 및 docstring 추가

### 새 서비스 추가 시
1. `src/services/` 디렉토리에 서비스 클래스 생성
2. `src/core/service_factory.py`에 서비스 등록
3. 필요시 `src/core/feature_registry.py`에 기능 등록
4. 설정이 필요한 경우 `src/core/config.py`에 설정 클래스 추가

### 새 페이지 추가 시
1. `pages/` 디렉토리에 `NN_page_name.py` 형식으로 파일 생성
2. Streamlit 페이지 규칙에 따라 `st.set_page_config()` 호출
3. 필요시 `src/pages/` 디렉토리에 페이지 비즈니스 로직 클래스 생성
4. 공통 레이아웃은 `src/layouts/main_layout.py` 활용