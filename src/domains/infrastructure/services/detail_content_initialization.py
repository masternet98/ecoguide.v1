"""
세부내역 콘텐츠 서비스 초기화 모듈입니다.

애플리케이션 시작 시 세부내역 프롬프트를 프롬프트 시스템에 등록합니다.
"""
from typing import Dict, Optional
from src.app.core.logger import get_logger

logger = get_logger(__name__)


def initialize_detail_content_service(app_context=None) -> Dict[str, Optional[str]]:
    """
    세부내역 서비스 초기화 및 프롬프트 등록

    이 함수는 애플리케이션 시작 시 호출되어야 합니다.
    프롬프트 서비스가 활성화되어 있는 경우 세부내역 프롬프트를 등록합니다.

    Args:
        app_context: ApplicationFactory에서 생성된 앱 컨텍스트 (선택사항)

    Returns:
        등록된 프롬프트 ID 딕셔너리 또는 빈 딕셔너리
    """
    try:
        # PromptService 가져오기
        try:
            if app_context:
                prompt_service = app_context.get_service('prompt_service')
            else:
                from src.app.core.app_factory import ApplicationFactory
                app_context = ApplicationFactory.create_application()
                prompt_service = app_context.get_service('prompt_service')

            if not prompt_service:
                logger.warning("PromptService를 사용할 수 없습니다. 프롬프트 등록을 건너뜁니다.")
                return {}

            # 프롬프트 등록
            from src.domains.infrastructure.services.detail_content_prompts import (
                register_detail_content_prompts
            )

            prompt_ids = register_detail_content_prompts(prompt_service)

            if prompt_ids:
                logger.info(f"세부내역 프롬프트 등록 완료: {prompt_ids}")
                return prompt_ids
            else:
                logger.warning("세부내역 프롬프트 등록이 반환값을 생성하지 못했습니다.")
                return {}

        except ImportError:
            logger.warning("PromptService를 임포트할 수 없습니다. 프롬프트 등록을 건너뜁니다.")
            return {}

    except Exception as e:
        logger.error(f"세부내역 서비스 초기화 실패: {e}")
        return {}


def is_detail_content_feature_enabled(app_context=None) -> bool:
    """
    세부내역 콘텐츠 기능이 활성화되어 있는지 확인

    Args:
        app_context: ApplicationFactory에서 생성된 앱 컨텍스트 (선택사항)

    Returns:
        기능 활성화 여부
    """
    try:
        if not app_context:
            from src.app.core.app_factory import ApplicationFactory
            app_context = ApplicationFactory.create_application()

        # 두 기능 모두 활성화되어 있는지 확인
        info_enabled = app_context.is_feature_enabled('detail_content_disposal_info')
        fee_enabled = app_context.is_feature_enabled('detail_content_fee_info')

        return info_enabled and fee_enabled

    except Exception as e:
        logger.error(f"기능 활성화 여부 확인 실패: {e}")
        return False
