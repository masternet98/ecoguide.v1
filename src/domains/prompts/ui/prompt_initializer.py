"""
프롬프트 초기화 컴포넌트 - 기본 프롬프트들을 초기화합니다.
"""
from src.components.base import BaseComponent


class PromptInitializerComponent(BaseComponent):
    """프롬프트를 초기화하는 컴포넌트입니다."""
    
    def render(self, **kwargs) -> None:
        """
        이 컴포넌트는 직접 렌더링하지 않고 초기화 작업만 수행합니다.
        """
        pass
    
    def initialize_default_prompts(self, prompt_service) -> None:
        """
        기본 프롬프트들을 초기화합니다.
        
        Args:
            prompt_service: 프롬프트 서비스 인스턴스
        """
        try:
            from src.app.core.prompt_types import PromptCategory
            
            # 기본 카메라 분석 프롬프트 생성
            self._create_camera_analysis_prompt(prompt_service, PromptCategory)
            
            # 폐기물 분석 프롬프트 생성
            self._create_waste_classification_prompt(prompt_service, PromptCategory)
            
        except Exception as e:
            # 초기화 실패는 로그만 남기고 계속 진행
            pass
    
    def _create_camera_analysis_prompt(self, prompt_service, PromptCategory) -> None:
        """카메라 분석을 위한 기본 프롬프트를 생성합니다."""
        existing_prompts = prompt_service.get_prompts_for_feature("camera_analysis")
        if not existing_prompts:
            default_prompt = prompt_service.create_prompt(
                name="기본 이미지 분석",
                description="카메라로 촬영한 이미지의 객체를 식별하고 분류합니다.",
                category=PromptCategory.VISION_ANALYSIS,
                template=(
                    "이미지 중앙에 있는 물체가 무엇인지 식별하고, 해당 물체를 가장 적절한 카테고리로 분류해 주세요. "
                    "분류 결과는 JSON 형식으로 제공해 주세요. 예시: {\\\"object\\\": \\\"의자\\\", \\\"category\\\": \\\"가구\\\"}"
                ),
                tags=["기본", "객체인식", "분류"],
                created_by="system"
            )
            
            # 기능에 매핑
            prompt_service.map_feature_to_prompt(
                feature_id="camera_analysis",
                prompt_id=default_prompt.id,
                is_default=True,
                priority=0
            )
    
    def _create_waste_classification_prompt(self, prompt_service, PromptCategory) -> None:
        """폐기물 분류를 위한 기본 프롬프트를 생성합니다."""
        waste_prompts = prompt_service.list_prompts(category=PromptCategory.WASTE_CLASSIFICATION)
        if not waste_prompts:
            waste_prompt = prompt_service.create_prompt(
                name="대형폐기물 분석",
                description="대형폐기물 배출을 위한 제품 크기 및 분류 분석",
                category=PromptCategory.WASTE_CLASSIFICATION,
                template=(
                    "이 이미지에 있는 제품을 대형폐기물로 배출하려고 한다. 이 때 제품의 크기가 가격에 중요한 영향을 미친다. "
                    "해당 제품이 어떤 품목인지, 사진으로 유추하였을 때 대략적인 크기에 대해 분석해줘."
                ),
                tags=["폐기물", "크기분석", "분류"],
                created_by="system"
            )
            
            # 갤러리 기능에 매핑
            prompt_service.map_feature_to_prompt(
                feature_id="gallery_upload",
                prompt_id=waste_prompt.id,
                is_default=True,
                priority=0
            )