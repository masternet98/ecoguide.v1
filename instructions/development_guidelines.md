# EcoGuide.v1 종합 개발 가이드라인

## 📖 개요

이 문서는 EcoGuide.v1 프로젝트의 **전체적인 개발 철학과 실용적인 가이드라인**을 제공합니다. 단순한 코딩 규칙을 넘어서 프로젝트의 목적, 설계 철학, 그리고 실제 개발 시 마주하는 다양한 상황에 대한 지침을 담고 있습니다.

---

## 🎯 프로젝트 비전과 목표

### 프로젝트 목적
EcoGuide.v1은 **AI 기반 대형폐기물 관리 도우미**로서:
- 시민들이 쉽게 대형폐기물을 식별하고 배출 방법을 안내
- 지자체별 배출 규정과 연결하여 정확한 정보 제공
- 확장 가능한 AI 플랫폼으로 다양한 환경 관련 서비스 통합

### 설계 철학
1. **사용자 중심**: 복잡한 행정 절차를 단순하게
2. **확장성**: 새로운 지역, 새로운 기능 쉽게 추가
3. **신뢰성**: 정확한 정보와 안정적인 서비스
4. **유지보수성**: 장기적으로 관리 가능한 코드베이스

---

## 🏗️ 아키텍처 개요와 설계 원칙

### 도메인 기반 아키텍처 선택 이유

**문제**: 기존의 레이어드 아키텍처(services/, components/)는 기능이 늘어날수록 파일이 무작정 증가하여 관리가 어려워짐

**해결책**: 비즈니스 도메인 중심으로 코드를 구조화하여 관련 기능들을 함께 관리

### 최종 디렉터리 구조
```
src/
├─ app/                     # 애플리케이션 계층
│  ├─ core/                # 핵심 시스템 (팩토리, 오류처리 등)
│  ├─ config/              # 설정 관리
│  └─ layouts/             # 공용 레이아웃
├─ domains/                # 도메인 계층 (비즈니스 로직)
│  ├─ analysis/           # 이미지 분석 도메인
│  │  ├─ services/        # 비즈니스 로직
│  │  ├─ ui/             # UI 컴포넌트
│  │  └─ vision_types.py # 타입 정의
│  ├─ prompts/           # 프롬프트 관리 도메인
│  ├─ district/          # 행정구역 데이터 도메인
│  ├─ monitoring/        # 시스템 모니터링 도메인
│  └─ infrastructure/    # 인프라 서비스 도메인
├─ pages/                # Streamlit 멀티페이지
├─ layouts/              # 메인 레이아웃
└─ components/           # 래거시 호환 계층
```

## 🚫 절대 금지 사항 (NEVER DO)

### 1. 잘못된 디렉터리 사용
- ❌ `src/services/`에 새로운 서비스 생성
- ❌ `src/core/`에 새로운 모듈 생성
- ❌ 도메인 외부에 비즈니스 로직 배치

### 2. 잘못된 import 경로
- ❌ `from src.services.*` 사용
- ❌ `from src.core.config` 사용 (올바름: `from src.app.core.config`)
- ❌ 도메인 간 직접 서비스 import (ServiceFactory 사용 필수)

### 3. 아키텍처 원칙 위반
- ❌ 도메인 간 순환 참조 생성
- ❌ UI 로직을 서비스에 포함
- ❌ 비즈니스 로직을 UI에 포함

### 각 도메인의 역할과 책임

#### 1. Analysis Domain (이미지 분석)
- **목적**: 사용자가 업로드한 이미지를 AI로 분석
- **핵심 기능**: OpenAI Vision API 연동, 로컬 비전 파이프라인
- **확장 방향**: 더 정교한 객체 인식, 크기 측정 개선

#### 2. Prompts Domain (프롬프트 관리)
- **목적**: AI에게 전달할 프롬프트를 관리하고 최적화
- **핵심 기능**: 동적 프롬프트 생성, 템플릿 관리, A/B 테스트
- **확장 방향**: 지역별 특화 프롬프트, 성능 분석

#### 3. District Domain (행정구역 데이터)
- **목적**: 전국 지자체의 대형폐기물 배출 규정 관리
- **핵심 기능**: 행정구역 데이터 동기화, 배출 링크 수집
- **확장 방향**: 실시간 규정 변경 감지, 배출 비용 계산

#### 4. Monitoring Domain (시스템 모니터링)
- **목적**: 시스템 상태 추적 및 문제 조기 발견
- **핵심 기능**: 성능 모니터링, 오류 추적, 알림 발송
- **확장 방향**: 예측적 모니터링, 자동 복구

