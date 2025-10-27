# 세부내역 콘텐츠 프롬프트 관리 가이드

## 개요

세부내역 콘텐츠 추출(배출정보, 수수료 정보) 기능의 AI 프롬프트는 더 이상 `DetailContentService`에 하드코딩되지 않습니다. 대신 **프롬프트 관리 시스템(PromptService)에 등록**되어 관리됩니다.

## 아키텍처

```
Application Initialization
    ↓
ApplicationFactory.create_application()
    ↓
_initialize_domain_services(app_context)
    ↓
initialize_detail_content_service(app_context)
    ↓
register_detail_content_prompts(prompt_service)
    ↓
PromptService에 등록 + PromptFeatureRegistry 업데이트
    ↓
DetailContentService 사용 시 프롬프트 템플릿 로드
```

## 파일 구조

### 1. 프롬프트 템플릿 정의
**파일**: `src/domains/infrastructure/services/detail_content_prompts.py`

```python
# 배출정보 추출 프롬프트 템플릿
def get_info_extraction_prompt_template() -> str:
    """배출정보 추출 프롬프트 템플릿 (변수: {district_context}, {content})"""

# 수수료 정보 추출 프롬프트 템플릿
def get_fee_extraction_prompt_template() -> str:
    """수수료 정보 추출 프롬프트 템플릿 (변수: {district_context}, {content})"""

# 프롬프트 시스템에 등록
def register_detail_content_prompts(prompt_service) -> Dict[str, str]:
    """프롬프트 서비스에 프롬프트 등록"""
```

**등록되는 프롬프트**:
- `detail_extraction_disposal_info`: 배출정보 추출용
- `detail_extraction_fee_info`: 수수료 정보 추출용

### 2. 초기화 로직
**파일**: `src/domains/infrastructure/services/detail_content_initialization.py`

```python
def initialize_detail_content_service(app_context=None) -> Dict[str, Optional[str]]:
    """
    애플리케이션 시작 시 호출되는 초기화 함수
    - PromptService 획득
    - 프롬프트 등록
    - PromptFeatureRegistry 업데이트
    """

def is_detail_content_feature_enabled(app_context=None) -> bool:
    """세부내역 기능 활성화 여부 확인"""
```

### 3. 서비스 통합
**파일**: `src/domains/infrastructure/services/detail_content_service.py`

**변경 사항**:
```python
# Before (하드코딩)
def _get_info_extraction_prompt(self, content: str, ...):
    return f"""당신은 대형폐기물 배출 정보 분석 전문가입니다.
    ... (긴 프롬프트 문자열)
    """

# After (템플릿 사용)
def _get_info_extraction_prompt(self, content: str, ...):
    from src.domains.infrastructure.services.detail_content_prompts import (
        get_info_extraction_prompt_template
    )
    template = get_info_extraction_prompt_template()
    return template.format(
        district_context=district_context,
        content=content[:3000]
    )
```

### 4. 애플리케이션 초기화
**파일**: `src/app/core/app_factory.py`

**변경 사항**:
```python
def create_application():
    # ... 기본 초기화 ...

    # 신규: 도메인 서비스 초기화
    ApplicationFactory._initialize_domain_services(app_context)

    return app_context

@staticmethod
def _initialize_domain_services(app_context):
    """도메인별 서비스 초기화 및 프롬프트 등록"""
    try:
        from src.domains.infrastructure.services.detail_content_initialization import (
            initialize_detail_content_service
        )
        prompt_ids = initialize_detail_content_service(app_context)
        if prompt_ids:
            logger.info(f"Detail content prompts registered: {prompt_ids}")
    except Exception as e:
        logger.warning(f"Domain service initialization failed: {e}")
```

## 등록되는 기능 (Features)

### 배출정보 세부내역
**Feature ID**: `detail_content_disposal_info`
- 이름: "세부내역 배출정보 관리"
- 설명: "지역별 대형폐기물 배출정보를 자동으로 추출하고 관리합니다"
- 카테고리: `infrastructure`
- 필수 서비스: `openai_service`
- 상태: 활성화됨 (default)

### 수수료 세부내역
**Feature ID**: `detail_content_fee_info`
- 이름: "세부내역 수수료 관리"
- 설명: "지역별 대형폐기물 수수료 정보를 자동으로 추출하고 관리합니다"
- 카테고리: `infrastructure`
- 필수 서비스: `openai_service`
- 상태: 활성화됨 (default)

## 프롬프트 변수

### `{district_context}`
- 지역 정보가 제공된 경우: `"(지역: 서울특별시 강남구)"`
- 제공되지 않은 경우: `""`

### `{content}`
- URL/PDF에서 추출한 원본 콘텐츠
- 최대 3000자로 제한

