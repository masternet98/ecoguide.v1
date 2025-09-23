# Phase 1: 사용자 피드백 시스템 설계서

## 🎯 목적 및 범위

### 핵심 목적
현재 VisionService의 물건 분류 및 크기 추정 결과에 대한 **사용자 피드백을 수집**하여 시스템 정확도를 지속적으로 개선

### 비즈니스 가치
- **즉시 가치 제공**: 구현 즉시 사용자 경험 개선
- **데이터 기반 개선**: 실제 사용 패턴 기반 시스템 최적화
- **사용자 참여도 증대**: 능동적 피드백을 통한 서비스 만족도 향상

### 구현 범위
- ✅ 분류 정확성 평가 인터페이스
- ✅ 크기 추정 정확성 평가 인터페이스
- ✅ 피드백 데이터 수집 및 저장
- ✅ 실시간 정확도 지표 대시보드
- ✅ 개선 사항 추천 시스템

## 🔗 기존 시스템 연계점

### 의존성 (최소화)
```python
# 기존 시스템에서 활용
- VisionService: 분석 결과 제공
- SessionState: 사용자 세션 관리
- BaseUIComponent: UI 컴포넌트 기반 클래스
- PostgreSQL: 데이터 저장
```

### 확장점
```python
# 다른 Phase와의 연계 (선택적)
- Phase 2 (라벨링): 피드백 데이터 → 학습 데이터
- Phase 4 (프롬프트): 피드백 패턴 → 프롬프트 개선
```

## 🏗️ 시스템 아키텍처

### 컴포넌트 구조
```
src/
├── components/
│   └── feedback_ui.py              # 피드백 UI 컴포넌트
├── domains/
│   └── analysis/
│       └── services/
│           ├── feedback_service.py      # 피드백 수집 서비스
│           └── accuracy_tracking_service.py  # 정확도 추적 서비스
└── pages/
    └── feedback_dashboard.py       # 피드백 대시보드 페이지 (선택적)
```

### 데이터 플로우
```
사용자 이미지 업로드
    ↓
VisionService 분석
    ↓
FeedbackUI 표시 (결과 + 피드백 인터페이스)
    ↓
사용자 피드백 입력
    ↓
FeedbackService 수집 및 검증
    ↓
AccuracyTrackingService 지표 업데이트
    ↓
실시간 대시보드 반영
```

## 📋 세부 기능 설계

### 1. FeedbackUI 컴포넌트

