"""
정확도 추적 및 분석 서비스

원래 설계서의 AccuracyTrackingService를 구현하여
피드백 데이터를 기반으로 AI 모델의 정확도를 실시간으로 추적하고 개선점을 식별합니다.
"""
from src.app.core.base_service import BaseService
from src.app.core.config import Config
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


class AccuracyTrackingService(BaseService):
    """정확도 추적 및 분석 서비스"""

    def __init__(self, config: Config):
        super().__init__(config)
        # 실제 운영환경에서는 PostgreSQL의 accuracy_metrics 테이블 사용
        # 현재는 메모리 기반으로 구현
        self.accuracy_data = {
            'daily_metrics': defaultdict(lambda: {
                'classification_total': 0,
                'classification_correct': 0,
                'size_total': 0,
                'size_correct': 0,
                'total_feedback': 0,
                'confidence_ratings': [],
                'improvement_areas': [],
                'object_name_corrections': 0
            }),
            'category_performance': defaultdict(lambda: {
                'total': 0,
                'correct': 0,
                'common_errors': []
            }),
            'size_performance': {
                'estimation_errors': [],
                'user_provided_count': 0,
                'correction_patterns': []
            },
            'object_name_performance': {
                'total_corrections': 0,
                'correction_patterns': [],
                'frequently_corrected_items': defaultdict(int)
            }
        }

    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "AccuracyTrackingService"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "1.0.0"

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "AI 모델 정확도 추적 및 성능 분석 서비스"

    def update_accuracy_metrics(self, feedback_record: Dict[str, Any]) -> None:
        """피드백을 기반으로 정확도 지표를 업데이트합니다."""

        try:
            validated_feedback = feedback_record.get('validated_feedback', {})
            today = datetime.now().strftime('%Y-%m-%d')

            # 1. 분류 정확도 업데이트
            self._update_classification_accuracy(validated_feedback, today)

            # 2. 크기 추정 정확도 업데이트
            self._update_size_estimation_accuracy(validated_feedback, today)

            # 3. 전체 만족도 업데이트
            self._update_overall_satisfaction(validated_feedback, today)

            # 4. 개선 포인트 식별
            self._identify_improvement_points(validated_feedback, today)

            # 5. 품목명 변경 추적 (새로 추가)
            self._update_object_name_accuracy(validated_feedback, today)

            logger.info(f"Accuracy metrics updated for feedback: {feedback_record.get('id')}")

        except Exception as e:
            logger.error(f"Error updating accuracy metrics: {e}", exc_info=True)

    def _update_classification_accuracy(self, validated_feedback: Dict[str, Any], date: str) -> None:
        """분류 정확도를 업데이트합니다."""

        classification_data = validated_feedback.get('classification', {})
        is_correct = classification_data.get('is_correct', False)
        confidence_rating = classification_data.get('confidence_rating')

        # 일별 메트릭 업데이트
        daily_metrics = self.accuracy_data['daily_metrics'][date]
        daily_metrics['classification_total'] += 1
        if is_correct:
            daily_metrics['classification_correct'] += 1

        if confidence_rating:
            daily_metrics['confidence_ratings'].append({
                'type': 'classification',
                'rating': confidence_rating,
                'is_correct': is_correct
            })

        # 카테고리별 성능 추적
        original_category = classification_data.get('original_primary_category', 'UNKNOWN')
        category_perf = self.accuracy_data['category_performance'][original_category]
        category_perf['total'] += 1
        if is_correct:
            category_perf['correct'] += 1
        else:
            # 오류 패턴 기록
            corrected_label = classification_data.get('corrected_label')
            if corrected_label:
                category_perf['common_errors'].append({
                    'original': classification_data.get('original_object_name'),
                    'corrected': corrected_label,
                    'timestamp': datetime.now().isoformat()
                })

    def _update_size_estimation_accuracy(self, validated_feedback: Dict[str, Any], date: str) -> None:
        """크기 추정 정확도를 업데이트합니다."""

        size_data = validated_feedback.get('size', {})
        size_available = size_data.get('size_available', False)
        is_correct = size_data.get('is_correct')
        confidence_rating = size_data.get('confidence_rating')

        if not size_available:
            return

        # 일별 메트릭 업데이트
        daily_metrics = self.accuracy_data['daily_metrics'][date]
        if is_correct is not None:  # 크기 평가가 있는 경우만
            daily_metrics['size_total'] += 1
            if is_correct:
                daily_metrics['size_correct'] += 1

        if confidence_rating:
            daily_metrics['confidence_ratings'].append({
                'type': 'size',
                'rating': confidence_rating,
                'is_correct': is_correct
            })

        # 사용자 제공 크기 추적
        if size_data.get('user_provided_size'):
            self.accuracy_data['size_performance']['user_provided_count'] += 1

            # 수정된 치수와 원본 치수 비교
            corrected_dims = size_data.get('corrected_dimensions', {})
            original_dims = size_data.get('original_dimensions', {})

            if corrected_dims and original_dims:
                self._analyze_size_correction_pattern(original_dims, corrected_dims)

    def _update_overall_satisfaction(self, validated_feedback: Dict[str, Any], date: str) -> None:
        """전체 만족도를 업데이트합니다."""

        daily_metrics = self.accuracy_data['daily_metrics'][date]
        daily_metrics['total_feedback'] += 1

        # 피드백 품질 지표 추가
        quality_indicators = validated_feedback.get('feedback_quality_indicators', {})
        if quality_indicators.get('has_additional_notes'):
            overall_data = validated_feedback.get('overall', {})
            notes = overall_data.get('additional_notes')
            if notes:
                daily_metrics['improvement_areas'].append({
                    'user_note': notes,
                    'timestamp': datetime.now().isoformat()
                })

    def _identify_improvement_points(self, validated_feedback: Dict[str, Any], date: str) -> None:
        """개선이 필요한 영역을 식별합니다."""

        classification_data = validated_feedback.get('classification', {})
        size_data = validated_feedback.get('size', {})

        improvement_points = []

        # 분류 개선점
        if not classification_data.get('is_correct'):
            improvement_points.append({
                'area': 'classification',
                'original_category': classification_data.get('original_primary_category'),
                'corrected_label': classification_data.get('corrected_label'),
                'priority': self._calculate_priority(classification_data.get('confidence_rating', 3))
            })

        # 크기 추정 개선점
        if size_data.get('is_correct') is False:
            improvement_points.append({
                'area': 'size_estimation',
                'size_type': 'dimension_estimation',
                'confidence': size_data.get('confidence_rating', 3),
                'priority': self._calculate_priority(size_data.get('confidence_rating', 3))
            })

        if improvement_points:
            daily_metrics = self.accuracy_data['daily_metrics'][date]
            daily_metrics['improvement_areas'].extend(improvement_points)

    def _analyze_size_correction_pattern(self, original_dims: Dict[str, Any],
                                       corrected_dims: Dict[str, Any]) -> None:
        """크기 수정 패턴을 분석합니다."""

        patterns = self.accuracy_data['size_performance']['correction_patterns']

        for dim_type in ['width_cm', 'height_cm', 'depth_cm']:
            original_val = original_dims.get(dim_type, 0)
            corrected_val = corrected_dims.get(dim_type, 0)

            if original_val > 0 and corrected_val > 0:
                error_ratio = abs(original_val - corrected_val) / original_val
                patterns.append({
                    'dimension_type': dim_type,
                    'original_value': original_val,
                    'corrected_value': corrected_val,
                    'error_ratio': error_ratio,
                    'timestamp': datetime.now().isoformat()
                })

    def _update_object_name_accuracy(self, validated_feedback: Dict[str, Any], date: str) -> None:
        """품목명 변경을 추적합니다."""

        classification_data = validated_feedback.get('classification', {})
        is_object_name_changed = classification_data.get('is_object_name_changed', False)

        if not is_object_name_changed:
            return

        # 일별 메트릭 업데이트
        daily_metrics = self.accuracy_data['daily_metrics'][date]
        daily_metrics['object_name_corrections'] += 1

        # 전체 품목명 변경 통계
        object_name_perf = self.accuracy_data['object_name_performance']
        object_name_perf['total_corrections'] += 1

        # 변경 패턴 기록
        original_name = classification_data.get('original_object_name', 'UNKNOWN')
        corrected_name = classification_data.get('corrected_object_name', 'UNKNOWN')

        correction_pattern = {
            'original_object_name': original_name,
            'corrected_object_name': corrected_name,
            'timestamp': datetime.now().isoformat()
        }
        object_name_perf['correction_patterns'].append(correction_pattern)

        # 자주 수정되는 물품 추적
        object_name_perf['frequently_corrected_items'][original_name] += 1

        logger.info(f"Object name correction tracked: {original_name} → {corrected_name}")

    def _calculate_priority(self, confidence_rating: int) -> int:
        """신뢰도 기반으로 개선 우선순위를 계산합니다."""
        if confidence_rating <= 2:
            return 5  # 높은 우선순위
        elif confidence_rating == 3:
            return 3  # 중간 우선순위
        else:
            return 1  # 낮은 우선순위

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """실시간 정확도 지표를 조회합니다."""

        try:
            # 최근 7일 데이터 집계
            recent_dates = self._get_recent_dates(7)
            aggregated_metrics = self._aggregate_metrics(recent_dates)

            return {
                'classification_accuracy': self._calculate_classification_accuracy(aggregated_metrics),
                'size_estimation_accuracy': self._calculate_size_accuracy(aggregated_metrics),
                'user_satisfaction': self._calculate_user_satisfaction(aggregated_metrics),
                'total_feedback_count': aggregated_metrics['total_feedback'],
                'object_name_corrections': self._get_object_name_statistics(),
                'recent_trends': self._get_recent_trends(),
                'improvement_suggestions': self._get_improvement_suggestions(),
                'category_performance': self._get_category_performance_summary()
            }

        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}", exc_info=True)
            return self._get_default_metrics()

    def _get_recent_dates(self, days: int) -> List[str]:
        """최근 N일의 날짜 목록을 반환합니다."""
        dates = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            dates.append(date)
        return dates

    def _aggregate_metrics(self, dates: List[str]) -> Dict[str, Any]:
        """지정된 날짜들의 메트릭을 집계합니다."""

        total_classification = 0
        correct_classification = 0
        total_size = 0
        correct_size = 0
        total_feedback = 0
        confidence_ratings = []

        for date in dates:
            if date in self.accuracy_data['daily_metrics']:
                metrics = self.accuracy_data['daily_metrics'][date]
                total_classification += metrics['classification_total']
                correct_classification += metrics['classification_correct']
                total_size += metrics['size_total']
                correct_size += metrics['size_correct']
                total_feedback += metrics['total_feedback']
                confidence_ratings.extend(metrics['confidence_ratings'])

        return {
            'total_classification': total_classification,
            'correct_classification': correct_classification,
            'total_size': total_size,
            'correct_size': correct_size,
            'total_feedback': total_feedback,
            'confidence_ratings': confidence_ratings
        }

    def _calculate_classification_accuracy(self, metrics: Dict[str, Any]) -> float:
        """분류 정확도를 계산합니다."""
        total = metrics['total_classification']
        correct = metrics['correct_classification']
        return correct / total if total > 0 else 0.0

    def _calculate_size_accuracy(self, metrics: Dict[str, Any]) -> float:
        """크기 추정 정확도를 계산합니다."""
        total = metrics['total_size']
        correct = metrics['correct_size']
        return correct / total if total > 0 else 0.0

    def _calculate_user_satisfaction(self, metrics: Dict[str, Any]) -> float:
        """사용자 만족도를 계산합니다."""
        confidence_ratings = metrics['confidence_ratings']
        if not confidence_ratings:
            return 0.0

        avg_rating = sum(rating['rating'] for rating in confidence_ratings) / len(confidence_ratings)
        return avg_rating / 5.0  # 0.0 ~ 1.0 범위로 정규화

    def _get_recent_trends(self) -> Dict[str, Any]:
        """최근 트렌드를 분석합니다."""
        recent_dates = self._get_recent_dates(7)

        daily_accuracies = []
        for date in reversed(recent_dates):  # 시간순 정렬
            if date in self.accuracy_data['daily_metrics']:
                metrics = self.accuracy_data['daily_metrics'][date]
                if metrics['classification_total'] > 0:
                    accuracy = metrics['classification_correct'] / metrics['classification_total']
                    daily_accuracies.append(accuracy)

        if len(daily_accuracies) >= 2:
            trend = daily_accuracies[-1] - daily_accuracies[0]
            return {
                'classification_trend': 'improving' if trend > 0.05 else 'declining' if trend < -0.05 else 'stable',
                'trend_value': trend
            }

        return {'classification_trend': 'insufficient_data', 'trend_value': 0.0}

    def _get_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """개선 제안을 생성합니다."""
        suggestions = []

        # 카테고리별 성능 분석
        for category, perf in self.accuracy_data['category_performance'].items():
            if perf['total'] >= 3:  # 충분한 데이터가 있는 경우
                accuracy = perf['correct'] / perf['total']
                if accuracy < 0.7:  # 70% 미만인 경우
                    suggestions.append({
                        'type': 'category_improvement',
                        'category': category,
                        'current_accuracy': accuracy,
                        'priority': 'high' if accuracy < 0.5 else 'medium',
                        'suggestion': f"{category} 카테고리의 분류 정확도 개선이 필요합니다"
                    })

        # 크기 추정 개선
        size_perf = self.accuracy_data['size_performance']
        if size_perf['user_provided_count'] > 5:  # 사용자 수정이 많은 경우
            suggestions.append({
                'type': 'size_estimation_improvement',
                'user_corrections': size_perf['user_provided_count'],
                'priority': 'medium',
                'suggestion': '크기 추정 알고리즘 개선이 필요합니다'
            })

        return suggestions

    def _get_category_performance_summary(self) -> Dict[str, Any]:
        """카테고리별 성능 요약을 반환합니다."""
        summary = {}

        for category, perf in self.accuracy_data['category_performance'].items():
            if perf['total'] > 0:
                summary[category] = {
                    'accuracy': perf['correct'] / perf['total'],
                    'total_samples': perf['total'],
                    'error_count': len(perf['common_errors'])
                }

        return summary

    def _get_object_name_statistics(self) -> Dict[str, Any]:
        """품목명 수정 통계를 반환합니다."""
        object_name_perf = self.accuracy_data['object_name_performance']

        # 자주 수정되는 물품 상위 5개
        frequently_corrected = sorted(
            object_name_perf['frequently_corrected_items'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'total_corrections': object_name_perf['total_corrections'],
            'correction_rate': (
                object_name_perf['total_corrections'] /
                sum(metrics['classification_total'] for metrics in self.accuracy_data['daily_metrics'].values())
                if sum(metrics['classification_total'] for metrics in self.accuracy_data['daily_metrics'].values()) > 0
                else 0.0
            ),
            'frequently_corrected_items': [
                {'item_name': name, 'correction_count': count}
                for name, count in frequently_corrected
            ],
            'recent_corrections': object_name_perf['correction_patterns'][-10:] if object_name_perf['correction_patterns'] else []
        }

    def _get_default_metrics(self) -> Dict[str, Any]:
        """기본 메트릭을 반환합니다."""
        return {
            'classification_accuracy': 0.0,
            'size_estimation_accuracy': 0.0,
            'user_satisfaction': 0.0,
            'total_feedback_count': 0,
            'object_name_corrections': {
                'total_corrections': 0,
                'correction_rate': 0.0,
                'frequently_corrected_items': [],
                'recent_corrections': []
            },
            'recent_trends': {'classification_trend': 'no_data', 'trend_value': 0.0},
            'improvement_suggestions': [],
            'category_performance': {}
        }

    def generate_accuracy_report(self, period: str = 'weekly') -> Dict[str, Any]:
        """정확도 보고서를 생성합니다."""

        days = {'daily': 1, 'weekly': 7, 'monthly': 30}.get(period, 7)
        recent_dates = self._get_recent_dates(days)
        aggregated_metrics = self._aggregate_metrics(recent_dates)

        return {
            'period': period,
            'summary': {
                'total_feedback': aggregated_metrics['total_feedback'],
                'classification_accuracy': self._calculate_classification_accuracy(aggregated_metrics),
                'size_estimation_accuracy': self._calculate_size_accuracy(aggregated_metrics),
                'user_satisfaction': self._calculate_user_satisfaction(aggregated_metrics)
            },
            'detailed_metrics': self._get_detailed_metrics(recent_dates),
            'object_name_statistics': self._get_object_name_statistics(),
            'trend_analysis': self._get_recent_trends(),
            'recommendations': self._get_improvement_suggestions(),
            'category_breakdown': self._get_category_performance_summary(),
            'generated_at': datetime.now().isoformat()
        }

    def _get_detailed_metrics(self, dates: List[str]) -> Dict[str, Any]:
        """상세 메트릭을 반환합니다."""
        detailed = {}

        for date in dates:
            if date in self.accuracy_data['daily_metrics']:
                metrics = self.accuracy_data['daily_metrics'][date]
                detailed[date] = {
                    'classification_accuracy': (
                        metrics['classification_correct'] / metrics['classification_total']
                        if metrics['classification_total'] > 0 else 0.0
                    ),
                    'size_accuracy': (
                        metrics['size_correct'] / metrics['size_total']
                        if metrics['size_total'] > 0 else 0.0
                    ),
                    'feedback_count': metrics['total_feedback']
                }

        return detailed