#### 5. Infrastructure Domain (인프라 서비스)
- **목적**: 다른 도메인들이 필요로 하는 공통 인프라 제공
- **핵심 기능**: 검색, 파일 관리, 네트워크 터널, 배치 작업
- **확장 방향**: 클라우드 연동, 캐싱, 보안

---

## ✅ 필수 준수 사항 (MUST DO)

### 1. 새로운 기능 개발 시

#### Step 1: 도메인 분류
새로운 기능을 개발할 때 반드시 다음 기준으로 도메인을 결정:

```python
# 도메인 분류 체크리스트
if "이미지 분석" or "AI 비전" or "OpenAI":
    domain = "analysis"
elif "프롬프트" or "AI 텍스트" or "템플릿":
    domain = "prompts"
elif "행정구역" or "위치" or "지역":
    domain = "district"
elif "모니터링" or "알림" or "로깅":
    domain = "monitoring"
elif "검색" or "터널" or "배치" or "파일관리":
    domain = "infrastructure"
else:
    # 새로운 도메인 생성 필요 - 아키텍트와 상의
    raise Exception("도메인 분류 필요")
```

#### Step 2: 파일 배치
```python
# 올바른 파일 배치
src/domains/{domain}/
├─ services/           # 비즈니스 로직만
│  ├─ {feature}_service.py
│  ├─ {feature}_manager.py
│  └─ {feature}_processor.py
├─ ui/                # UI 컴포넌트만
│  ├─ {feature}_ui.py
│  ├─ {feature}_dashboard.py
│  └─ {feature}_form.py
└─ types.py           # 타입 정의 (선택적)
```

#### Step 3: Import 패턴
```python
# ✅ 올바른 import 패턴
from src.app.core.config import Config
from src.domains.{domain}.services.{service} import {ServiceClass}

# ✅ ServiceFactory를 통한 서비스 접근
def some_function(app_context):
    service = app_context.get_service('service_name')
    return service.method()

# ❌ 잘못된 직접 import
from src.domains.other_domain.services.other_service import OtherService
```

## 🛠️ 코드 패턴 및 템플릿

### 서비스 클래스 구조
```python
# src/domains/{domain}/services/{feature}_service.py
"""
{Feature} 도메인의 핵심 비즈니스 로직을 담당하는 서비스입니다.
"""
from typing import Any, Dict, Optional
from src.app.core.base_service import BaseService
from src.app.core.config import Config

class {Feature}Service(BaseService):
    """
    {Feature} 관련 비즈니스 로직을 처리하는 서비스입니다.

    이 서비스는 다음 책임을 가집니다:
    1. {기능 1}
    2. {기능 2}
    3. {기능 3}
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self.feature_config = config.{domain}

    def process_{feature}(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        {기능} 처리 메인 메서드

        Args:
            data: 처리할 데이터

        Returns:
            처리 결과
        """
        # 비즈니스 로직만 포함
        pass
```

### UI 컴포넌트 구조
```python
# src/domains/{domain}/ui/{feature}_ui.py
"""
{Feature} 도메인의 UI 컴포넌트입니다.
"""
import streamlit as st
from src.app.core.base_component import BaseUIComponent

class {Feature}UI(BaseUIComponent):
    """
    {Feature} 관련 UI를 담당하는 컴포넌트입니다.
    """

    def __init__(self, app_context):
        super().__init__(app_context)
        self.service = self.get_service('{feature}_service')

    def render(self) -> None:
        """UI 렌더링 메서드"""
        # UI 로직만 포함
        pass
```

### ServiceFactory 등록
새로운 서비스를 만들 때 반드시 ServiceFactory에 등록:

```python
# src/app/core/service_factory.py의 SERVICE_DOMAIN_MAP에 추가
SERVICE_DOMAIN_MAP = {
    # 기존 서비스들...
    '{new_service_name}': '{domain}',  # 새 서비스 추가
}
```

### 페이지 개발 규칙
```python
# pages/{number}_{page_name}.py
"""
{Page} 페이지입니다.
"""
import streamlit as st
from src.app.core.config import load_config
from src.domains.{domain}.ui.{feature}_ui import {Feature}UI

# 페이지 설정 (필수)
st.set_page_config(
    page_title="{Page Title} - EcoGuide",
    page_icon="🔧",
    layout="wide"
)

# Config 로드 (필수)
config = load_config()

# UI 컴포넌트 사용
ui_component = {Feature}UI(app_context)
ui_component.render()
```

---

## 📋 개발 시나리오별 가이드

### 시나리오 1: 새로운 기능 추가하기

