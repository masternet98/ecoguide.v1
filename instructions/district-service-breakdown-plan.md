# district_service.py 분해 계획서

## 📊 분석 결과 요약

### 현재 상태
- **총 라인 수**: 2,217줄
- **총 함수 수**: 22개
- **함수별 평균**: 99.5줄
- **가장 큰 함수**: process_district_csv (299줄)
- **가장 작은 함수**: get_last_update_info (28줄)

### 함수 의존성 관계
복잡한 호출 체인이 존재하지만, 기능별로 자연스럽게 분리 가능

## 🎯 4개 파일 분해 전략

### 1. district_loader.py (데이터 로딩)
**책임**: CSV 파싱, 웹 다운로드, 파라미터 추출

**포함할 함수 (10개)**:
```python
# CSV 파싱 관련
- manual_csv_parse(csv_string: str) → Optional[pd.DataFrame]  # 82줄
- validate_csv_data(data: bytes, ...) → Dict[str, Any]        # 170줄
- process_district_csv(csv_content: bytes, ...) → Dict[str, Any]  # 299줄

# 웹 다운로드 관련
- download_district_data_from_web(config: ...) → Dict[str, Any]   # 121줄
- extract_download_params(soup: BeautifulSoup) → Dict[str, Any]   # 129줄

# 다양한 다운로드 시도 방법들
- try_javascript_download(session: ...) → Dict[str, Any]          # 178줄
- try_direct_file_download(session: ...) → Dict[str, Any]         # 30줄
- try_direct_links(session: ...) → Dict[str, Any]                 # 45줄
- try_api_endpoints(session: ...) → Dict[str, Any]                # 40줄
- try_fallback_download(session: ...) → Dict[str, Any]            # 36줄
```

**예상 라인 수**: ~1,130줄
**외부 의존성**: pandas, requests, BeautifulSoup, logging, config

### 2. district_cache.py (파일 관리 및 캐시)
**책임**: 파일 목록, 삭제, 미리보기, 최신 파일 관리

**포함할 함수 (5개)**:
```python
# 파일 목록 및 조회
- get_district_files(config: ...) → List[Dict[str, Any]]          # 39줄
- get_latest_district_file(config: ...) → Optional[str]           # 84줄
- preview_district_file(file_path: str, ...) → Dict[str, Any]     # 32줄

# 파일 삭제 관리
- delete_district_file(file_path: str, ...) → Dict[str, Any]      # 60줄
- delete_all_district_files(config: ...) → Dict[str, Any]         # 66줄
```

**예상 라인 수**: ~281줄
**외부 의존성**: logging, config, requests (미리보기용)

### 3. district_validator.py (데이터 검증)
**책임**: 데이터 정규화, 검증 로직

**포함할 함수 (1개 + α)**:
```python
# 데이터 정규화
- _normalize_admin_field(field_name: str, ...) → str             # 214줄

# 추가로 validation 관련 헬퍼 함수들도 여기로 이동 예정
```

**예상 라인 수**: ~350줄 (헬퍼 함수들 추가 고려)
**외부 의존성**: config

### 4. district_api.py (통합 인터페이스 및 업데이트 관리)
**책임**: 외부 인터페이스 제공, 업데이트 관리, 기존 호환성 유지

**포함할 함수 (6개)**:
```python
# 업데이트 관리
- check_data_go_kr_update(url: str, ...) → Dict[str, Any]         # 82줄
- get_last_update_info(config: ...) → Dict[str, Any]              # 28줄
- save_update_info(modification_date: str, ...)                   # 28줄
- auto_update_district_data(config: ...) → Dict[str, Any]         # 221줄
- clear_update_info(config: ...) → Dict[str, Any]                 # 46줄
- force_update_district_data(config: ...) → Dict[str, Any]        # 158줄

# 통합 인터페이스 (다른 모듈들을 조합)
- DistrictService 클래스 (새로 생성)
```

**예상 라인 수**: ~563줄
**외부 의존성**: logging, config, requests, 위 3개 모듈들

## 🔗 모듈 간 의존성 설계

### Import 구조
```python
# district_loader.py
from src.core.logger import logger, log_info, log_warning, log_error
from src.core.config import DistrictConfig
from .file_source_validator import validate_downloaded_file, detect_website_changes

# district_cache.py
from src.core.logger import logger, log_info, log_warning, log_error
from src.core.config import DistrictConfig

# district_validator.py
from src.core.config import DistrictConfig

# district_api.py
from src.core.logger import logger, log_info, log_warning, log_error
from src.core.config import DistrictConfig
from .district_loader import (
    process_district_csv, download_district_data_from_web, validate_csv_data
)
from .district_cache import (
    get_district_files, get_latest_district_file, preview_district_file,
    delete_district_file, delete_all_district_files
)
from .district_validator import _normalize_admin_field
```

### 기존 코드 호환성 유지
```python
# district_api.py에서 기존 인터페이스 제공
class DistrictService:
    """기존 district_service.py와 동일한 인터페이스 제공"""

    def __init__(self, config: Optional[DistrictConfig] = None):
        self.config = config or DistrictConfig()

    # 기존 함수들을 메서드로 래핑
    def process_district_csv(self, *args, **kwargs):
        from .district_loader import process_district_csv
        return process_district_csv(*args, **kwargs)

    def get_district_files(self, *args, **kwargs):
        from .district_cache import get_district_files
        return get_district_files(*args, **kwargs)

    # ... 모든 기존 함수들을 동일하게 래핑
```

## ⚠️ 주요 고려사항

### 1. 순환 import 방지
- **문제**: 일부 함수들이 서로를 호출함
- **해결**: 공통으로 필요한 함수들은 district_validator에 배치
- **예시**: `_normalize_admin_field`는 여러 모듈에서 사용

### 2. 설정 의존성
- **모든 모듈이 DistrictConfig 의존**
- **해결**: 각 모듈에서 독립적으로 import하되, 기본값 제공

### 3. 로깅 의존성
- **대부분 함수가 로깅 사용**
- **해결**: 각 모듈에서 필요한 로깅 함수만 import

### 4. 외부 호출 호환성
- **기존 코드에서 직접 함수 호출하는 부분 존재 가능**
- **해결**: district_api.py에서 모든 기존 함수를 다시 export

## 🎯 분해 순서 (안전한 단계별 접근)

### Step 1: district_validator.py 생성
- 가장 독립적인 `_normalize_admin_field` 먼저 분리
- 다른 모듈들이 이를 import하도록 설정

### Step 2: district_cache.py 생성
- 파일 관리 함수들 분리 (외부 의존성 적음)
- 독립적으로 동작 가능

### Step 3: district_loader.py 생성
- 가장 복잡한 데이터 로딩 로직 분리
- district_validator 의존성 추가

### Step 4: district_api.py 생성 및 통합
- 기존 인터페이스 유지하면서 모든 모듈 통합
- 기존 district_service.py를 이것으로 교체

## 🧪 테스트 전략

### 각 단계별 테스트
1. **새 모듈 생성 후**: `python -m py_compile` 문법 확인
2. **함수 이동 후**: 간단한 import 테스트
3. **전체 통합 후**: Streamlit 앱 정상 실행 확인
4. **최종 확인**: 행정구역 관련 모든 페이지 동작 확인

### 롤백 계획
- 각 단계마다 Git 커밋
- 문제 발생 시 `.backup` 파일에서 즉시 복원
- 최악의 경우 `git reset --hard HEAD~1`

---

**작성일**: 2025-09-21
**예상 소요시간**: Day 2-5 (4일)
**안전도**: 높음 (각 단계별 안전장치 완비)**