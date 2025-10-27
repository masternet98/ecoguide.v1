
from src.app.core.base_service import BaseService
from src.app.core.config import Config
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class ConfirmationService(BaseService):
    """
    AI 분석 결과에 대한 사용자의 피드백을 체계적으로 수집하고 저장하는 서비스입니다.
    원래 설계서의 FeedbackService 기능을 통합하여 구현되었습니다.
    """

    def __init__(self, config: Config):
        super().__init__(config)
        # 실제 운영환경에서는 PostgreSQL 등 데이터베이스 연결
        # 현재는 로그 및 파일 기반 저장으로 구현
        self.feedback_storage = []  # 메모리 기반 임시 저장소
        self.accuracy_tracking_service = None  # 지연 로딩

    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "ConfirmationService"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "1.0.0"

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "AI 분석 결과에 대한 사용자 피드백 수집 및 저장 서비스"

    def save_confirmation(
        self,
        session_id: str,
        image_id: str,
        original_analysis: Dict[str, Any],
        is_correct: bool,
        corrected_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        사용자의 확인 결과를 체계적으로 저장합니다.

        Args:
            session_id: 사용자 세션 ID
            image_id: 분석된 이미지의 고유 ID
            original_analysis: AI가 분석한 원본 결과
            is_correct: 사용자가 전체적으로 확인했는지 여부
            corrected_data: 사용자가 수정한 데이터 및 피드백 상세 정보

        Returns:
            저장 결과 (성공 여부, ID 등)
        """
        try:
            # 1. 피드백 데이터 검증 및 구조화
            validated_feedback = self._validate_and_structure_feedback(
                original_analysis, corrected_data, is_correct
            )

            # 2. 데이터베이스 저장용 레코드 생성
            feedback_record = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'image_id': image_id,
                'original_analysis': original_analysis,
                'is_correct': is_correct,
                'corrected_data': corrected_data,
                'validated_feedback': validated_feedback,
                'confirmed_at': datetime.now().isoformat(),
                'processed': False
            }

            # 3. 저장 처리 (실제 DB 대신 로깅 및 메모리 저장)
            self._save_feedback_to_storage(feedback_record)

            # 4. 정확도 지표 업데이트 (향후 AccuracyTrackingService 연동)
            self._update_accuracy_metrics(validated_feedback)

            # 5. 감사 메시지 생성
            thank_you_message = self._generate_thank_you_message(validated_feedback)

            return {
                'success': True,
                'confirmation_id': feedback_record['id'],
                'message': thank_you_message,
                'feedback_quality_score': self._calculate_feedback_quality(validated_feedback)
            }

        except Exception as e:
            logger.error(f"Error saving confirmation: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '피드백 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
            }

    def _validate_and_structure_feedback(self, original_analysis: Dict[str, Any],
                                       corrected_data: Optional[Dict[str, Any]],
                                       is_correct: bool) -> Dict[str, Any]:
        """피드백 데이터를 검증하고 구조화합니다."""

        feedback_details = corrected_data.get('feedback_details', {}) if corrected_data else {}
        corrected_classification = corrected_data.get('classification', {}) if corrected_data else {}

        # 분류 피드백 처리
        classification_feedback = feedback_details.get('classification', {})
        original_object_name = original_analysis.get('object_name')

        # corrected_data에서도 object_name 확인
        corrected_object_name = (
            classification_feedback.get('corrected_object_name') or
            corrected_classification.get('object_name')
        )

        # 피드백 정보에서 수정 여부 확인
        is_object_name_changed = (
            classification_feedback.get('is_object_name_changed', False) or
            classification_feedback.get('is_object_name_corrected', False) or
            (original_object_name != corrected_object_name and corrected_object_name is not None)
        )

        classification_data = {
            'is_correct': classification_feedback.get('classification_accurate', is_correct),
            'confidence_rating': classification_feedback.get('confidence_level'),
            'corrected_label': classification_feedback.get('corrected_label'),
            'corrected_category': classification_feedback.get('corrected_category'),
            'original_object_name': original_object_name,
            'original_primary_category': original_analysis.get('primary_category'),
            'original_secondary_category': original_analysis.get('secondary_category'),
            # 품목명 관련 필드
            'object_name_accurate': classification_feedback.get('object_name_accurate', True),
            'corrected_object_name': corrected_object_name,
            'is_object_name_changed': is_object_name_changed or (original_object_name != corrected_object_name and corrected_object_name is not None)
        }

        # 크기 피드백 처리
        size_feedback = feedback_details.get('size', {})
        size_data = {
            'size_available': size_feedback.get('size_available', True),
            'is_correct': size_feedback.get('size_accurate'),
            'confidence_rating': size_feedback.get('confidence_level'),
            'user_provided_size': size_feedback.get('user_provided_size', False),
            'corrected_dimensions': size_feedback.get('corrected_dimensions'),
            'original_dimensions': original_analysis.get('dimensions', {})
        }

        # 전체 피드백 처리
        overall_feedback = feedback_details.get('overall', {})
        overall_data = {
            'user_confirmed': is_correct,
            'additional_notes': overall_feedback.get('additional_notes'),
            'feedback_timestamp': overall_feedback.get('feedback_timestamp'),
            'session_id': overall_feedback.get('session_id')
        }

        return {
            'classification': classification_data,
            'size': size_data,
            'overall': overall_data,
            'feedback_quality_indicators': {
                'has_confidence_ratings': bool(
                    classification_data.get('confidence_rating') or size_data.get('confidence_rating')
                ),
                'has_corrections': bool(
                    classification_data.get('corrected_label') or size_data.get('corrected_dimensions')
                ),
                'has_additional_notes': bool(overall_data.get('additional_notes')),
                'has_object_name_correction': bool(classification_data.get('is_object_name_changed'))
            }
        }

    def _save_feedback_to_storage(self, feedback_record: Dict[str, Any]) -> None:
        """피드백을 저장소에 저장합니다."""

        # 메모리 저장
        self.feedback_storage.append(feedback_record)

        # 분류 데이터에서 품목명 변경 정보 추출
        classification_data = feedback_record['validated_feedback'].get('classification', {})
        is_object_name_changed = classification_data.get('is_object_name_changed', False)
        original_object_name = classification_data.get('original_object_name')
        corrected_object_name = classification_data.get('corrected_object_name')

        # 로그 저장
        log_message = (f"Feedback saved: ID={feedback_record['id']}, "
                      f"Correct={feedback_record['is_correct']}, "
                      f"Session={feedback_record['session_id']}")

        if is_object_name_changed:
            log_message += f", ObjectName Changed: {original_object_name} → {corrected_object_name}"

        logger.info(log_message)

        # 개발용 콘솔 출력
        print(f"\n=== FEEDBACK RECORD SAVED ===")
        print(f"ID: {feedback_record['id']}")
        print(f"User Confirmed: {feedback_record['is_correct']}")
        print(f"Classification Feedback: {feedback_record['validated_feedback']['classification']}")
        print(f"Size Feedback: {feedback_record['validated_feedback']['size']}")
        if is_object_name_changed:
            print(f"📝 Object Name Changed: {original_object_name} → {corrected_object_name}")
        print(f"================================\n")

    def _update_accuracy_metrics(self, validated_feedback: Dict[str, Any]) -> None:
        """정확도 지표를 업데이트합니다."""

        try:
            # AccuracyTrackingService 지연 로딩
            if self.accuracy_tracking_service is None:
                from src.domains.analysis.services.accuracy_tracking_service import AccuracyTrackingService
                self.accuracy_tracking_service = AccuracyTrackingService(self.config)

            # 가장 최근 피드백 레코드 가져오기
            if self.feedback_storage:
                latest_record = self.feedback_storage[-1]
                self.accuracy_tracking_service.update_accuracy_metrics(latest_record)

        except Exception as e:
            logger.error(f"Error updating accuracy metrics: {e}", exc_info=True)

        # 로그 기록
        classification_data = validated_feedback['classification']
        size_data = validated_feedback['size']
        logger.info(f"Accuracy update - Classification: {classification_data['is_correct']}, "
                   f"Size: {size_data['is_correct']}")

    def _generate_thank_you_message(self, validated_feedback: Dict[str, Any]) -> str:
        """피드백 내용에 따른 감사 메시지를 생성합니다."""

        quality_indicators = validated_feedback['feedback_quality_indicators']

        # 품목명 수정이 있는 경우 우선적으로 언급
        if quality_indicators['has_object_name_correction']:
            if quality_indicators['has_corrections'] or quality_indicators['has_confidence_ratings']:
                return "품목명 수정과 상세 피드백을 주셔서 감사합니다! 더 정확한 품목 인식에 큰 도움이 됩니다."
            else:
                return "품목명 수정을 주셔서 감사합니다! 향후 품목 인식 정확도 개선에 활용하겠습니다."
        elif quality_indicators['has_confidence_ratings'] and quality_indicators['has_corrections']:
            return "상세한 피드백과 수정 정보를 주셔서 감사합니다! AI 정확도 향상에 큰 도움이 됩니다."
        elif quality_indicators['has_confidence_ratings']:
            return "신뢰도 평가를 주셔서 감사합니다! AI 성능 개선에 활용하겠습니다."
        elif quality_indicators['has_corrections']:
            return "수정 정보를 주셔서 감사합니다! 향후 분석 정확도가 개선될 것입니다."
        else:
            return "피드백을 주셔서 감사합니다!"

    def _calculate_feedback_quality(self, validated_feedback: Dict[str, Any]) -> float:
        """피드백 품질 점수를 계산합니다 (0.0 ~ 1.0)."""

        quality_indicators = validated_feedback['feedback_quality_indicators']
        score = 0.0

        # 기본 확인: 0.25점
        score += 0.25

        # 신뢰도 평가: 0.25점
        if quality_indicators['has_confidence_ratings']:
            score += 0.25

        # 수정 정보: 0.25점
        if quality_indicators['has_corrections']:
            score += 0.25

        # 품목명 수정: 0.15점 (높은 가치의 피드백)
        if quality_indicators['has_object_name_correction']:
            score += 0.15

        # 추가 메모: 0.1점
        if quality_indicators['has_additional_notes']:
            score += 0.1

        return min(score, 1.0)

    def get_feedback_statistics(self, date_range: tuple = None) -> Dict[str, Any]:
        """피드백 통계를 조회합니다."""

        # 현재는 메모리 기반으로 간단히 구현
        total_count = len(self.feedback_storage)
        if total_count == 0:
            return {
                'total_feedback_count': 0,
                'classification_accuracy': 0.0,
                'size_estimation_accuracy': 0.0,
                'average_quality_score': 0.0
            }

        correct_classifications = sum(
            1 for record in self.feedback_storage
            if record['validated_feedback']['classification']['is_correct']
        )

        correct_sizes = sum(
            1 for record in self.feedback_storage
            if record['validated_feedback']['size']['is_correct'] is True
        )

        size_responses = sum(
            1 for record in self.feedback_storage
            if record['validated_feedback']['size']['is_correct'] is not None
        )

        return {
            'total_feedback_count': total_count,
            'classification_accuracy': correct_classifications / total_count if total_count > 0 else 0.0,
            'size_estimation_accuracy': correct_sizes / size_responses if size_responses > 0 else 0.0,
            'average_quality_score': sum(
                self._calculate_feedback_quality(record['validated_feedback'])
                for record in self.feedback_storage
            ) / total_count if total_count > 0 else 0.0
        }
