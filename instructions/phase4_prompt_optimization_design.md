# Phase 4: 프롬프트 최적화 시스템 설계서

## 🎯 목적 및 범위

### 핵심 목적
Phase 1(피드백)과 Phase 3(RAG)의 성과를 통합하여 **컨텍스트 인식 고품질 AI 응답 생성 시스템**을 구축하고, 지속적인 개선을 통해 전체 시스템 완성도 극대화

### 비즈니스 가치
- **응답 품질 극대화**: 사용자별, 상황별 맞춤형 고품질 응답
- **지속적 자가 개선**: A/B 테스트와 피드백 기반 자동 최적화
- **시스템 완성도**: 모든 Phase의 시너지를 통한 완전한 AI 서비스
- **경쟁 우위 확보**: 단순 정보 제공을 넘어선 지능형 상담 서비스

### 구현 범위
- ✅ 컨텍스트 인식 프롬프트 생성
- ✅ A/B 테스트 시스템
- ✅ 응답 품질 자동 평가
- ✅ 프롬프트 성능 모니터링
- ✅ 피드백 기반 지속적 개선
- ✅ 개인화 프롬프트 전략

## 🔗 기존 시스템 연계점

### 주요 의존성
```python
# Phase 1 연계 (필수)
- FeedbackService: 사용자 피드백 패턴 분석
- AccuracyTrackingService: 성능 지표 활용

# Phase 3 연계 (필수)
- DistrictRAGService: 지자체 정보 컨텍스트
- RAGSearchService: 검색 품질 데이터

# 기존 시스템
- OpenAIService: LLM 응답 생성
- PromptService: 기본 프롬프트 관리
```

### 독립 실행 시 제한사항
```python
# Phase 1+3 없이는 기능 제한적
- 기본 프롬프트 최적화만 가능
- 개인화 및 컨텍스트 인식 기능 제한
- 데이터 기반 개선 효과 제한적
```

## 🏗️ 시스템 아키텍처

### 컴포넌트 구조
```
src/
├── domains/
│   └── prompts/
│       └── services/
│           ├── context_aware_prompt_service.py  # 컨텍스트 인식 프롬프트
│           ├── prompt_optimization_service.py   # 프롬프트 최적화 관리
│           ├── ab_test_service.py              # A/B 테스트 관리
│           ├── response_quality_service.py     # 응답 품질 평가
│           └── personalization_service.py      # 개인화 프롬프트
└── pages/
    └── prompt_optimization_dashboard.py        # 최적화 대시보드 (관리자용)
```

### 프롬프트 최적화 플로우
```
사용자 요청
    ↓
Context Analysis (컨텍스트 분석)
    ↓
Prompt Strategy Selection (전략 선택)
    ↓
Dynamic Prompt Generation (동적 프롬프트 생성)
    ↓
A/B Test Assignment (A/B 테스트 할당)
    ↓
LLM Response Generation (응답 생성)
    ↓
Quality Assessment (품질 평가)
    ↓
Performance Tracking (성능 추적)
    ↓
Continuous Improvement (지속적 개선)
```

## 📋 세부 기능 설계

### 1. ContextAwarePromptService (핵심 프롬프트 엔진)

