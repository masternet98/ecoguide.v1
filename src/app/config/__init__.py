"""
App Configuration Module

Phase 3에서 재구성된 설정 모듈
기존 src/core/config.py의 내용을 포함하며 호환성 유지
"""

# 새 경로에서 설정 클래스들을 re-export
from .main import (
    Config,
    DistrictConfig,
    SearchProviderConfig,
    PromptConfig,
    VisionConfig,
    LocationConfig,
    load_config
)

# 하위 호환성을 위한 alias
get_config = load_config  # 하위 호환성

__all__ = [
    'Config',
    'DistrictConfig',
    'SearchProviderConfig',
    'PromptConfig',
    'VisionConfig',
    'LocationConfig',
    'load_config',
    'get_config'
]