```python
# src/components/feedback_ui.py
class FeedbackUI(BaseUIComponent):
    """사용자 피드백 수집 UI 컴포넌트"""

    def __init__(self, vision_result: dict, session_id: str):
        self.vision_result = vision_result
        self.session_id = session_id
        self.feedback_service = self.get_service('feedback_service')

    def render_feedback_interface(self) -> dict:
        """메인 피드백 인터페이스 렌더링"""

        # 1. 분석 결과 표시
        self._render_analysis_results()

        # 2. 분류 정확성 평가
        classification_feedback = self._render_classification_feedback()

        # 3. 크기 추정 정확성 평가
        size_feedback = self._render_size_feedback()

        # 4. 추가 의견 입력
        additional_comments = self._render_additional_feedback()

        # 5. 피드백 제출
        if st.button("피드백 제출"):
            return self._submit_feedback({
                'classification': classification_feedback,
                'size': size_feedback,
                'comments': additional_comments
            })

    def _render_classification_feedback(self) -> dict:
        """물건 분류 정확성 피드백"""

        st.subheader("🔍 물건 분류가 정확한가요?")

        col1, col2 = st.columns(2)

        with col1:
            is_correct = st.radio(
                "분류 결과",
                ["정확함", "부정확함"],
                key=f"classification_{self.session_id}"
            )

        corrected_label = None
        if is_correct == "부정확함":
            with col2:
                corrected_label = st.text_input(
                    "올바른 물건 이름을 입력해주세요",
                    key=f"corrected_label_{self.session_id}"
                )

        confidence_rating = st.slider(
            "분류 결과에 대한 신뢰도 (1=매우 부정확, 5=매우 정확)",
            1, 5, 3,
            key=f"classification_confidence_{self.session_id}"
        )

        return {
            'is_correct': is_correct == "정확함",
            'corrected_label': corrected_label,
            'confidence_rating': confidence_rating
        }

    def _render_size_feedback(self) -> dict:
        """크기 추정 정확성 피드백"""

        st.subheader("📏 크기 추정이 정확한가요?")

        col1, col2 = st.columns(2)

        with col1:
            is_correct = st.radio(
                "크기 추정 결과",
                ["정확함", "부정확함"],
                key=f"size_{self.session_id}"
            )

        corrected_size = {}
        if is_correct == "부정확함":
            with col2:
                st.write("실제 크기를 입력해주세요")
                corrected_size = {
                    'width_cm': st.number_input(
                        "가로 (cm)",
                        min_value=0.1,
                        key=f"width_{self.session_id}"
                    ),
                    'height_cm': st.number_input(
                        "세로 (cm)",
                        min_value=0.1,
                        key=f"height_{self.session_id}"
                    )
                }

        size_confidence = st.slider(
            "크기 추정에 대한 신뢰도 (1=매우 부정확, 5=매우 정확)",
            1, 5, 3,
            key=f"size_confidence_{self.session_id}"
        )

        return {
            'is_correct': is_correct == "정확함",
            'corrected_size': corrected_size if corrected_size else None,
            'confidence_rating': size_confidence
        }

    def _render_additional_feedback(self) -> str:
        """추가 의견 입력"""

        st.subheader("💬 추가 의견 (선택사항)")

        return st.text_area(
            "개선 사항이나 추가 의견이 있으시면 자유롭게 작성해주세요",
            key=f"additional_{self.session_id}",
            height=100
        )
```

### 2. FeedbackService

```python
# src/domains/analysis/services/feedback_service.py
from src.app.core.base_service import BaseService
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

class FeedbackService(BaseService):
    """사용자 피드백 수집 및 처리 서비스"""

    def collect_feedback(self,
                        image_id: str,
                        vision_result: dict,
                        user_feedback: dict,
                        session_id: str) -> dict:
        """피드백 수집 및 저장"""

        # 1. 피드백 데이터 검증
        validated_feedback = self._validate_feedback_data(user_feedback)

        # 2. 데이터베이스 저장
        feedback_record = self._save_feedback_to_db(
            image_id=image_id,
            vision_result=vision_result,
            feedback=validated_feedback,
            session_id=session_id
        )

        # 3. 정확도 지표 업데이트
        self._update_accuracy_metrics(feedback_record)

        # 4. 감사 메시지 생성
        thank_you_message = self._generate_thank_you_message(validated_feedback)

        return {
            'success': True,
            'feedback_id': feedback_record['id'],
            'message': thank_you_message,
            'accuracy_impact': self._calculate_accuracy_impact(validated_feedback)
        }

    def _validate_feedback_data(self, feedback: dict) -> dict:
        """피드백 데이터 유효성 검증"""

        validated = {
            'classification': {
                'is_correct': bool(feedback.get('classification', {}).get('is_correct', False)),
                'corrected_label': self._sanitize_text(
                    feedback.get('classification', {}).get('corrected_label')
                ),
                'confidence_rating': max(1, min(5,
                    int(feedback.get('classification', {}).get('confidence_rating', 3))
                ))
            },
            'size': {
                'is_correct': bool(feedback.get('size', {}).get('is_correct', False)),
                'corrected_size': self._validate_size_data(
                    feedback.get('size', {}).get('corrected_size')
                ),
                'confidence_rating': max(1, min(5,
                    int(feedback.get('size', {}).get('confidence_rating', 3))
                ))
            },
            'additional_comments': self._sanitize_text(
                feedback.get('comments', '')
            ),
            'overall_satisfaction': self._calculate_overall_satisfaction(feedback)
        }

        return validated

    def _save_feedback_to_db(self,
                           image_id: str,
                           vision_result: dict,
                           feedback: dict,
                           session_id: str) -> dict:
        """데이터베이스에 피드백 저장"""

        feedback_record = {
            'id': str(uuid.uuid4()),
            'image_id': image_id,
            'session_id': session_id,
            'vision_result': vision_result,
            'user_feedback': feedback,
            'created_at': datetime.now(),
            'processed': False
        }

        # PostgreSQL 저장 로직
        # (데이터베이스 스키마는 별도 섹션에서 정의)

        return feedback_record

    def get_feedback_statistics(self, date_range: tuple = None) -> dict:
        """피드백 통계 조회"""

        return {
            'total_feedback_count': 0,  # 구현 필요
            'classification_accuracy': 0.0,
            'size_estimation_accuracy': 0.0,
            'average_satisfaction': 0.0,
            'improvement_suggestions': []
        }
```