```python
# src/domains/prompts/services/context_aware_prompt_service.py
from src.app.core.base_service import BaseService
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class PromptStrategy(Enum):
    BEGINNER_FRIENDLY = "beginner_friendly"
    TECHNICAL_DETAILED = "technical_detailed"
    QUICK_ANSWER = "quick_answer"
    COMPREHENSIVE = "comprehensive"
    VISUAL_FOCUSED = "visual_focused"

@dataclass
class PromptContext:
    """프롬프트 생성을 위한 컨텍스트 정보"""
    # 사용자 정보
    user_session_id: str
    user_history: Dict[str, Any]
    user_expertise_level: str  # 'beginner', 'intermediate', 'expert'

    # 분석 결과 정보
    vision_result: Dict[str, Any]
    confidence_level: float

    # RAG 검색 결과
    rag_context: Dict[str, Any]
    district_info: Dict[str, Any]

    # 상황 정보
    time_of_day: str
    device_type: str  # 'mobile', 'desktop'
    session_duration: float

    # 피드백 이력
    previous_feedback: List[Dict[str, Any]]
    accuracy_history: Dict[str, float]

class ContextAwarePromptService(BaseService):
    """컨텍스트 인식 프롬프트 생성 서비스"""

    def __init__(self, config):
        super().__init__(config)
        self.prompt_templates = self._load_prompt_templates()
        self.optimization_service = None  # lazy loading

    def generate_contextual_prompt(self, context: PromptContext) -> Dict[str, Any]:
        """컨텍스트 기반 최적 프롬프트 생성 (메인 API)"""

        try:
            # 1. 사용자 프로필 분석
            user_profile = self._analyze_user_profile(context)

            # 2. 최적 전략 선택
            optimal_strategy = self._select_optimal_strategy(context, user_profile)

            # 3. 동적 프롬프트 생성
            prompt_components = self._build_prompt_components(context, optimal_strategy)

            # 4. A/B 테스트 변형 적용 (선택적)
            final_prompt = self._apply_ab_test_variation(prompt_components, context)

            # 5. 프롬프트 메타데이터 생성
            metadata = self._generate_prompt_metadata(context, optimal_strategy, user_profile)

            return {
                'success': True,
                'prompt': final_prompt,
                'strategy': optimal_strategy.value,
                'user_profile': user_profile,
                'metadata': metadata,
                'expected_quality': self._predict_response_quality(context, optimal_strategy)
            }

        except Exception as e:
            self.logger.error(f"Context-aware prompt generation failed: {e}")
            return self._generate_fallback_prompt(context)

    def _analyze_user_profile(self, context: PromptContext) -> Dict[str, Any]:
        """사용자 프로필 분석"""

        profile = {
            'expertise_level': context.user_expertise_level,
            'communication_preference': 'standard',
            'attention_span': 'medium',
            'detail_preference': 'balanced',
            'confidence_in_system': 0.5
        }

        # 사용자 히스토리 기반 분석
        if context.user_history:
            # 이전 세션에서의 선호도 패턴 분석
            profile.update(self._extract_preferences_from_history(context.user_history))

        # 피드백 패턴 분석
        if context.previous_feedback:
            feedback_analysis = self._analyze_feedback_patterns(context.previous_feedback)
            profile.update(feedback_analysis)

        # 정확도 이력 기반 신뢰도 조정
        if context.accuracy_history:
            avg_accuracy = sum(context.accuracy_history.values()) / len(context.accuracy_history)
            profile['confidence_in_system'] = avg_accuracy

        # 디바이스 기반 조정
        if context.device_type == 'mobile':
            profile['attention_span'] = 'short'
            profile['detail_preference'] = 'concise'

        return profile

    def _select_optimal_strategy(self, context: PromptContext, user_profile: Dict) -> PromptStrategy:
        """최적 프롬프트 전략 선택"""

        # 기본 점수 계산
        strategy_scores = {
            PromptStrategy.BEGINNER_FRIENDLY: 0.3,
            PromptStrategy.TECHNICAL_DETAILED: 0.2,
            PromptStrategy.QUICK_ANSWER: 0.2,
            PromptStrategy.COMPREHENSIVE: 0.2,
            PromptStrategy.VISUAL_FOCUSED: 0.1
        }

        # 사용자 전문성 수준 반영
        if user_profile['expertise_level'] == 'beginner':
            strategy_scores[PromptStrategy.BEGINNER_FRIENDLY] += 0.4
            strategy_scores[PromptStrategy.VISUAL_FOCUSED] += 0.2
        elif user_profile['expertise_level'] == 'expert':
            strategy_scores[PromptStrategy.TECHNICAL_DETAILED] += 0.4
            strategy_scores[PromptStrategy.COMPREHENSIVE] += 0.2

        # 신뢰도 기반 조정
        confidence = context.confidence_level
        if confidence > 0.8:
            strategy_scores[PromptStrategy.COMPREHENSIVE] += 0.2
        elif confidence < 0.5:
            strategy_scores[PromptStrategy.BEGINNER_FRIENDLY] += 0.3

        # RAG 컨텍스트 품질 반영
        rag_confidence = context.rag_context.get('confidence_score', 0.5)
        if rag_confidence > 0.8:
            strategy_scores[PromptStrategy.TECHNICAL_DETAILED] += 0.2
        else:
            strategy_scores[PromptStrategy.QUICK_ANSWER] += 0.2

        # 디바이스 타입 반영
        if context.device_type == 'mobile':
            strategy_scores[PromptStrategy.QUICK_ANSWER] += 0.3
            strategy_scores[PromptStrategy.VISUAL_FOCUSED] += 0.2

        # 시간대 반영 (밤늦은 시간 = 간단한 답변 선호)
        if context.time_of_day in ['late_night', 'early_morning']:
            strategy_scores[PromptStrategy.QUICK_ANSWER] += 0.2

        # 최고 점수 전략 선택
        return max(strategy_scores, key=strategy_scores.get)

    def _build_prompt_components(self, context: PromptContext, strategy: PromptStrategy) -> Dict[str, str]:
        """전략별 프롬프트 컴포넌트 구성"""

        components = {
            'system_role': self._get_system_role(strategy),
            'context_section': self._build_context_section(context, strategy),
            'instruction_section': self._build_instruction_section(strategy),
            'output_format': self._get_output_format(strategy),
            'constraints': self._get_constraints(strategy, context)
        }

        return components

    def _get_system_role(self, strategy: PromptStrategy) -> str:
        """전략별 시스템 역할 정의"""

        role_templates = {
            PromptStrategy.BEGINNER_FRIENDLY: """당신은 친근하고 이해하기 쉬운 대형폐기물 배출 도우미입니다.
초보자도 쉽게 이해할 수 있도록 단계별로 차근차근 설명해주세요.""",

            PromptStrategy.TECHNICAL_DETAILED: """당신은 대형폐기물 배출 규정 전문가입니다.
정확한 법규와 세부 절차를 포함하여 전문적이고 상세한 정보를 제공해주세요.""",

            PromptStrategy.QUICK_ANSWER: """당신은 효율적인 대형폐기물 배출 안내원입니다.
핵심 정보만 빠르고 명확하게 전달해주세요.""",

            PromptStrategy.COMPREHENSIVE: """당신은 종합적인 대형폐기물 관리 컨설턴트입니다.
전체적인 맥락과 다양한 옵션을 포함하여 완전한 안내를 제공해주세요.""",

            PromptStrategy.VISUAL_FOCUSED: """당신은 시각적 설명에 특화된 대형폐기물 배출 가이드입니다.
이미지 분석 결과를 중심으로 직관적이고 이해하기 쉽게 설명해주세요."""
        }

        return role_templates.get(strategy, role_templates[PromptStrategy.BEGINNER_FRIENDLY])

    def _build_context_section(self, context: PromptContext, strategy: PromptStrategy) -> str:
        """컨텍스트 섹션 구성"""

        context_parts = []

        # 기본 상황 정보
        context_parts.append(f"=== 현재 상황 ===")
        context_parts.append(f"사용자 위치: {context.district_info.get('district_name', '정보 없음')}")

        # 이미지 분석 결과
        vision_info = context.vision_result
        if vision_info:
            confidence_emoji = "🔴" if vision_info.get('confidence', 0) < 0.5 else "🟡" if vision_info.get('confidence', 0) < 0.8 else "🟢"
            context_parts.append(f"감지된 물건: {vision_info.get('category', '미확인')} {confidence_emoji}")

            if strategy in [PromptStrategy.TECHNICAL_DETAILED, PromptStrategy.COMPREHENSIVE]:
                context_parts.append(f"분석 신뢰도: {vision_info.get('confidence', 0):.1%}")
                size_info = vision_info.get('size_estimation', {})
                if size_info:
                    context_parts.append(f"추정 크기: {size_info.get('width_cm', 0):.1f}cm × {size_info.get('height_cm', 0):.1f}cm")

        # RAG 검색 결과 (고품질인 경우만)
        rag_info = context.rag_context
        if rag_info and rag_info.get('confidence_score', 0) > 0.6:
            context_parts.append(f"\n=== 지자체 공식 정보 ===")
            if strategy != PromptStrategy.QUICK_ANSWER:
                context_parts.append(rag_info.get('context_window', ''))
            else:
                # 간단한 답변 전략에서는 핵심 정보만
                key_info = self._extract_key_from_rag(rag_info)
                context_parts.append(key_info)

        # 사용자 피드백 이력 (관련성 있는 경우만)
        if context.previous_feedback and strategy in [PromptStrategy.COMPREHENSIVE, PromptStrategy.TECHNICAL_DETAILED]:
            recent_feedback = context.previous_feedback[-3:]  # 최근 3개만
            if recent_feedback:
                context_parts.append(f"\n=== 이전 피드백 패턴 ===")
                for feedback in recent_feedback:
                    if feedback.get('classification_correct') == False:
                        context_parts.append(f"- {feedback.get('corrected_classification', '')} 분류 수정 이력")

        return "\n".join(context_parts)

    def _build_instruction_section(self, strategy: PromptStrategy) -> str:
        """지시사항 섹션 구성"""

        instruction_templates = {
            PromptStrategy.BEGINNER_FRIENDLY: """
다음 순서로 친근하게 안내해주세요:
1. 😊 감지된 물건에 대한 확인 및 간단한 설명
2. 💰 해당 지역의 수수료 정보 (구체적 금액)
3. 📅 배출 가능한 날짜와 시간
4. 📋 신청 또는 배출 방법 (단계별)
5. ⚠️ 주의사항 (안전 관련)
6. 📞 궁금한 점이 있을 때 문의할 곳

각 단계마다 이모지를 사용하고, 이해하기 쉬운 말로 설명해주세요.""",

            PromptStrategy.TECHNICAL_DETAILED: """
다음 항목들을 정확하고 상세하게 안내해주세요:
1. 물건 분류 및 관련 법규/조례
2. 수수료 계산 방식 및 근거 조례
3. 배출 일정 및 장소 (상세 주소 포함)
4. 신청 절차 및 필요 서류
5. 크기/무게 제한 및 예외 사항
6. 위반 시 과태료 및 법적 조치
7. 관련 조례 및 규정 참조

전문 용어 사용을 허용하며, 법적 근거를 명시해주세요.""",

            PromptStrategy.QUICK_ANSWER: """
핵심 정보만 간결하게 제공해주세요:
• 수수료: [구체적 금액]
• 배출일: [요일/날짜]
• 신청: [방법]
• 문의: [연락처]

추가 설명은 최소화하고 실행 가능한 정보만 제공해주세요.""",

            PromptStrategy.COMPREHENSIVE: """
종합적인 안내를 제공해주세요:
1. 상황 분석 및 물건 확인
2. 해당 지역 규정 전체 개요
3. 수수료 및 배출 일정 상세 정보
4. 다양한 배출 방법 및 장단점 비교
5. 대안적 처리 방법 (재활용, 기부 등)
6. 예상되는 문제점 및 해결 방법
7. 관련 정책 동향 및 변경 사항
8. 추가 도움이 될 수 있는 자원

맥락과 배경 정보를 포함하여 완전한 이해를 도와주세요.""",

            PromptStrategy.VISUAL_FOCUSED: """
이미지 분석 결과를 중심으로 설명해주세요:
1. 🔍 "사진에서 보이는 물건은 [물건명]입니다"
2. 📏 크기 분석 결과 및 수수료 영향
3. 🎯 이 물건의 특별한 처리 방법 (있다면)
4. 📸 배출 시 사진 촬영 팁 (신청용)
5. ✅ 올바른 배출 상태 vs ❌ 잘못된 배출 상태

시각적 요소와 이미지 분석 결과를 최대한 활용해주세요."""
        }

        return instruction_templates.get(strategy, instruction_templates[PromptStrategy.BEGINNER_FRIENDLY])

    def _get_output_format(self, strategy: PromptStrategy) -> str:
        """출력 형식 지정"""

        format_templates = {
            PromptStrategy.BEGINNER_FRIENDLY: """
다음 형식으로 답변해주세요:
- 친근한 말투 사용 (존댓말, 하지만 딱딱하지 않게)
- 이모지 적극 활용
- 단락별로 명확히 구분
- 중요한 정보는 **굵게** 표시""",

            PromptStrategy.TECHNICAL_DETAILED: """
다음 형식으로 답변해주세요:
- 공식적이고 정확한 표현 사용
- 법규/조례 번호 명시
- 표나 목록 형태로 정리
- 참조 문서나 링크 포함""",

            PromptStrategy.QUICK_ANSWER: """
다음 형식으로 답변해주세요:
- 불필요한 설명 제거
- 핵심 정보만 나열
- 짧은 문장 사용
- 실행 가능한 정보 위주""",

            PromptStrategy.COMPREHENSIVE: """
다음 형식으로 답변해주세요:
- 섹션별로 체계적 구성
- 상세한 설명과 맥락 제공
- 다양한 시나리오 고려
- 추가 참고 자료 제공""",

            PromptStrategy.VISUAL_FOCUSED: """
다음 형식으로 답변해주세요:
- 이미지 분석 결과 우선 언급
- 시각적 비교나 예시 활용
- "사진에서 보시는 바와 같이..." 같은 표현 사용
- 단계별 시각적 가이드 제공"""
        }

        return format_templates.get(strategy, "자연스럽고 도움이 되는 형태로 답변해주세요.")

    def _apply_ab_test_variation(self, components: Dict[str, str], context: PromptContext) -> str:
        """A/B 테스트 변형 적용"""

        # A/B 테스트 서비스에서 현재 활성 테스트 확인
        ab_test_service = self._get_ab_test_service()
        active_test = ab_test_service.get_active_test_for_user(context.user_session_id)

        if active_test:
            # 테스트 변형 적용
            variation = active_test['variation']
            components = self._apply_test_variation(components, variation)

        # 최종 프롬프트 조합
        final_prompt = f"""
{components['system_role']}

{components['context_section']}

{components['instruction_section']}

{components['output_format']}

{components['constraints']}
"""

        return final_prompt.strip()

    def create_personalized_prompt(self, context: PromptContext, user_preferences: Dict) -> str:
        """개인화 프롬프트 생성"""

        # 사용자 선호도 반영
        if user_preferences.get('communication_style') == 'formal':
            # 격식있는 말투
            pass
        elif user_preferences.get('communication_style') == 'casual':
            # 캐주얼한 말투
            pass

        # 정보 상세도 조절
        detail_level = user_preferences.get('detail_preference', 'medium')
        if detail_level == 'minimal':
            # 최소한의 정보
            pass
        elif detail_level == 'maximum':
            # 최대한 상세한 정보
            pass

        return self.generate_contextual_prompt(context)['prompt']
```

