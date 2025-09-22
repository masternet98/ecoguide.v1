"""
인프라 도메인 타입 정의
"""
from typing import TypedDict, Optional, List, Dict, Any


class SearchResult(TypedDict):
    """검색 결과"""
    title: str
    url: str
    snippet: str
    source: str


class TunnelStatus(TypedDict):
    """터널 상태"""
    active: bool
    url: Optional[str]
    process_id: Optional[int]