## 사용 흐름

### 1. 애플리케이션 시작 (자동)
```
app.py 실행
  ↓
ApplicationFactory.create_application()
  ↓
_initialize_domain_services() 호출
  ↓
initialize_detail_content_service() 호출
  ↓
PromptService.create_prompt() 호출
  ↓
프롬프트 저장 (data/prompts/templates/{uuid}.json)
  ↓
PromptFeatureRegistry 업데이트
```

### 2. 세부내역 추출 (사용자가 호출)
```
DetailContentUI.show() 호출
  ↓
자동 추출 또는 수동 입력
  ↓
DetailContentService.generate_detail_content() 호출
  ↓
_get_info_extraction_prompt() 또는 _get_fee_extraction_prompt() 호출
  ↓
프롬프트 템플릿 로드 (detail_content_prompts.py에서)
  ↓
OpenAI API 호출
  ↓
결과 반환
```

## 저장 위치

프롬프트 관련 파일들:

```
data/
├── prompts/
│   ├── features/
│   │   ├── prompt_feature_registry.json  # 기능 정의
│   │   └── feature_config.json
│   ├── templates/
│   │   ├── {uuid1}.json  # detail_extraction_disposal_info
│   │   ├── {uuid2}.json  # detail_extraction_fee_info
│   │   └── ...
│   ├── mappings/
│   │   └── feature_mappings.json  # 기능-프롬프트 매핑
│   └── backups/
```

## 관리

### 프롬프트 수정

프롬프트를 수정하려면:

1. **프롬프트 템플릿 파일 직접 수정**:
   - `data/prompts/templates/{uuid}.json` 파일을 직접 편집
   - JSON 형식 유지 필수

2. **코드에서 템플릿 수정**:
   - `src/domains/infrastructure/services/detail_content_prompts.py` 수정
   - 다음 실행 시 새 프롬프트로 등록됨

### 기능 활성화/비활성화

```python
from src.domains.infrastructure.services.detail_content_initialization import (
    is_detail_content_feature_enabled
)

if is_detail_content_feature_enabled(app_context):
    # 세부내역 기능 사용 가능
    pass
```

또는 UI에서:
```python
app_context.is_feature_enabled('detail_content_disposal_info')
app_context.is_feature_enabled('detail_content_fee_info')
```

## 장점

### 이전 (하드코딩)
- ❌ 프롬프트 변경 시 코드 수정 필요
- ❌ 프롬프트 버전 관리 어려움
- ❌ 관리자 UI에서 관리 불가능
- ❌ 다른 프롬프트 관리 시스템과 불일치

### 현재 (등록된 시스템)
- ✅ 프롬프트 중앙화 관리
- ✅ 버전 관리 지원 (created_by, created_at 등)
- ✅ 향후 관리자 UI 통합 가능
- ✅ 통일된 프롬프트 관리 시스템
- ✅ 기능별 활성화/비활성화 제어
- ✅ 메타데이터 및 태그 지원

## 확장

새로운 프롬프트를 추가하려면:

1. **프롬프트 템플릿 함수 추가**:
```python
# detail_content_prompts.py에 추가
def get_new_extraction_prompt_template() -> str:
    return """..."""
```

2. **등록 로직 추가**:
```python
# register_detail_content_prompts() 함수에 추가
new_prompt = prompt_service.create_prompt(
    name="detail_extraction_new_type",
    description="새로운 타입 추출",
    category=PromptCategory.CUSTOM,
    template=get_new_extraction_prompt_template(),
    # ...
)
```

3. **기능 등록**:
```python
registry.register_feature(
    feature_id="detail_content_new_type",
    name="세부내역 새로운 타입",
    # ...
)
```

## 트러블슈팅

### 프롬프트가 등록되지 않음

1. PromptService가 활성화되어 있는지 확인
2. `data/prompts/` 디렉토리 권한 확인
3. 로그에서 "Detail content prompts registered" 메시지 확인

### 프롬프트가 최신이 아님

- `data/prompts/templates/` 폴더 삭제 후 애플리케이션 재시작
- 또는 특정 프롬프트 파일 삭제

### 기능이 작동하지 않음

```python
# 디버깅 코드
from src.app.core.app_factory import get_application
app = get_application()

# 기능 확인
print(app.is_feature_enabled('detail_content_disposal_info'))
print(app.is_feature_enabled('detail_content_fee_info'))

# 서비스 확인
service = app.get_service('detail_content_service')
print(service is not None)
```

## 참고 문서

- `instructions/development_guidelines.md` - 일반 개발 가이드
- `src/domains/prompts/services/prompt_service.py` - PromptService 구현
- `src/app/core/prompt_feature_registry.py` - PromptFeatureRegistry 구현