### 2. ABTestService (A/B 테스트 관리)

```python
# src/domains/prompts/services/ab_test_service.py
class ABTestService(BaseService):
    """A/B 테스트 관리 서비스"""

    def __init__(self, config):
        super().__init__(config)
        self.active_tests = {}
        self.test_results = {}

    def create_ab_test(self,
                      test_name: str,
                      test_description: str,
                      variations: List[Dict],
                      target_metric: str,
                      duration_days: int = 7) -> Dict[str, Any]:
        """A/B 테스트 생성"""

        test_id = f"test_{test_name}_{int(time.time())}"

        test_config = {
            'test_id': test_id,
            'name': test_name,
            'description': test_description,
            'variations': variations,  # [{'name': 'control', 'prompt_changes': {}}, {'name': 'variant_a', 'prompt_changes': {}}]
            'target_metric': target_metric,  # 'user_satisfaction', 'response_accuracy', 'engagement'
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=duration_days),
            'traffic_split': self._calculate_traffic_split(len(variations)),
            'status': 'active',
            'participants': {},
            'results': {variation['name']: {'count': 0, 'metrics': {}} for variation in variations}
        }

        self.active_tests[test_id] = test_config

        # 데이터베이스에 저장
        self._save_test_config(test_config)

        return {
            'success': True,
            'test_id': test_id,
            'config': test_config
        }

    def assign_user_to_test(self, user_session_id: str, test_id: str = None) -> Dict[str, Any]:
        """사용자를 A/B 테스트에 할당"""

        if test_id:
            test = self.active_tests.get(test_id)
        else:
            # 가장 우선순위 높은 활성 테스트 선택
            test = self._get_priority_active_test()

        if not test:
            return {'assigned': False, 'variation': None}

        # 사용자 할당 로직 (해시 기반 일관성 보장)
        variation = self._assign_user_variation(user_session_id, test)

        # 할당 기록
        test['participants'][user_session_id] = {
            'variation': variation,
            'assigned_at': datetime.now(),
            'interactions': []
        }

        return {
            'assigned': True,
            'test_id': test['test_id'],
            'variation': variation,
            'test_name': test['name']
        }

    def record_test_interaction(self,
                              user_session_id: str,
                              test_id: str,
                              interaction_type: str,
                              metrics: Dict[str, Any]) -> None:
        """테스트 상호작용 기록"""

        test = self.active_tests.get(test_id)
        if not test or user_session_id not in test['participants']:
            return

        participant = test['participants'][user_session_id]
        variation = participant['variation']

        # 상호작용 기록
        interaction = {
            'type': interaction_type,
            'timestamp': datetime.now(),
            'metrics': metrics
        }

        participant['interactions'].append(interaction)

        # 테스트 결과 업데이트
        self._update_test_results(test, variation, interaction)

    def analyze_test_results(self, test_id: str) -> Dict[str, Any]:
        """A/B 테스트 결과 분석"""

        test = self.active_tests.get(test_id)
        if not test:
            return {'success': False, 'error': 'Test not found'}

        analysis = {
            'test_info': {
                'name': test['name'],
                'duration': (datetime.now() - test['start_date']).days,
                'total_participants': len(test['participants']),
                'target_metric': test['target_metric']
            },
            'variation_performance': {},
            'statistical_significance': {},
            'recommendations': []
        }

        # 각 변형별 성능 분석
        for variation_name, results in test['results'].items():
            if results['count'] > 0:
                avg_metrics = {
                    metric: sum(values) / len(values)
                    for metric, values in results['metrics'].items()
                    if values
                }

                analysis['variation_performance'][variation_name] = {
                    'participant_count': results['count'],
                    'average_metrics': avg_metrics
                }

        # 통계적 유의성 검정
        analysis['statistical_significance'] = self._calculate_statistical_significance(test)

        # 추천사항 생성
        analysis['recommendations'] = self._generate_test_recommendations(analysis)

        return analysis

    def _calculate_statistical_significance(self, test: Dict) -> Dict[str, Any]:
        """통계적 유의성 계산"""

        # 간단한 t-검정 또는 카이제곱 검정
        # 실제 구현에서는 scipy.stats 등 사용

        significance = {
            'is_significant': False,
            'p_value': 0.0,
            'confidence_level': 0.95,
            'sample_size_sufficient': False
        }

        # 최소 표본 크기 확인
        total_participants = sum(len(variation['participants']) for variation in test['results'].values())
        significance['sample_size_sufficient'] = total_participants >= 100

        # p-value 계산 (간단한 구현)
        if significance['sample_size_sufficient']:
            # 실제 통계 검정 로직 구현
            significance['p_value'] = 0.05  # 임시값
            significance['is_significant'] = significance['p_value'] < 0.05

        return significance
```

