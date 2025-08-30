"""
애플리케이션의 설정을 정의하는 모듈입니다.

Config 데이터 클래스를 통해 타입 안전하고 확장 가능한 설정을 제공합니다.
Vision 관련 기본값은 src.services.vision_types.VisionConfig를 사용하여 관리합니다.
"""
from dataclasses import dataclass, field
from typing import List
import os

from src.services.vision_types import VisionConfig


@dataclass
class DistrictConfig:
    """
    행정구역 데이터 처리 관련 설정을 포함하는 데이터 클래스입니다.
    """
    # 파일 경로 설정
    uploads_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "uploads\districts"))
    
    # data.go.kr API URL 설정
    meta_url: str = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?publicDataDetailPk=uddi%3A5176efd5-da6e-42a0-b2cf-8512f74503ea&publicDataPk=15063424&atchFileId=&fileDetailSn=1"
    download_url: str = "https://www.data.go.kr/cmm/cmm/fileDownload.do"
    
    # 파일명 설정
    file_prefix: str = "districts"
    file_extension: str = "json"
    
    # CSV 처리 설정
    expected_columns: List[str] = field(default_factory=lambda: [
        '법정동코드', '시도명', '시군구명', '읍면동명', '리명', '순위', '생성일자', '삭제일자'
    ])
    required_columns: List[str] = field(default_factory=lambda: [
        '법정동코드', '시도명', '시군구명'
    ])
    
    # 네트워크 설정
    request_timeout: int = 30
    download_timeout: int = 120
    
    # User-Agent 설정
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


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
    
    # District-specific configuration
    district: DistrictConfig = field(default_factory=DistrictConfig)


def load_config() -> Config:
    """
    애플리케이션 설정을 로드하고 Config 인스턴스를 반환합니다.
    향후 환경 변수나 다른 설정 파일에서 값을 오버라이드할 수 있도록 확장될 수 있습니다.
    """
    return Config()