#### 예시: "음성 인식 기능" 추가

1. **도메인 분류 질문**:
   - 이 기능이 주로 어떤 비즈니스 가치를 제공하는가?
   - 기존 도메인 중 어디와 가장 밀접한가?
   - 완전히 새로운 영역인가?

2. **답변 예시**:
   - 음성으로 대형폐기물을 설명하면 텍스트로 변환 → Analysis 도메인
   - 이유: 사용자 입력을 AI가 이해할 수 있게 변환하는 것이 핵심

3. **구현 위치**:
   ```
   src/domains/analysis/
   ├─ services/
   │  ├─ vision_service.py     # 기존
   │  ├─ openai_service.py     # 기존
   │  └─ speech_service.py     # 새로 추가
   └─ ui/
      ├─ image_input.py        # 기존
      └─ voice_input.py        # 새로 추가
   ```

#### 예시: "사용자 계정 관리" 추가

1. **도메인 분류 질문**:
   - 기존 5개 도메인과는 완전히 다른 영역
   - 새로운 도메인이 필요한가?

2. **판단 기준**:
   - 3개 이상의 서비스/UI가 필요한가? → Yes
   - 독립적으로 발전할 가능성이 있는가? → Yes
   - 다른 도메인들이 의존할 가능성이 있는가? → Yes

3. **결정**: 새로운 `user` 도메인 생성

### 시나리오 2: 기존 기능 개선하기

#### 예시: "이미지 분석 속도 개선"

1. **영향 범위 분석**:
   - 주로 영향받는 도메인: Analysis
   - 간접적 영향: Monitoring (성능 지표)

2. **접근 방법**:
   ```python
   # src/domains/analysis/services/vision_service.py
   class VisionService:
       def analyze_image_fast(self, image_data):
           # 새로운 빠른 분석 방법
           pass

       def analyze_image(self, image_data):
           # 기존 방법 유지 (하위 호환성)
           pass
   ```

3. **모니터링 연동**:
   ```python
   # src/domains/monitoring/services/performance_service.py
   def track_analysis_performance(self, analysis_time, method):
       # 성능 지표 수집
   ```

### 시나리오 3: 외부 서비스 연동하기

#### 예시: "새로운 AI 모델 API 연동"

1. **기존 패턴 확인**:
   - OpenAI API 연동이 어떻게 구현되어 있는지 참고
   - 유사한 패턴으로 구현하여 일관성 유지

2. **설정 관리**:
   ```python
   # src/app/core/config.py
   @dataclass
   class Config:
       # 기존 설정들...
       new_ai_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('NEW_AI_API_KEY'))
       new_ai_model: str = "default-model"
   ```

3. **서비스 구현**:
   ```python
   # src/domains/analysis/services/new_ai_service.py
   class NewAIService(BaseService):
       def __init__(self, config: Config):
           super().__init__(config)
           self.api_key = config.new_ai_api_key
   ```

---

## 🚦 의사결정 가이드라인

### 새로운 파일을 어디에 둘까?

#### 1단계: 도메인 식별
```python
def identify_domain(feature_description):
    """기능 설명을 바탕으로 도메인을 식별합니다."""

    # 핵심 질문들
    questions = [
        "이 기능의 주된 목적이 무엇인가?",
        "사용자에게 어떤 가치를 제공하는가?",
        "어떤 데이터를 주로 다루는가?",
        "기존 어떤 기능과 가장 밀접한가?"
    ]

    # 키워드 기반 분류 (참고용)
    keywords_map = {
        "analysis": ["이미지", "분석", "AI", "비전", "인식", "측정"],
        "prompts": ["프롬프트", "템플릿", "텍스트", "지시사항"],
        "district": ["행정구역", "지역", "시군구", "배출", "규정"],
        "monitoring": ["모니터링", "추적", "알림", "성능", "로그"],
        "infrastructure": ["검색", "파일", "네트워크", "시스템", "유틸리티"]
    }

    # 실제로는 맥락과 목적을 고려하여 판단
```

#### 2단계: 파일 유형 결정
```python
def decide_file_type(functionality):
    """기능의 성격에 따라 파일 유형을 결정합니다."""

    if "비즈니스 로직" or "외부 API":
        return "services/"
    elif "UI 컴포넌트" or "사용자 인터페이스":
        return "ui/"
    elif "데이터 타입" or "상수":
        return "types.py"
    else:
        return "unclear - 재검토 필요"
```

### 기존 코드를 수정할까 새로 만들까?

#### 수정하는 경우 (권장)
- 동일한 도메인 내에서 유사한 기능
- 기존 인터페이스를 확장하는 경우
- 성능 개선이나 버그 수정