### 3. ResponseQualityService (응답 품질 평가)

```python
# src/domains/prompts/services/response_quality_service.py
class ResponseQualityService(BaseService):
    """응답 품질 평가 서비스"""

    def __init__(self, config):
        super().__init__(config)
        self.quality_metrics = {
            'factual_accuracy': 0.3,
            'completeness': 0.25,
            'clarity': 0.2,
            'relevance': 0.15,
            'user_satisfaction': 0.1
        }

    def evaluate_response_quality(self,
                                prompt: str,
                                response: str,
                                context: Dict[str, Any],
                                user_feedback: Dict = None) -> Dict[str, Any]:
        """응답 품질 종합 평가"""

        evaluation = {
            'overall_score': 0.0,
            'detailed_scores': {},
            'quality_grade': 'unknown',
            'improvement_suggestions': [],
            'confidence': 0.0
        }

        try:
            # 각 지표별 평가
            detailed_scores = {}

            detailed_scores['factual_accuracy'] = self._evaluate_factual_accuracy(
                response, context
            )

            detailed_scores['completeness'] = self._evaluate_completeness(
                prompt, response, context
            )

            detailed_scores['clarity'] = self._evaluate_clarity(response)

            detailed_scores['relevance'] = self._evaluate_relevance(
                prompt, response, context
            )

            if user_feedback:
                detailed_scores['user_satisfaction'] = self._evaluate_user_satisfaction(
                    user_feedback
                )
            else:
                detailed_scores['user_satisfaction'] = 0.5  # 중간값

            # 가중 평균 계산
            overall_score = sum(
                score * self.quality_metrics[metric]
                for metric, score in detailed_scores.items()
            )

            evaluation.update({
                'overall_score': round(overall_score, 3),
                'detailed_scores': detailed_scores,
                'quality_grade': self._determine_quality_grade(overall_score),
                'improvement_suggestions': self._generate_improvement_suggestions(detailed_scores),
                'confidence': self._calculate_evaluation_confidence(detailed_scores, user_feedback)
            })

        except Exception as e:
            self.logger.error(f"Response quality evaluation failed: {e}")
            evaluation['error'] = str(e)

        return evaluation

    def _evaluate_factual_accuracy(self, response: str, context: Dict) -> float:
        """사실적 정확성 평가"""

        score = 0.5  # 기본점수

        # RAG 컨텍스트와의 일치성 확인
        rag_context = context.get('rag_context', {})
        if rag_context:
            context_confidence = rag_context.get('confidence_score', 0.5)

            # 응답이 RAG 컨텍스트와 일치하는지 확인
            consistency_score = self._check_rag_consistency(response, rag_context)
            score = (context_confidence * 0.6 + consistency_score * 0.4)

        # 비전 분석 결과와의 일치성
        vision_result = context.get('vision_result', {})
        if vision_result:
            vision_confidence = vision_result.get('confidence', 0.5)
            vision_consistency = self._check_vision_consistency(response, vision_result)
            score = (score * 0.7 + (vision_confidence * vision_consistency) * 0.3)

        return round(score, 3)

    def _evaluate_completeness(self, prompt: str, response: str, context: Dict) -> float:
        """완성도 평가"""

        # 필수 요소 체크리스트
        required_elements = {
            'fee_information': ['수수료', '요금', '비용'],
            'schedule_information': ['배출', '일정', '요일'],
            'application_process': ['신청', '방법', '절차'],
            'contact_information': ['문의', '연락처', '전화']
        }

        found_elements = 0
        total_elements = len(required_elements)

        for element_type, keywords in required_elements.items():
            if any(keyword in response for keyword in keywords):
                found_elements += 1

        # 응답 길이 기반 보정
        response_length = len(response)
        length_score = min(response_length / 300, 1.0)  # 300자 기준

        completeness_score = (found_elements / total_elements) * 0.8 + length_score * 0.2

        return round(completeness_score, 3)

    def _evaluate_clarity(self, response: str) -> float:
        """명확성 평가"""

        score = 0.5

        # 문장 길이 분석
        sentences = response.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0

        if 10 <= avg_sentence_length <= 25:  # 적절한 문장 길이
            score += 0.2

        # 전문용어 사용 빈도
        technical_terms = ['조례', '규정', '법령', '과태료']
        technical_ratio = sum(1 for term in technical_terms if term in response) / len(technical_terms)

        if technical_ratio < 0.3:  # 과도한 전문용어 사용 지양
            score += 0.1

        # 구조화 정도 (번호, 불릿 포인트 등)
        structure_indicators = ['1.', '2.', '•', '-', '✓']
        if any(indicator in response for indicator in structure_indicators):
            score += 0.2

        return min(score, 1.0)

    def _evaluate_user_satisfaction(self, user_feedback: Dict) -> float:
        """사용자 만족도 평가"""

        satisfaction = user_feedback.get('overall_satisfaction', 3) / 5.0

        # 피드백 의견 분석
        comments = user_feedback.get('additional_comments', '')
        if comments:
            positive_words = ['좋은', '도움', '명확', '정확', '감사']
            negative_words = ['부족', '틀린', '어려운', '복잡', '이해']

            positive_count = sum(1 for word in positive_words if word in comments)
            negative_count = sum(1 for word in negative_words if word in comments)

            sentiment_score = (positive_count - negative_count) / max(positive_count + negative_count, 1)
            satisfaction = (satisfaction * 0.7 + (sentiment_score + 1) / 2 * 0.3)

        return round(satisfaction, 3)

    def generate_quality_report(self, period: str = 'weekly') -> Dict[str, Any]:
        """품질 보고서 생성"""

        report = {
            'period': period,
            'summary_statistics': {
                'total_evaluations': 0,
                'average_quality_score': 0.0,
                'quality_grade_distribution': {},
                'top_performing_prompts': [],
                'improvement_needed_areas': []
            },
            'trend_analysis': {
                'quality_trend': 'stable',  # 'improving', 'declining', 'stable'
                'trend_percentage': 0.0
            },
            'recommendations': []
        }

        # 실제 구현에서는 데이터베이스에서 기간별 데이터 조회 및 분석

        return report
```

