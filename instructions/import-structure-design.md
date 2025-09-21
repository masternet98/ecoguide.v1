# Import 구조 설계 및 호환성 계획

## 📊 현재 외부 사용 현황 분석

### 외부에서 district_service를 사용하는 파일들:
1. **pages/01_district_config.py** - 행정구역 설정 페이지
2. **src/core/service_factory.py** - 서비스 팩토리
3. **src/services/location_service.py** - 위치 서비스

### 구체적 사용 패턴:

#### 1. pages/01_district_config.py
```python
# 현재 import 패턴
from src.services.district_service import (
    # 여러 함수들을 직접 import
)

# 사용되는 함수들:
- get_last_update_info
- check_data_go_kr_update
```

#### 2. src/core/service_factory.py
```python
# 서비스 팩토리 등록
module_path='src.services.district_service'
```

#### 3. src/services/location_service.py
```python
# 지연 import 사용
from src.services.district_service import get_latest_district_file
```

## 🎯 호환성 유지 전략

### 방법 1: district_api.py에서 모든 함수 re-export (권장)
```python
# src/services/district_api.py

# 새로운 모듈들에서 함수 import
from .district_loader import (
    manual_csv_parse, validate_csv_data, process_district_csv,
    download_district_data_from_web, extract_download_params,
    try_javascript_download, try_direct_file_download,
    try_direct_links, try_api_endpoints, try_fallback_download
)

from .district_cache import (
    get_district_files, get_latest_district_file, preview_district_file,
    delete_district_file, delete_all_district_files
)

from .district_validator import _normalize_admin_field

# 업데이트 관리 함수들 (이 파일에서 직접 구현)
def check_data_go_kr_update(...):
    pass

def get_last_update_info(...):
    pass

# 등등...

# 모든 함수를 __all__에 포함하여 export
__all__ = [
    # 데이터 로딩
    'manual_csv_parse', 'validate_csv_data', 'process_district_csv',
    'download_district_data_from_web', 'extract_download_params',
    'try_javascript_download', 'try_direct_file_download',
    'try_direct_links', 'try_api_endpoints', 'try_fallback_download',

    # 파일 관리
    'get_district_files', 'get_latest_district_file', 'preview_district_file',
    'delete_district_file', 'delete_all_district_files',

    # 데이터 검증
    '_normalize_admin_field',

    # 업데이트 관리
    'check_data_go_kr_update', 'get_last_update_info', 'save_update_info',
    'auto_update_district_data', 'clear_update_info', 'force_update_district_data'
]
```

### 방법 2: 기존 district_service.py를 래퍼로 유지
```python
# src/services/district_service.py (기존 파일을 완전 교체)

# 모든 함수를 새로운 모듈들에서 import하여 re-export
from .district_api import *

# 이렇게 하면 기존 import 구문들이 모두 동작함
```

## 🔧 단계별 Import 마이그레이션 계획

### Phase 1: 새 모듈들 생성 (Day 2-4)
1. **district_validator.py** 생성
2. **district_cache.py** 생성
3. **district_loader.py** 생성
4. 각 모듈별 독립적 테스트

### Phase 2: district_api.py 통합 (Day 5)
1. **district_api.py** 생성
2. 모든 기존 함수를 re-export
3. 기존 district_service.py를 district_api.py로 교체

### Phase 3: 외부 파일 업데이트 (필요시)
1. **service_factory.py** 업데이트
   ```python
   # 변경 전
   module_path='src.services.district_service'
   # 변경 후
   module_path='src.services.district_api'
   ```

2. **기타 import 문 정리** (선택사항)
   - 성능 최적화를 위해 직접 모듈에서 import로 변경 가능
   - 하지만 호환성을 위해 기존 방식 유지도 가능

## 📁 새로운 파일 구조

