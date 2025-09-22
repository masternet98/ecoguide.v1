"""
프롬프트 관리 통합 서비스 모듈입니다.

프롬프트 관리, 렌더링, 검증 모듈들을 통합하여 제공하는 메인 서비스입니다.
"""
from typing import List, Dict, Optional, Any

from src.core.prompt_types import (
    PromptTemplate, FeaturePromptMapping, PromptUsageStats,
    PromptCategory, PromptStatus, PromptConfig
)
from src.core.base_service import BaseService
from src.services.prompt_manager import PromptManager
from src.services.prompt_renderer import PromptRenderer
from src.services.prompt_validator import PromptValidator


class PromptService(BaseService):
    """
    프롬프트 관리 통합 서비스 클래스입니다.

    PromptManager, PromptRenderer, PromptValidator를 통합하여 제공합니다.
    """

    def __init__(self, config: PromptConfig):
        """
        프롬프트 서비스를 초기화합니다.

        Args:
            config: 프롬프트 설정
        """
        # BaseService는 Config 타입을 요구하므로, 임시로 config를 전달
        # 실제로는 PromptConfig만 사용함
        from src.core.config import Config
        super().__init__(config=Config())
        from src.core.logger import get_logger

        self.config = config
        self.logger = get_logger(__name__)

        # 하위 모듈들 초기화
        self.manager = PromptManager(config, self.logger)
        self.renderer = PromptRenderer(config, self.logger)
        self.validator = PromptValidator(config, self.logger)

    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "prompt_service"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "2.0.0"

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "프롬프트 관리, 렌더링, 검증 통합 서비스"

    # ===== PromptManager 위임 메서드들 =====

    def create_prompt(self,
                     name: str,
                     description: str,
                     category: PromptCategory,
                     template: str,
                     created_by: str = "admin",
                     tags: List[str] = None,
                     metadata: Dict[str, Any] = None) -> PromptTemplate:
        """새로운 프롬프트를 생성합니다."""
        return self.manager.create_prompt(
            name=name, description=description, category=category,
            template=template, created_by=created_by,
            tags=tags, metadata=metadata
        )

    def update_prompt(self, prompt_id: str, **kwargs) -> Optional[PromptTemplate]:
        """기존 프롬프트를 수정합니다."""
        return self.manager.update_prompt(prompt_id, **kwargs)

    def delete_prompt(self, prompt_id: str) -> bool:
        """프롬프트를 삭제합니다."""
        return self.manager.delete_prompt(prompt_id)

    def get_prompt(self, prompt_id: str) -> Optional[PromptTemplate]:
        """프롬프트를 조회합니다."""
        return self.manager.get_prompt(prompt_id)

    def list_prompts(self,
                    category: Optional[PromptCategory] = None,
                    status: Optional[PromptStatus] = None,
                    tags: Optional[List[str]] = None) -> List[PromptTemplate]:
        """프롬프트 목록을 조회합니다."""
        return self.manager.list_prompts(category=category, status=status, tags=tags)

    def search_prompts(self, query: str) -> List[PromptTemplate]:
        """프롬프트를 검색합니다."""
        return self.manager.search_prompts(query)

    def map_feature_to_prompt(self,
                             feature_id: str,
                             prompt_id: str,
                             is_default: bool = False,
                             priority: int = 0,
                             conditions: Dict[str, Any] = None) -> bool:
        """기능과 프롬프트를 매핑합니다."""
        return self.manager.map_feature_to_prompt(
            feature_id=feature_id, prompt_id=prompt_id,
            is_default=is_default, priority=priority, conditions=conditions
        )

    def unmap_feature_from_prompt(self, feature_id: str, prompt_id: str) -> bool:
        """기능과 프롬프트 매핑을 제거합니다."""
        return self.manager.unmap_feature_from_prompt(feature_id, prompt_id)

    def get_prompts_for_feature(self, feature_id: str) -> List[PromptTemplate]:
        """특정 기능에 매핑된 프롬프트들을 조회합니다."""
        return self.manager.get_prompts_for_feature(feature_id)

    def get_default_prompt_for_feature(self, feature_id: str) -> Optional[PromptTemplate]:
        """특정 기능의 기본 프롬프트를 조회합니다."""
        return self.manager.get_default_prompt_for_feature(feature_id)

    def get_usage_stats(self, prompt_id: str) -> Optional[PromptUsageStats]:
        """프롬프트 사용 통계를 조회합니다."""
        return self.manager.get_usage_stats(prompt_id)

    def export_prompts(self, category: Optional[PromptCategory] = None) -> Dict[str, Any]:
        """프롬프트를 내보냅니다."""
        return self.manager.export_prompts(category=category)

    def import_prompts(self, import_data: Dict[str, Any], overwrite: bool = False) -> Dict[str, Any]:
        """프롬프트를 가져옵니다."""
        return self.manager.import_prompts(import_data, overwrite=overwrite)

    # ===== PromptRenderer 위임 메서드들 =====

    def render_prompt(self, prompt_id: str, variables: Dict[str, Any] = None) -> Optional[str]:
        """프롬프트를 변수로 렌더링합니다."""
        template = self.get_prompt(prompt_id)
        if not template:
            return None

        rendered = self.renderer.render_prompt(template, variables)

        # 사용 통계 업데이트
        if rendered and self.config.usage_tracking_enabled:
            self.manager.update_usage_stats(prompt_id)

        return rendered

    def render_with_context(self, prompt_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """컨텍스트 정보와 함께 프롬프트를 렌더링합니다."""
        template = self.get_prompt(prompt_id)
        if not template:
            return {
                'success': False,
                'error': '프롬프트를 찾을 수 없습니다.',
                'rendered_text': None
            }

        result = self.renderer.render_with_context(template, context)

        # 사용 통계 업데이트
        if result.get('success') and self.config.usage_tracking_enabled:
            self.manager.update_usage_stats(prompt_id)

        return result

    def preview_render(self, prompt_id: str, sample_variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """프롬프트 렌더링 미리보기를 생성합니다."""
        template = self.get_prompt(prompt_id)
        if not template:
            return {
                'success': False,
                'error': '프롬프트를 찾을 수 없습니다.',
                'preview_text': None
            }

        return self.renderer.preview_render(template, sample_variables)

    def extract_variables(self, template_text: str) -> List[str]:
        """템플릿에서 변수들을 추출합니다."""
        return self.renderer.extract_variables(template_text)

    def validate_variables(self, template_text: str, provided_variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """템플릿 변수의 유효성을 검증합니다."""
        return self.renderer.validate_variables(template_text, provided_variables)

    def analyze_template_complexity(self, template_text: str) -> Dict[str, Any]:
        """템플릿의 복잡도를 분석합니다."""
        return self.renderer.analyze_template_complexity(template_text)

    # ===== PromptValidator 위임 메서드들 =====

    def validate_prompt_template(self, template: str) -> Dict[str, Any]:
        """프롬프트 템플릿의 유효성을 검증합니다."""
        return self.validator.validate_prompt_template(template)

    def validate_prompt_structure(self, template: PromptTemplate) -> Dict[str, Any]:
        """프롬프트 전체 구조의 유효성을 검증합니다."""
        return self.validator.validate_prompt_structure(template)

    def validate_prompt_content(self, template: str, category: Optional[PromptCategory] = None) -> Dict[str, Any]:
        """프롬프트 내용의 유효성을 검증합니다."""
        return self.validator.validate_prompt_content(template, category)

    def check_template_syntax(self, template: str) -> Dict[str, Any]:
        """템플릿 문법을 검증합니다."""
        return self.validator.check_template_syntax(template)

    def analyze_template_quality(self, template: PromptTemplate) -> Dict[str, Any]:
        """템플릿의 품질을 분석합니다."""
        return self.validator.analyze_template_quality(template)

    def suggest_improvements(self, template: PromptTemplate) -> Dict[str, Any]:
        """템플릿 개선사항을 제안합니다."""
        return self.validator.suggest_improvements(template)

    # ===== 편의 메서드들 =====

    def create_and_validate_prompt(self,
                                  name: str,
                                  description: str,
                                  category: PromptCategory,
                                  template: str,
                                  created_by: str = "admin",
                                  tags: List[str] = None,
                                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """프롬프트를 생성하고 유효성을 검증합니다."""
        # 먼저 템플릿 검증
        validation_result = self.validate_prompt_template(template)

        if not validation_result['is_valid']:
            return {
                'success': False,
                'prompt': None,
                'validation': validation_result,
                'errors': validation_result['errors']
            }

        # 프롬프트 생성
        try:
            prompt = self.create_prompt(
                name=name, description=description, category=category,
                template=template, created_by=created_by,
                tags=tags, metadata=metadata
            )

            # 구조 검증
            structure_validation = self.validate_prompt_structure(prompt)

            return {
                'success': True,
                'prompt': prompt,
                'validation': validation_result,
                'structure_validation': structure_validation
            }

        except Exception as e:
            return {
                'success': False,
                'prompt': None,
                'validation': validation_result,
                'errors': [f"프롬프트 생성 실패: {e}"]
            }

    def render_and_validate(self, prompt_id: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """프롬프트를 렌더링하고 변수를 검증합니다."""
        template = self.get_prompt(prompt_id)
        if not template:
            return {
                'success': False,
                'error': '프롬프트를 찾을 수 없습니다.',
                'rendered_text': None
            }

        # 변수 검증
        variable_validation = self.validate_variables(template.template, variables)

        # 렌더링
        rendered = self.render_prompt(prompt_id, variables)

        return {
            'success': rendered is not None,
            'rendered_text': rendered,
            'variable_validation': variable_validation,
            'template_info': {
                'id': template.id,
                'name': template.name,
                'category': template.category.value
            }
        }


__all__ = [
    'PromptService',
    'NotificationConfig',
    'NotificationEvent',
    'NotificationPriority',
    'create_daily_summary_email',
    'create_notification_event',
    'determine_notification_priority',
    'get_notification_history',
    'get_notification_history_path',
    'get_notification_settings_path',
    'get_notification_storage_path',
    'group_results_by_district',
    'load_notification_config',
    'load_notification_settings',
    'process_monitoring_results',
    'save_notification_event',
    'save_notification_settings',
    'send_batch_summary_email',
    'send_daily_summary_email',
    'send_email_notification',
    'send_test_email',
    'should_send_batch_email',
]