"""
AI 분석 결과 매핑 서비스

AI 분석 결과를 waste_types.json 계층 구조에 매핑하는 서비스입니다.
분류가 없으면 "기타" 카테고리로 분류하며, 사용자가 직접 입력할 수 있도록 제공합니다.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from src.app.core.base_service import BaseService
from src.app.core.config import Config

logger = logging.getLogger(__name__)


class AIClassificationMapper(BaseService):
    """AI 분석 결과를 waste_types.json 기반으로 매핑하는 서비스

    분류를 찾지 못한 경우 "기타"로 분류하고, 사용자가 직접 입력할 수 있는 필드를 제공합니다.
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self.waste_types_file = Path("uploads/waste_types/waste_types.json")
        self.waste_types_data = self._load_waste_types_data()

    def _load_waste_types_data(self) -> Dict[str, Any]:
        """waste_types.json 파일을 로드합니다."""
        try:
            if not self.waste_types_file.exists():
                logger.error(f"Waste types file not found: {self.waste_types_file}")
                return {}

            with open(self.waste_types_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Waste types data loaded: {len(data)} categories")
                return data

        except Exception as e:
            logger.error(f"Error loading waste types data: {e}")
            return {}

    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "AIClassificationMapper"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "3.0.0"  # 사용자 입력 기반 분류로 업그레이드

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "AI 분석 결과를 waste_types.json 기반으로 매핑하고 미분류 항목은 사용자 입력을 지원하는 서비스"

    def map_legacy_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI 분석 결과를 waste_types.json 기반으로 매핑합니다.

        분류를 찾지 못한 경우 "기타"로 분류하며, 사용자가 직접 입력할 수 있도록 제공합니다.

        Args:
            analysis_result: AI 분석 결과

        Returns:
            매핑된 분류 결과 (사용자 입력 필드 포함)
        """
        try:
            # 기존 분석 결과에서 필요한 정보 추출
            object_name = analysis_result.get('object_name', '')
            primary_category = analysis_result.get('primary_category', '')
            secondary_category = analysis_result.get('secondary_category', '')
            confidence = analysis_result.get('confidence', 0.0)
            dimensions = analysis_result.get('dimensions', {})
            reasoning = analysis_result.get('reasoning', '')

            # waste_types.json에서 최적 분류 찾기
            best_main, best_sub, match_score = self._find_best_classification(object_name, primary_category, secondary_category)

            # 분류를 찾지 못한 경우 "기타"로 분류
            requires_user_input = False
            if not best_main or match_score < 0.3:
                best_main = '기타'
                best_sub = '분류불가'
                match_score = 0.0
                requires_user_input = True
                logger.info(f"Could not classify '{object_name}' - marked for user input")

            # 매핑된 결과 구성
            mapped_result = {
                'object_name': object_name,
                'main_category': best_main,
                'sub_category': best_sub,
                'dimensions': dimensions,
                'confidence': max(confidence, match_score),
                'reasoning': reasoning,
                'mapping_info': {
                    'original_primary': primary_category,
                    'original_secondary': secondary_category,
                    'mapping_confidence': match_score,
                    'needs_review': match_score < 0.5,
                    'requires_user_input': requires_user_input,  # 새로운 필드
                    'user_custom_name': None  # 사용자가 입력할 내용
                }
            }

            logger.info(f"Mapped {primary_category}/{secondary_category} -> {best_main}/{best_sub} (score: {match_score:.2f}, user_input_required: {requires_user_input})")
            return mapped_result

        except Exception as e:
            logger.error(f"Error mapping analysis: {e}")
            return self._create_fallback_result(analysis_result)

    def enhance_with_ai_suggestion(self, mapped_result: Dict[str, Any], waste_service) -> Dict[str, Any]:
        """
        매핑된 결과를 AI 추천으로 개선합니다.

        Args:
            mapped_result: 매핑된 결과
            waste_service: WasteClassificationService 인스턴스

        Returns:
            AI 추천으로 개선된 결과
        """
        try:
            object_name = mapped_result.get('object_name', '')

            if not object_name or not waste_service:
                return mapped_result

            # AI 기반 최적 분류 찾기
            best_main, best_sub, ai_confidence = waste_service.find_best_match(object_name)

            if best_main and ai_confidence > 0.5:  # AI 추천 신뢰도가 높은 경우
                # 기존 매핑과 AI 추천 비교
                current_main = mapped_result.get('main_category')
                current_sub = mapped_result.get('sub_category')

                suggestion_info = {
                    'has_ai_suggestion': True,
                    'ai_main_category': best_main,
                    'ai_sub_category': best_sub,
                    'ai_confidence': ai_confidence,
                    'differs_from_mapping': (best_main != current_main or best_sub != current_sub)
                }

                # AI 추천이 더 신뢰도가 높다면 교체
                if ai_confidence > mapped_result.get('confidence', 0.0):
                    mapped_result.update({
                        'main_category': best_main,
                        'sub_category': best_sub,
                        'confidence': ai_confidence,
                        'reasoning': f"AI 추천: {object_name}에 대한 최적 분류"
                    })
                    suggestion_info['recommendation_applied'] = True
                else:
                    suggestion_info['recommendation_applied'] = False

                mapped_result['ai_suggestion'] = suggestion_info

            return mapped_result

        except Exception as e:
            logger.error(f"Error enhancing with AI suggestion: {e}")
            return mapped_result

    def _find_best_classification(self, object_name: str, primary: str, secondary: str) -> Tuple[Optional[str], Optional[str], float]:
        """waste_types.json에서 최적의 분류를 찾습니다."""
        best_main = None
        best_sub = None
        best_score = 0.0

        if not self.waste_types_data:
            return None, None, 0.0

        # 1. object_name으로 직접 매칭 시도
        if object_name:
            for main_category, category_data in self.waste_types_data.items():
                subcategories = category_data.get('세분류', [])
                for subcategory in subcategories:
                    sub_name = subcategory.get('명칭', '')
                    examples = subcategory.get('예시', [])

                    # 세분류명과 매칭
                    if object_name.lower() in sub_name.lower():
                        score = len(object_name) / len(sub_name) if sub_name else 0
                        if score > best_score:
                            best_main = main_category
                            best_sub = sub_name
                            best_score = score

                    # 예시와 매칭
                    for example in examples:
                        if object_name.lower() in example.lower() or example.lower() in object_name.lower():
                            score = min(len(object_name), len(example)) / max(len(object_name), len(example)) if example else 0
                            if score > best_score:
                                best_main = main_category
                                best_sub = sub_name
                                best_score = score

        # 2. primary/secondary 카테고리로 매칭 시도
        if best_score < 0.5 and (primary or secondary):
            for main_category, category_data in self.waste_types_data.items():
                # 주분류명과 매칭
                if primary and primary.lower() in main_category.lower():
                    score = 0.6
                    if score > best_score:
                        best_main = main_category
                        # 첫 번째 세분류를 기본으로 선택
                        subcategories = category_data.get('세분류', [])
                        if subcategories:
                            best_sub = subcategories[0].get('명칭', '')
                        best_score = score

        return best_main, best_sub, best_score

    def update_classification_with_user_input(self, mapped_result: Dict[str, Any], user_custom_name: str) -> Dict[str, Any]:
        """사용자가 입력한 분류 정보로 결과를 업데이트합니다.

        Args:
            mapped_result: 매핑된 결과
            user_custom_name: 사용자가 입력한 물품명

        Returns:
            사용자 입력으로 업데이트된 결과
        """
        try:
            if user_custom_name and user_custom_name.strip():
                mapped_result['mapping_info']['user_custom_name'] = user_custom_name.strip()
                logger.info(f"Updated classification with user input: '{user_custom_name}'")

            return mapped_result

        except Exception as e:
            logger.error(f"Error updating classification with user input: {e}")
            return mapped_result

    def _create_fallback_result(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """매핑 실패 시 대체 결과를 생성합니다."""
        return {
            'object_name': analysis_result.get('object_name', '알 수 없음'),
            'main_category': '기타',
            'sub_category': '분류불가',
            'dimensions': analysis_result.get('dimensions', {}),
            'confidence': 0.1,
            'reasoning': '자동 매핑 실패 - 수동 분류 필요',
            'mapping_info': {
                'original_primary': analysis_result.get('primary_category', ''),
                'original_secondary': analysis_result.get('secondary_category', ''),
                'mapping_confidence': 0.1,
                'needs_review': True,
                'mapping_failed': True
            }
        }

    def validate_classification(self, main_category: str, sub_category: str, waste_service) -> Dict[str, Any]:
        """
        분류의 유효성을 검증합니다.

        Args:
            main_category: 주분류
            sub_category: 세분류
            waste_service: WasteClassificationService 인스턴스

        Returns:
            검증 결과
        """
        if not waste_service:
            return {'valid': False, 'reason': 'WasteClassificationService를 사용할 수 없습니다'}

        is_valid = waste_service.validate_classification(main_category, sub_category)

        if is_valid:
            return {'valid': True}
        else:
            # 대안 제안
            suggestions = []
            if main_category in waste_service.get_all_categories():
                subcategories = waste_service.get_subcategories(main_category)
                suggestions = [sub.get('명칭', '') for sub in subcategories[:3]]

            return {
                'valid': False,
                'reason': f'"{main_category}" 분류에 "{sub_category}" 세분류가 존재하지 않습니다',
                'suggestions': suggestions
            }

    def get_mapping_statistics(self) -> Dict[str, Any]:
        """매핑 통계를 반환합니다."""
        if not self.waste_types_data:
            return {'error': 'No waste types data loaded'}

        total_subcategories = 0
        total_examples = 0

        for category_data in self.waste_types_data.values():
            subcategories = category_data.get('세분류', [])
            total_subcategories += len(subcategories)
            for sub in subcategories:
                total_examples += len(sub.get('예시', []))

        return {
            'main_categories': len(self.waste_types_data),
            'total_subcategories': total_subcategories,
            'total_examples': total_examples,
            'data_source': 'waste_types.json',
            'user_input_fallback': '기타 - 분류불가',
            'classification_mode': 'fixed_with_user_input'
        }