#### 새로 만드는 경우
- 완전히 다른 비즈니스 로직
- 기존 코드가 너무 복잡해질 우려
- 독립적으로 테스트가 필요한 경우

### 의존성을 어떻게 관리할까?

#### 원칙
1. **도메인 내부**: 자유로운 의존성
2. **도메인 간**: ServiceFactory를 통해서만
3. **앱 계층**: 모든 도메인에서 접근 가능
4. **외부 라이브러리**: 최소한으로, 필요시 추상화

#### 예시
```python
# ✅ 올바른 의존성
class AnalysisUI(BaseUIComponent):
    def __init__(self, app_context):
        super().__init__(app_context)
        # 같은 도메인 내 직접 import
        from .analysis_helper import format_result
        # 다른 도메인은 ServiceFactory 통해서
        self.district_service = self.get_service('district_service')

# ❌ 잘못된 의존성
from src.domains.district.services.district_service import DistrictService
```

---

## 🛠️ 실용적인 개발 팁

### 디버깅과 문제 해결

#### 1. Import 오류가 발생할 때
```bash
# 1단계: 파일이 올바른 위치에 있는지 확인
find src -name "*.py" | grep <파일명>

# 2단계: __init__.py 파일이 있는지 확인
find src -name "__init__.py"

# 3단계: 경로가 맞는지 확인
python -c "from src.domains.analysis.services.vision_service import VisionService"
```

#### 2. ServiceFactory에서 서비스를 찾을 수 없을 때
```python
# 1단계: SERVICE_DOMAIN_MAP 확인
# src/app/core/service_factory.py
SERVICE_DOMAIN_MAP = {
    'vision_service': 'analysis',  # 이 매핑이 있는가?
}

# 2단계: 서비스 클래스명 확인
# 파일명: vision_service.py
# 클래스명: VisionService (일치하는가?)
```

#### 3. 페이지가 표시되지 않을 때
```python
# 1단계: 파일명 확인 (pages/01_page_name.py)
# 2단계: st.set_page_config() 호출 확인
# 3단계: 오류 로그 확인
streamlit run app.py --logger.level=debug
```

### 성능 최적화

#### 1. Streamlit 캐싱 활용
```python
@st.cache_data
def expensive_computation(data):
    # 무거운 계산
    return result

@st.cache_resource
def load_model():
    # 모델 로딩 (한 번만)
    return model
```

#### 2. 지연 로딩 (Lazy Loading)
```python
class VisionService:
    def __init__(self, config):
        self.config = config
        self._model = None  # 지연 초기화

    @property
    def model(self):
        if self._model is None:
            self._model = self._load_model()
        return self._model
```

### 테스트 작성 가이드

#### 1. 단위 테스트 (각 도메인별)
```python
# test/domains/analysis/test_vision_service.py
class TestVisionService:
    def test_analyze_image_success(self):
        # 성공 케이스
        pass

    def test_analyze_image_invalid_input(self):
        # 실패 케이스
        pass
```

#### 2. 통합 테스트
```python
# test/integration/test_analysis_flow.py
def test_full_analysis_pipeline():
    # 전체 플로우 테스트
    pass
```

#### 3. UI 테스트 (수동 체크리스트)
- [ ] 모든 페이지가 로드되는가?
- [ ] 오류 메시지가 적절히 표시되는가?
- [ ] 사용자 입력이 올바르게 처리되는가?

---

## 🔒 보안 및 운영 가이드라인

### API 키 관리

#### 1. 로컬 개발
```bash
# .env 파일 (저장소에 커밋하지 말것!)
OPENAI_API_KEY=sk-...
GOOGLE_CSE_API_KEY=...
```

#### 2. 배포 환경
```toml
# .streamlit/secrets.toml
[general]
OPENAI_API_KEY = "sk-..."
GOOGLE_CSE_API_KEY = "..."
```

#### 3. 코드에서 사용
```python
# ✅ 올바른 방법
from src.app.core.config import load_config
config = load_config()
api_key = config.openai_api_key

# ❌ 잘못된 방법
api_key = "sk-hardcoded-key"  # 절대 하지 말것
```

### 에러 처리

#### 1. 사용자 친화적 메시지
```python
try:
    result = some_api_call()
except APIError as e:
    st.error("죄송합니다. 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
    logger.error(f"API call failed: {e}")
```

#### 2. 우아한 기능 저하 (Graceful Degradation)
```python
def analyze_image(image):
    try:
        return ai_analysis(image)
    except ModelNotAvailable:
        st.warning("AI 분석 기능을 사용할 수 없습니다. 기본 정보를 제공합니다.")
        return basic_analysis(image)
```