```
src/services/
├── district_service.py.backup          # 백업 파일
├── district_validator.py               # 새로 생성: 데이터 검증
├── district_cache.py                   # 새로 생성: 파일 관리
├── district_loader.py                  # 새로 생성: 데이터 로딩
├── district_api.py                     # 새로 생성: 통합 API
└── district_service.py                 # 교체: district_api.py 내용으로
```

## 🔗 각 모듈별 Import 구조

### district_validator.py
```python
"""데이터 검증 및 정규화"""
from src.core.config import DistrictConfig

def _normalize_admin_field(field_name: str, value: str, config: Optional[DistrictConfig] = None) -> str:
    pass
```

### district_cache.py
```python
"""파일 관리 및 캐시"""
import os
import json
from typing import Dict, List, Any, Optional
from src.core.logger import logger, log_info, log_warning, log_error
from src.core.config import DistrictConfig

def get_district_files(config: Optional[DistrictConfig] = None) -> List[Dict[str, Any]]:
    pass

def get_latest_district_file(config: Optional[DistrictConfig] = None) -> Optional[str]:
    pass

# 등등...
```

### district_loader.py
```python
"""데이터 로딩 및 CSV 처리"""
import csv
import io
import re
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup

from src.core.logger import logger, log_info, log_warning, log_error
from src.core.config import DistrictConfig
from .file_source_validator import validate_downloaded_file, detect_website_changes
from .district_validator import _normalize_admin_field

def manual_csv_parse(csv_string: str) -> Optional[pd.DataFrame]:
    pass

def process_district_csv(csv_content: bytes, output_filename: Optional[str] = None, config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    pass

# 등등...
```

### district_api.py
```python
"""통합 API 및 업데이트 관리"""
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.core.logger import logger, log_info, log_warning, log_error
from src.core.config import DistrictConfig

# 다른 모듈들에서 함수 import
from .district_loader import (
    manual_csv_parse, validate_csv_data, process_district_csv,
    download_district_data_from_web, extract_download_params,
    try_javascript_download, try_direct_file_download,
    try_direct_links, try_api_endpoints, try_fallback_download
)

from .district_cache import (
    get_district_files, get_latest_district_file, preview_district_file,
    delete_district_file, delete_all_district_files
)

from .district_validator import _normalize_admin_field

# 업데이트 관리 함수들 직접 구현
def check_data_go_kr_update(url: str = None, config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    pass

# 모든 함수 re-export
__all__ = [
    # ... 모든 함수 목록
]
```

## ⚠️ 잠재적 위험 요소 및 대응

### 1. Circular Import 위험
**위험**: district_loader가 district_validator를 import하고, 반대로도 의존성이 생길 수 있음
**대응**:
- district_validator는 순수 유틸리티 함수만 포함
- 다른 모듈에 의존하지 않도록 설계

### 2. Import 경로 변경
**위험**: service_factory에서 모듈 경로 변경 필요할 수 있음
**대응**:
- 기존 district_service.py를 유지하되 내용만 교체
- 또는 service_factory만 수정

### 3. 성능 영향
**위험**: 여러 모듈로 분리하면서 import 오버헤드 증가 가능
**대응**:
- 실제 사용 시점에서 지연 import 사용
- 필요한 함수만 선택적 import

## 🧪 호환성 테스트 계획

### 1. 기본 Import 테스트
```python
# 이 import들이 모두 정상 동작해야 함
from src.services.district_service import get_last_update_info
from src.services.district_service import check_data_go_kr_update
from src.services.district_service import get_latest_district_file
```

### 2. 페이지 동작 테스트
- **01_district_config.py** 페이지 정상 로딩
- 행정구역 업데이트 기능 정상 동작
- 파일 업로드 및 처리 정상 동작

### 3. 서비스 팩토리 테스트
- `get_service('district_service')` 정상 동작

---

**결론**: 호환성 유지를 위해 기존 district_service.py 파일은 유지하되, 내용을 district_api.py로 교체하는 방식을 채택합니다. 이렇게 하면 기존 코드 수정 없이도 모든 기능이 정상 동작할 것입니다.