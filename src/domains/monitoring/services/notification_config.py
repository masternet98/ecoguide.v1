"""알림 서비스 설정 및 저장소 유틸리티 모듈입니다."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.config import Config
from src.core.logger import LogCategory, log_error
from src.services.monitoring_service import get_monitoring_storage_path

class NotificationPriority(Enum):
    """알림 우선순위"""
    CRITICAL = "critical"  # 즉시 알림 (URL 접근 불가, 서비스 중단)
    HIGH = "high"         # 일일 요약 (페이지 구조 변경, 핵심 내용 변경)
    MEDIUM = "medium"     # 주간 요약 (텍스트 변경, 파일 업데이트)
    LOW = "low"

@dataclass
class NotificationConfig:
    """알림 설정"""
    email_enabled: bool = False
    email_host: str = "smtp.gmail.com"
    email_port: int = 587
    email_user: str = ""
    email_password: str = ""
    email_recipients: List[str] = None
    
    # 알림 주기 설정
    critical_immediate: bool = True
    high_daily_summary: bool = True
    medium_weekly_summary: bool = True
    low_monthly_summary: bool = True
    
    # 필터링 설정
    min_priority: NotificationPriority = NotificationPriority.MEDIUM
    ignore_temporary_errors: bool = True
    max_notifications_per_day: int = 10
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []

@dataclass
class NotificationEvent:
    """알림 이벤트"""
    id: str
    priority: NotificationPriority
    title: str
    message: str
    district_key: str
    url_type: str
    created_at: str
    sent_at: Optional[str] = None
    channels: List[str] = None  # email, log, dashboard
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = []
        if self.metadata is None:
            self.metadata = {}

def get_notification_storage_path(config: Optional[Config] = None) -> str:
    """알림 데이터 저장 경로를 반환합니다."""
    monitoring_dir = get_monitoring_storage_path(config)
    notifications_dir = os.path.join(monitoring_dir, 'notifications')
    os.makedirs(notifications_dir, exist_ok=True)
    return notifications_dir

def get_notification_settings_path(config: Optional[Config] = None) -> str:
    """알림 설정 파일 경로를 반환합니다."""
    storage_dir = get_notification_storage_path(config)
    return os.path.join(storage_dir, "notification_settings.json")

def get_notification_history_path(config: Optional[Config] = None) -> str:
    """알림 이력 파일 경로를 반환합니다."""
    storage_dir = get_notification_storage_path(config)
    return os.path.join(storage_dir, "notification_history.json")

def load_notification_settings(config: Optional[Config] = None) -> Dict[str, Any]:
    """
    알림 설정 파일을 로드합니다.
    수신자 목록과 알림 설정을 JSON 파일에서 가져옵니다.
    """
    settings_path = get_notification_settings_path(config)
    
    default_settings = {
        "email_recipients": [],
        "notification_preferences": {
            "critical_immediate": True,
            "high_daily_summary": True,
            "medium_weekly_summary": True,
            "low_monthly_summary": True
        },
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }
    
    if not os.path.exists(settings_path):
        return default_settings
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        # 기본 설정과 병합
        for key in default_settings:
            if key not in settings:
                settings[key] = default_settings[key]
        return settings
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "notification_service", "load_notification_settings",
            "알림 설정 로드 실패", f"Error: {str(e)}", error=e
        )
        return default_settings

def save_notification_settings(settings: Dict[str, Any], config: Optional[Config] = None) -> bool:
    """
    알림 설정을 파일에 저장합니다.
    """
    settings_path = get_notification_settings_path(config)
    
    try:
        settings["last_updated"] = datetime.now().isoformat()
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
        
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "notification_service", "save_notification_settings",
            "알림 설정 저장 실패", f"Error: {str(e)}", error=e
        )
        return False

def load_notification_config(config: Optional[Config] = None) -> NotificationConfig:
    """
    알림 설정을 로드합니다.
    환경변수에서 발송자 정보, 설정 파일에서 수신자 정보를 가져옵니다.
    """
    notification_config = NotificationConfig()
    
    # 환경변수에서 발송자 이메일 설정 로드 (관리자 계정)
    notification_config.email_user = os.getenv('NOTIFICATION_EMAIL_USER', '')
    notification_config.email_password = os.getenv('NOTIFICATION_EMAIL_PASSWORD', '')
    notification_config.email_enabled = bool(notification_config.email_user and notification_config.email_password)
    
    # 설정 파일에서 수신자 정보 로드
    settings = load_notification_settings(config)
    notification_config.email_recipients = settings.get("email_recipients", [])
    
    # 알림 선호도 설정 적용
    prefs = settings.get("notification_preferences", {})
    notification_config.critical_immediate = prefs.get("critical_immediate", True)
    notification_config.high_daily_summary = prefs.get("high_daily_summary", True)
    notification_config.medium_weekly_summary = prefs.get("medium_weekly_summary", True)
    notification_config.low_monthly_summary = prefs.get("low_monthly_summary", True)
    
    return notification_config

def save_notification_event(event: NotificationEvent, config: Optional[Config] = None) -> bool:
    """
    알림 이벤트를 파일에 저장합니다.
    
    Args:
        event: 알림 이벤트
        config: 앱 설정
        
    Returns:
        저장 성공 여부
    """
    try:
        history_path = get_notification_history_path(config)
        
        # 기존 히스토리 로드
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = {"events": [], "metadata": {"created_at": datetime.now().isoformat()}}
        
        # 새 이벤트 추가
        event_data = {
            "id": event.id,
            "priority": event.priority.value,
            "title": event.title,
            "message": event.message,
            "district_key": event.district_key,
            "url_type": event.url_type,
            "created_at": event.created_at,
            "sent_at": event.sent_at,
            "channels": event.channels,
            "metadata": event.metadata
        }
        
        history["events"].append(event_data)
        
        # 최근 1000개 이벤트만 유지
        history["events"] = history["events"][-1000:]
        history["metadata"]["last_updated"] = datetime.now().isoformat()
        
        # 파일에 저장
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "notification_service", "save_notification_event",
            "알림 이벤트 저장 실패", f"Event: {event.id}, Error: {str(e)}", error=e
        )
        return False

def get_notification_history(config: Optional[Config] = None, days: int = 30) -> Dict[str, Any]:
    """
    최근 알림 이력을 조회합니다.
    
    Args:
        config: 앱 설정
        days: 조회할 최근 일수
        
    Returns:
        알림 이력 데이터
    """
    try:
        history_path = get_notification_history_path(config)
        
        if not os.path.exists(history_path):
            return {"events": [], "summary": {"total": 0}}
        
        with open(history_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # 최근 N일간 이벤트 필터링
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_events = []
        
        for event in history.get("events", []):
            event_date = datetime.fromisoformat(event["created_at"])
            if event_date >= cutoff_date:
                recent_events.append(event)
        
        # 우선순위별 통계
        priority_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for event in recent_events:
            priority = event.get("priority", "low")
            if priority in priority_counts:
                priority_counts[priority] += 1
        
        return {
            "events": recent_events[-50:],  # 최근 50개만
            "summary": {
                "total": len(recent_events),
                "by_priority": priority_counts,
                "date_range": {
                    "from": cutoff_date.isoformat(),
                    "to": datetime.now().isoformat()
                }
            }
        }
        
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "notification_service", "get_notification_history",
            "알림 이력 조회 실패", f"Error: {str(e)}", error=e
        )
        return {"events": [], "summary": {"total": 0}}

__all__ = [
    'NotificationPriority',
    'NotificationConfig',
    'NotificationEvent',
    'get_notification_storage_path',
    'get_notification_settings_path',
    'get_notification_history_path',
    'load_notification_settings',
    'save_notification_settings',
    'load_notification_config',
    'save_notification_event',
    'get_notification_history',
]