## 🗄️ 데이터베이스 스키마

### 프롬프트 최적화 관련 테이블

```sql
-- A/B 테스트 테이블
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    test_name TEXT NOT NULL,
    description TEXT,
    target_metric TEXT NOT NULL, -- 'user_satisfaction', 'response_accuracy', 'engagement'

    -- 테스트 설정
    variations JSONB NOT NULL, -- 변형 설정
    traffic_split JSONB NOT NULL, -- 트래픽 분할 비율

    -- 상태 및 일정
    status TEXT DEFAULT 'draft', -- 'draft', 'active', 'paused', 'completed'
    start_date TIMESTAMP,
    end_date TIMESTAMP,

    -- 결과
    results JSONB,
    statistical_analysis JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system'
);

-- A/B 테스트 참가자 테이블
CREATE TABLE ab_test_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    test_id UUID REFERENCES ab_tests(id) ON DELETE CASCADE,
    user_session_id TEXT NOT NULL,

    -- 할당 정보
    variation_name TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 상호작용 이력
    interactions JSONB, -- [{type, timestamp, metrics}]

    UNIQUE(test_id, user_session_id)
);

-- 응답 품질 평가 테이블
CREATE TABLE response_quality_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 연결 정보
    user_session_id TEXT,
    prompt_strategy TEXT, -- PromptStrategy enum value
    ab_test_id UUID REFERENCES ab_tests(id),

    -- 프롬프트 및 응답
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    context_data JSONB,

    -- 품질 평가 결과
    overall_score FLOAT NOT NULL,
    detailed_scores JSONB NOT NULL, -- {metric: score}
    quality_grade TEXT, -- 'excellent', 'good', 'fair', 'poor'

    -- 사용자 피드백 (있는 경우)
    user_feedback JSONB,

    -- 메타데이터
    evaluation_method TEXT DEFAULT 'automated', -- 'automated', 'manual', 'hybrid'
    evaluation_confidence FLOAT DEFAULT 0.5,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 프롬프트 성능 지표 테이블
CREATE TABLE prompt_performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    date DATE NOT NULL,
    prompt_strategy TEXT NOT NULL,

    -- 성능 지표
    total_uses INTEGER DEFAULT 0,
    avg_quality_score FLOAT DEFAULT 0.0,
    avg_user_satisfaction FLOAT DEFAULT 0.0,
    avg_response_time_ms INTEGER DEFAULT 0,

    -- 사용자 반응
    positive_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    improvement_suggestions_count INTEGER DEFAULT 0,

    -- 정확도 관련
    accuracy_rate FLOAT DEFAULT 0.0,
    rag_consistency_rate FLOAT DEFAULT 0.0,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date, prompt_strategy)
);

-- 프롬프트 최적화 실험 로그
CREATE TABLE prompt_optimization_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    optimization_type TEXT NOT NULL, -- 'ab_test', 'strategy_change', 'parameter_tuning'
    description TEXT,

    -- 변경 전후
    before_config JSONB,
    after_config JSONB,

    -- 결과
    performance_impact JSONB, -- 성능 변화 지표
    success BOOLEAN DEFAULT FALSE,

    -- 메타데이터
    triggered_by TEXT DEFAULT 'automated', -- 'automated', 'manual', 'scheduled'
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by TEXT DEFAULT 'system'
);
```

