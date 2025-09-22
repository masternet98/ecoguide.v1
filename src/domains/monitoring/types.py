"""
모니터링 도메인 타입 정의
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class MonitoringMetric(TypedDict):
    """모니터링 메트릭"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]