### 3. AccuracyTrackingService

```python
# src/domains/analysis/services/accuracy_tracking_service.py
class AccuracyTrackingService(BaseService):
    """정확도 추적 및 분석 서비스"""

    def update_accuracy_metrics(self, feedback_record: dict) -> None:
        """피드백을 기반으로 정확도 지표 업데이트"""

        # 1. 분류 정확도 업데이트
        self._update_classification_accuracy(feedback_record)

        # 2. 크기 추정 정확도 업데이트
        self._update_size_estimation_accuracy(feedback_record)

        # 3. 전체 만족도 업데이트
        self._update_overall_satisfaction(feedback_record)

        # 4. 개선 포인트 식별
        self._identify_improvement_points(feedback_record)

    def get_real_time_metrics(self) -> dict:
        """실시간 정확도 지표 조회"""

        return {
            'classification_accuracy': self._calculate_classification_accuracy(),
            'size_estimation_accuracy': self._calculate_size_accuracy(),
            'user_satisfaction': self._calculate_user_satisfaction(),
            'total_feedback_count': self._get_total_feedback_count(),
            'recent_trends': self._get_recent_trends(),
            'improvement_suggestions': self._get_improvement_suggestions()
        }

    def generate_accuracy_report(self, period: str = 'weekly') -> dict:
        """정확도 보고서 생성"""

        return {
            'period': period,
            'summary': self._generate_summary_stats(period),
            'detailed_metrics': self._generate_detailed_metrics(period),
            'trend_analysis': self._analyze_trends(period),
            'recommendations': self._generate_recommendations(period)
        }
```

## 🗄️ 데이터베이스 스키마

### 피드백 관련 테이블

