"""
프롬프트 도메인 타입 정의
"""
from typing import TypedDict, Optional, List, Dict, Any


class PromptTemplate(TypedDict):
    """프롬프트 템플릿"""
    id: str
    name: str
    template: str
    category: str
    required_services: List[str]