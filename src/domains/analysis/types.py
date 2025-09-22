"""
이미지 분석 도메인 타입 정의
"""
from typing import TypedDict, Optional, List, Dict, Any


class AnalysisResult(TypedDict):
    """이미지 분석 결과"""
    confidence: float
    objects: List[str]
    description: str
    metadata: Optional[Dict[str, Any]]