"""
행정구역 도메인 타입 정의
"""
from typing import TypedDict, Optional, List, Dict, Any


class DistrictInfo(TypedDict):
    """행정구역 정보"""
    code: str
    sido: str
    sigungu: str
    dong: Optional[str]
    homepage: Optional[str]