```sql
-- 사용자 피드백 테이블
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 연결 정보
    image_id TEXT, -- VisionService 분석 대상 이미지 (임시 ID)
    session_id TEXT NOT NULL,

    -- 원본 분석 결과
    original_analysis JSONB NOT NULL, -- VisionService 결과

    -- 분류 피드백
    classification_correct BOOLEAN,
    corrected_classification TEXT,
    classification_confidence_rating INTEGER CHECK (classification_confidence_rating >= 1 AND classification_confidence_rating <= 5),

    -- 크기 추정 피드백
    size_correct BOOLEAN,
    corrected_size JSONB, -- {width_cm, height_cm}
    size_confidence_rating INTEGER CHECK (size_confidence_rating >= 1 AND size_confidence_rating <= 5),

    -- 전반적 피드백
    overall_satisfaction INTEGER CHECK (overall_satisfaction >= 1 AND overall_satisfaction <= 5),
    additional_comments TEXT,

    -- 메타데이터
    user_agent TEXT,
    feedback_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 정확도 지표 테이블
CREATE TABLE accuracy_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL,

    -- 분류 정확도
    classification_accuracy FLOAT,
    classification_total_count INTEGER DEFAULT 0,
    classification_correct_count INTEGER DEFAULT 0,

    -- 크기 추정 정확도
    size_estimation_accuracy FLOAT,
    size_total_count INTEGER DEFAULT 0,
    size_correct_count INTEGER DEFAULT 0,

    -- 사용자 만족도
    avg_user_satisfaction FLOAT,
    total_feedback_count INTEGER DEFAULT 0,

    -- 상세 통계
    category_metrics JSONB, -- 카테고리별 정확도
    improvement_areas JSONB, -- 개선이 필요한 영역

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(metric_date)
);

-- 개선 제안 테이블
CREATE TABLE improvement_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    suggestion_type TEXT NOT NULL, -- 'classification', 'size_estimation', 'ui', 'general'
    priority_level INTEGER DEFAULT 1, -- 1(낮음) ~ 5(높음)

    description TEXT NOT NULL,
    evidence_feedback_ids TEXT[], -- 근거가 되는 피드백 ID들

    status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'rejected'
    assigned_to TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 인덱스 최적화

```sql
-- 성능 최적화 인덱스
CREATE INDEX idx_user_feedback_timestamp ON user_feedback(feedback_timestamp);
CREATE INDEX idx_user_feedback_session ON user_feedback(session_id);
CREATE INDEX idx_user_feedback_processed ON user_feedback(processed);
CREATE INDEX idx_accuracy_metrics_date ON accuracy_metrics(metric_date);
CREATE INDEX idx_improvement_suggestions_status ON improvement_suggestions(status);
CREATE INDEX idx_improvement_suggestions_priority ON improvement_suggestions(priority_level);
```

## 🚀 구현 가이드

### 1단계: 기본 구조 구축 (1-2일)

```bash
# 1. 서비스 클래스 생성
touch src/domains/analysis/services/feedback_service.py
touch src/domains/analysis/services/accuracy_tracking_service.py

# 2. UI 컴포넌트 생성
touch src/components/feedback_ui.py

# 3. 데이터베이스 스키마 적용
# PostgreSQL에 위 스키마 실행
```

### 2단계: 핵심 기능 구현 (3-4일)

```python
# ServiceFactory에 새 서비스 등록
# src/core/service_factory.py에 추가

registry.register_service(
    name='feedback_service',
    service_class=type('FeedbackService', (), {}),
    module_path='src.domains.analysis.services.feedback_service',
    dependencies=[],
    is_optional=False,
    singleton=True
)

registry.register_service(
    name='accuracy_tracking_service',
    service_class=type('AccuracyTrackingService', (), {}),
    module_path='src.domains.analysis.services.accuracy_tracking_service',
    dependencies=['feedback_service'],
    is_optional=False,
    singleton=True
)
```

### 3단계: UI 통합 (2-3일)

```python
# 기존 이미지 분석 페이지에 피드백 UI 추가
# src/pages/camera_analysis.py 또는 해당 페이지에서

from src.components.feedback_ui import FeedbackUI

# 분석 결과 표시 후
if vision_result and vision_result.success:
    # 기존 결과 표시 코드...

    # 피드백 인터페이스 추가
    st.divider()
    st.subheader("📝 결과가 정확한지 피드백을 주세요!")

    feedback_ui = FeedbackUI(
        vision_result=vision_result,
        session_id=st.session_state.get('session_id', 'default')
    )

    feedback_result = feedback_ui.render_feedback_interface()

    if feedback_result and feedback_result.get('success'):
        st.success(feedback_result['message'])
        st.balloons()  # 사용자 경험 개선