### 인덱스 최적화

```sql
-- 성능 최적화 인덱스
CREATE INDEX idx_ab_tests_status ON ab_tests(status);
CREATE INDEX idx_ab_test_participants_session ON ab_test_participants(user_session_id);
CREATE INDEX idx_response_quality_strategy ON response_quality_evaluations(prompt_strategy);
CREATE INDEX idx_response_quality_created ON response_quality_evaluations(created_at);
CREATE INDEX idx_prompt_metrics_date ON prompt_performance_metrics(date);
CREATE INDEX idx_prompt_metrics_strategy ON prompt_performance_metrics(prompt_strategy);
CREATE INDEX idx_optimization_logs_type ON prompt_optimization_logs(optimization_type);
```

## 🚀 구현 가이드

### 1단계: 기본 컨텍스트 인식 프롬프트 (2-3일)

```python
# ServiceFactory에 프롬프트 최적화 서비스들 등록
registry.register_service(
    name='context_aware_prompt_service',
    service_class=type('ContextAwarePromptService', (), {}),
    module_path='src.domains.prompts.services.context_aware_prompt_service',
    dependencies=['feedback_service', 'district_rag_service'],
    is_optional=False,
    singleton=True
)
```

### 2단계: 응답 품질 평가 시스템 (2-3일)

