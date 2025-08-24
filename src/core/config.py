"""
애플리케이션의 설정을 정의하는 모듈입니다.

Config 데이터 클래스를 통해 타입 안전하고 확장 가능한 설정을 제공합니다.
Vision 관련 기본값은 src.services.vision_types.VisionConfig를 사용하여 관리합니다.
"""
from dataclasses import dataclass, field
from typing import List

from src.services.vision_types import VisionConfig


@dataclass
class Config:
    """
    애플리케이션의 모든 설정을 포함하는 데이터 클래스입니다.
    """
    page_title: str = "카메라 - LLM 이미지 분석"
    page_icon: str = "📷"
    default_model: str = "gpt-4o-mini"
    vision_models: List[str] = field(default_factory=lambda: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"])
    default_prompt: str = (
        "이 이미지에 있는 제품을 대형폐기물로 배출하려고 한다. 이 때 제품의 크기가 가격에 중요한 영향을 미친다."
        "해당 제품이 어떤 품목인지. 사진으로 유추하였을 때 대략적인 크기에 대해 분석해줘."
    )
    default_port: int = 8501
    max_image_size: int = 1024
    jpeg_quality: int = 90

    # Vision-specific configuration (uses VisionConfig from src.services.vision_types)
    vision: VisionConfig = field(default_factory=VisionConfig)


def load_config() -> Config:
    """
    애플리케이션 설정을 로드하고 Config 인스턴스를 반환합니다.
    향후 환경 변수나 다른 설정 파일에서 값을 오버라이드할 수 있도록 확장될 수 있습니다.
    """
    return Config()