### 로깅

#### 1. 적절한 로그 레벨
```python
logger.debug("상세한 디버그 정보")      # 개발시에만
logger.info("일반적인 동작 정보")       # 운영 모니터링용
logger.warning("주의가 필요한 상황")    # 문제 징후
logger.error("오류 발생")             # 즉시 대응 필요
```

#### 2. 구조화된 로깅
```python
logger.info("Image analysis completed", extra={
    "user_id": user_id,
    "image_size": len(image_data),
    "analysis_time": elapsed_time,
    "model_used": model_name
})
```

---

## 📈 확장성 고려사항

### 새로운 지역 추가

#### 1. 국제화 준비
```python
# src/domains/district/services/region_service.py
class RegionService:
    def get_waste_rules(self, country, region):
        # 국가별 규정 로딩
        pass
```

#### 2. 다국어 지원
```python
# src/app/core/i18n.py
def get_text(key, language='ko'):
    translations = {
        'ko': {'welcome': '환영합니다'},
        'en': {'welcome': 'Welcome'}
    }
    return translations[language][key]
```

### 새로운 AI 모델 통합

#### 1. 모델 추상화
```python
# src/domains/analysis/services/base_ai_service.py
class BaseAIService(ABC):
    @abstractmethod
    def analyze_image(self, image): pass

    @abstractmethod
    def get_model_info(self): pass
```

#### 2. 모델 선택 로직
```python
def select_best_model(image_type, quality_requirement):
    # 이미지 특성과 요구사항에 따라 최적 모델 선택
    pass
```

### 대용량 처리

#### 1. 배치 처리
```python
# src/domains/infrastructure/services/batch_service.py
def process_large_dataset(data_chunks):
    for chunk in data_chunks:
        yield process_chunk(chunk)
```

#### 2. 캐싱 전략
```python
@st.cache_data(ttl=3600)  # 1시간 캐시
def get_district_data(region_code):
    # 자주 조회되는 데이터 캐싱
    pass
```

---

## 🎓 학습 리소스

### 새로운 개발자를 위한 학습 순서

#### 1주차: 기본 이해
- [ ] 프로젝트 목적과 사용자 시나리오 파악
- [ ] 로컬 환경 설정 및 앱 실행
- [ ] 각 페이지 기능 체험

#### 2주차: 아키텍처 이해
- [ ] 도메인별 역할과 책임 파악
- [ ] 주요 서비스들의 동작 방식 이해
- [ ] 설정 시스템과 의존성 주입 패턴 학습

#### 3주차: 첫 기여
- [ ] 간단한 UI 개선 작업
- [ ] 기존 기능에 작은 개선사항 추가
- [ ] 테스트 코드 작성 연습

#### 4주차 이후: 독립적 개발
- [ ] 새로운 기능 설계 및 구현
- [ ] 성능 최적화 작업
- [ ] 복잡한 통합 작업

### 추천 학습 자료

#### Streamlit 관련
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Streamlit 모범 사례](https://docs.streamlit.io/library/advanced-features)

#### Python 아키텍처
- Clean Architecture in Python
- Domain-Driven Design 기초

#### AI/ML 통합
- OpenAI API 공식 문서
- Computer Vision 기초

---

## 🔄 지속적 개선

### 정기 리뷰 포인트

#### 매월
- [ ] 성능 지표 검토 (응답 시간, 정확도)
- [ ] 사용자 피드백 분석
- [ ] 보안 업데이트 확인

#### 분기별
- [ ] 아키텍처 개선점 검토
- [ ] 새로운 기술 도입 검토
- [ ] 팀 프로세스 개선

#### 연간
- [ ] 전체 기술 스택 재평가
- [ ] 확장성 계획 수립
- [ ] 장기 로드맵 업데이트

### 피드백 루프

#### 1. 사용자 피드백
- Streamlit 앱 내 피드백 폼
- 사용 패턴 분석
- 오류 리포트 모니터링

#### 2. 개발자 피드백
- 코드 리뷰 과정에서의 개선점
- 개발 생산성 지표
- 기술 부채 추적

#### 3. 시스템 피드백
- 성능 모니터링 결과
- 자동화된 테스트 결과
- 보안 스캔 결과

---

**📝 작성일**: 2025-09-23
**🔄 버전**: 1.0
**🎯 목적**: 실용적이고 포괄적인 개발 가이드 제공
**📖 대상**: 모든 개발자 및 AI 어시스턴트