```

### 4단계: 대시보드 추가 (선택사항, 1-2일)

```python
# src/pages/feedback_dashboard.py (관리자용)
def render_feedback_dashboard():
    """피드백 및 정확도 대시보드"""

    st.title("📊 피드백 & 정확도 대시보드")

    accuracy_service = get_service('accuracy_tracking_service')
    metrics = accuracy_service.get_real_time_metrics()

    # 실시간 지표 표시
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "분류 정확도",
            f"{metrics['classification_accuracy']:.1%}",
            delta=f"+{metrics.get('classification_improvement', 0):.1%}"
        )

    with col2:
        st.metric(
            "크기 추정 정확도",
            f"{metrics['size_estimation_accuracy']:.1%}",
            delta=f"+{metrics.get('size_improvement', 0):.1%}"
        )

    with col3:
        st.metric(
            "사용자 만족도",
            f"{metrics['user_satisfaction']:.1f}/5.0",
            delta=f"+{metrics.get('satisfaction_improvement', 0):.1f}"
        )
```

## 🧪 테스트 전략

### 단위 테스트

```python
# test/test_feedback_service.py
def test_feedback_collection():
    """피드백 수집 기능 테스트"""

    feedback_service = FeedbackService()

    # 테스트 데이터
    test_feedback = {
        'classification': {
            'is_correct': False,
            'corrected_label': '의자',
            'confidence_rating': 2
        },
        'size': {
            'is_correct': True,
            'confidence_rating': 4
        },
        'comments': '분류가 틀렸지만 크기는 정확합니다'
    }

    result = feedback_service.collect_feedback(
        image_id='test_image_123',
        vision_result={'category': '테이블', 'confidence': 0.85},
        user_feedback=test_feedback,
        session_id='test_session'
    )

    assert result['success'] == True
    assert 'feedback_id' in result
    assert '감사합니다' in result['message']
```

### 통합 테스트

```python
# test/test_feedback_integration.py
def test_feedback_ui_integration():
    """피드백 UI 통합 테스트"""

    # Streamlit 앱 테스트 (selenium 등 활용)
    # 실제 사용자 시나리오 검증
    pass
```

### 성능 테스트

```python
def test_feedback_performance():
    """피드백 처리 성능 테스트"""

    # 대량 피드백 처리 시간 측정
    # 데이터베이스 성능 확인
    pass
```

## 📊 성공 지표 및 모니터링

### 핵심 KPI
1. **피드백 수집률**: 분석 대비 피드백 제공 비율 > 70%
2. **분류 정확도 개선**: 피드백 반영 후 개선율 > 10%
3. **사용자 만족도**: 피드백 인터페이스 만족도 > 4.0/5.0
4. **응답 시간**: 피드백 저장 시간 < 1초

### 모니터링 대시보드
- 실시간 정확도 지표
- 피드백 수집 트렌드
- 카테고리별 개선 현황
- 사용자 만족도 추이

## 🔮 다음 Phase 연계점

### Phase 2 (라벨링) 연계
```python
# 피드백 데이터를 라벨링 데이터로 활용
- 수정된 분류 정보 → 학습 라벨
- 크기 정보 보정 → 정확한 메타데이터
- 고품질 피드백 → 신뢰도 높은 학습 데이터
```

### Phase 4 (프롬프트 최적화) 연계
```python
# 피드백 패턴을 프롬프트 개선에 활용
- 자주 틀리는 분류 → 프롬프트 강화 포인트
- 사용자 의견 → 설명 방식 개선
- 만족도 데이터 → A/B 테스트 기준
```

## 💡 구현 팁

1. **점진적 배포**: 피드백 UI를 선택적으로 표시하여 사용자 반응 확인
2. **성능 최적화**: 피드백 저장은 비동기로 처리하여 사용자 경험 방해 없이
3. **데이터 품질**: 피드백 데이터 검증 로직으로 노이즈 데이터 필터링
4. **사용자 동기부여**: 피드백 제공 시 재미있는 애니메이션이나 포인트 시스템 고려

이 Phase 1은 **완전히 독립적으로 구현하여 즉시 가치를 제공**할 수 있으며, 다른 Phase들의 기반 데이터를 제공하는 핵심 역할을 수행합니다.