```python
# 기존 응답 생성 플로우에 품질 평가 추가
def enhanced_response_generation(user_query, context):
    """품질 평가가 포함된 응답 생성"""

    # 1. 컨텍스트 인식 프롬프트 생성
    prompt_service = get_service('context_aware_prompt_service')
    prompt_result = prompt_service.generate_contextual_prompt(context)

    # 2. LLM 응답 생성
    openai_service = get_service('openai_service')
    response = openai_service.generate_response(prompt_result['prompt'])

    # 3. 응답 품질 평가
    quality_service = get_service('response_quality_service')
    quality_evaluation = quality_service.evaluate_response_quality(
        prompt=prompt_result['prompt'],
        response=response,
        context=context
    )

    # 4. 낮은 품질인 경우 재생성 (선택적)
    if quality_evaluation['overall_score'] < 0.6:
        # 다른 전략으로 재시도
        alternative_prompt = prompt_service.generate_contextual_prompt(
            context, fallback_strategy=True
        )
        response = openai_service.generate_response(alternative_prompt['prompt'])

    return {
        'response': response,
        'quality_score': quality_evaluation['overall_score'],
        'prompt_strategy': prompt_result['strategy'],
        'metadata': quality_evaluation
    }
```

### 3단계: A/B 테스트 시스템 (3-4일)

```python
# A/B 테스트 통합
def ab_test_integrated_response(user_session_id, user_query, context):
    """A/B 테스트가 통합된 응답 생성"""

    ab_test_service = get_service('ab_test_service')

    # 1. 사용자를 활성 테스트에 할당
    test_assignment = ab_test_service.assign_user_to_test(user_session_id)

    # 2. 할당된 변형에 따른 프롬프트 생성
    if test_assignment['assigned']:
        # 테스트 변형 적용
        context['ab_test_variation'] = test_assignment['variation']

    # 3. 응답 생성
    response_result = enhanced_response_generation(user_query, context)

    # 4. 테스트 상호작용 기록
    if test_assignment['assigned']:
        ab_test_service.record_test_interaction(
            user_session_id=user_session_id,
            test_id=test_assignment['test_id'],
            interaction_type='response_generated',
            metrics={
                'quality_score': response_result['quality_score'],
                'response_length': len(response_result['response']),
                'prompt_strategy': response_result['prompt_strategy']
            }
        )

    return response_result
```

### 4단계: 지속적 최적화 (ongoing)

```python
# 자동 최적화 스케줄러
def automated_optimization_scheduler():
    """자동 최적화 스케줄러 (크론잡으로 실행)"""

    optimization_service = get_service('prompt_optimization_service')

    # 1. 주간 성능 분석
    weekly_analysis = optimization_service.analyze_weekly_performance()

    # 2. 개선이 필요한 영역 식별
    improvement_areas = optimization_service.identify_improvement_areas(weekly_analysis)

    # 3. 자동 A/B 테스트 제안
    for area in improvement_areas:
        if area['confidence'] > 0.8:  # 높은 신뢰도인 경우만
            test_proposal = optimization_service.propose_ab_test(area)

            # 자동 승인 조건 확인
            if test_proposal['risk_level'] == 'low':
                ab_test_service.create_ab_test(**test_proposal['config'])

    # 4. 성능 보고서 생성
    report = optimization_service.generate_optimization_report()

    # 5. 알림 발송 (관리자에게)
    send_optimization_report(report)
```

## 📊 성공 지표 및 모니터링

### 핵심 KPI
1. **응답 품질**: 전체 평균 품질 점수 > 4.5/5.0
2. **A/B 테스트 효율**: 월 2-3개 테스트, 개선율 > 20%
3. **사용자 만족도**: 프롬프트 만족도 > 4.5/5.0
4. **시스템 완성도**: 모든 Phase 통합 효과 > 80%

### 모니터링 대시보드
- 실시간 응답 품질 지표
- A/B 테스트 진행 현황 및 결과
- 프롬프트 전략별 성능 비교
- 사용자 피드백 패턴 분석
- 지속적 개선 트렌드

## 🔮 전체 시스템 완성

### Phase 통합 시너지
```python
# 모든 Phase가 통합된 최종 플로우
def complete_ecoguide_flow(image, user_location, user_session):
    """완전한 EcoGuide 분석 플로우"""

    # Phase 0: 기존 이미지 분석
    vision_result = vision_service.analyze_image_pipeline(image)

    # Phase 1: 사용자 피드백 준비
    feedback_context = prepare_feedback_context(vision_result)

    # Phase 3: RAG 기반 지자체 정보
    district_guidance = rag_service.get_district_guidance(
        query=f"{vision_result.category} 배출 방법",
        district_code=get_district_code(user_location),
        item_info=vision_result.to_dict()
    )

    # Phase 4: 최적화된 프롬프트로 최종 응답
    final_context = PromptContext(
        user_session_id=user_session.id,
        vision_result=vision_result.to_dict(),
        rag_context=district_guidance,
        user_history=user_session.history,
        # ... 기타 컨텍스트
    )

    optimized_response = ab_test_integrated_response(
        user_session.id,
        "대형폐기물 배출 안내",
        final_context
    )

    # Phase 2: 라벨링 데이터 저장
    labeling_service.save_analysis_data(
        original_image=image,
        vision_result=vision_result.to_dict(),
        final_response=optimized_response,
        context=final_context
    )

    return {
        'vision_analysis': vision_result,
        'district_guidance': district_guidance,
        'optimized_response': optimized_response,
        'feedback_interface': feedback_context,
        'overall_confidence': calculate_system_confidence(
            vision_result, district_guidance, optimized_response
        )
    }
```

## 💡 구현 팁

1. **단계적 도입**: 기본 컨텍스트 인식부터 시작하여 점진적으로 고도화
2. **성능 모니터링**: 모든 최적화의 효과를 정량적으로 측정
3. **사용자 중심**: 기술적 완성도보다 사용자 경험 개선에 집중
4. **지속적 개선**: 자동화된 최적화 시스템으로 장기적 품질 유지

이 Phase 4는 **모든 Phase의 성과를 통합하여 완전한 AI 서비스**를 완성하며, 지속적인 자가 개선을 통해 장기적으로 경쟁 우위를 확보합니다.