"""
모니터링 결과에 대한 알림 발송을 관리하는 서비스 모듈입니다.
이메일, 로그, 대시보드 알림 등 다양한 채널을 통해 관리자에게 변경사항을 알립니다.
"""
import json
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.core.config import Config
from src.core.logger import log_error, log_info, LogCategory
from src.services.monitoring_service import MonitoringResult, get_monitoring_storage_path

class NotificationPriority(Enum):
    """알림 우선순위"""
    CRITICAL = "critical"  # 즉시 알림 (URL 접근 불가, 서비스 중단)
    HIGH = "high"         # 일일 요약 (페이지 구조 변경, 핵심 내용 변경)
    MEDIUM = "medium"     # 주간 요약 (텍스트 변경, 파일 업데이트)
    LOW = "low"          # 월간 요약 (경미한 변경, 통계 정보)

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

def determine_notification_priority(result: MonitoringResult) -> NotificationPriority:
    """
    모니터링 결과를 바탕으로 알림 우선순위를 결정합니다.
    
    Args:
        result: 모니터링 결과
        
    Returns:
        알림 우선순위
    """
    if result.status == 'unreachable':
        return NotificationPriority.CRITICAL
    elif result.status == 'error':
        # 파일 에러는 중간 우선순위
        if result.url_type.endswith('_file') or 'file' in result.error_message.lower():
            return NotificationPriority.MEDIUM
        else:
            return NotificationPriority.HIGH
    elif result.status == 'changed':
        if result.change_type == 'structure':
            return NotificationPriority.HIGH
        elif result.change_type == 'file':
            return NotificationPriority.MEDIUM
        else:  # content change
            return NotificationPriority.MEDIUM
    
    return NotificationPriority.LOW

def create_notification_event(result: MonitoringResult, config: Optional[Config] = None) -> NotificationEvent:
    """
    모니터링 결과로부터 알림 이벤트를 생성합니다.
    
    Args:
        result: 모니터링 결과
        config: 앱 설정
        
    Returns:
        알림 이벤트
    """
    priority = determine_notification_priority(result)
    
    # 제목과 메시지 생성
    district_name = result.district_key.replace('_', ' ')
    url_type_names = {
        'info_url': '배출정보',
        'system_url': '시스템',
        'fee_url': '수수료',
        'appliance_url': '폐가전제품'
    }
    url_type_name = url_type_names.get(result.url_type, result.url_type)
    
    if result.status == 'unreachable':
        title = f"[CRITICAL] {district_name} {url_type_name} 접근 불가"
        message = f"지역: {district_name}\n항목: {url_type_name}\n상태: 접근 불가\n오류: {result.error_message}"
    elif result.status == 'error':
        title = f"[ERROR] {district_name} {url_type_name} 오류 발생"
        message = f"지역: {district_name}\n항목: {url_type_name}\n상태: 오류\n오류: {result.error_message}"
    elif result.status == 'changed':
        title = f"[CHANGED] {district_name} {url_type_name} 변경 감지"
        change_type_names = {
            'content': '내용 변경',
            'structure': '구조 변경',
            'file': '파일 변경'
        }
        change_type_name = change_type_names.get(result.change_type, result.change_type)
        message = f"지역: {district_name}\n항목: {url_type_name}\n변경 유형: {change_type_name}"
    else:
        return None  # 정상 상태는 알림 생성하지 않음
    
    event_id = f"{result.district_key}_{result.url_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return NotificationEvent(
        id=event_id,
        priority=priority,
        title=title,
        message=message,
        district_key=result.district_key,
        url_type=result.url_type,
        created_at=result.checked_at or datetime.now().isoformat(),
        metadata={
            'monitoring_result': {
                'status': result.status,
                'change_type': result.change_type,
                'error_message': result.error_message,
                'response_time': result.response_time,
                'previous_hash': result.previous_hash,
                'current_hash': result.current_hash
            }
        }
    )

def send_email_notification(event: NotificationEvent, notification_config: NotificationConfig) -> bool:
    """
    이메일 알림을 발송합니다.
    
    Args:
        event: 알림 이벤트
        notification_config: 알림 설정
        
    Returns:
        발송 성공 여부
    """
    if not notification_config.email_enabled or not notification_config.email_recipients:
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = notification_config.email_user
        msg['To'] = ', '.join(notification_config.email_recipients)
        msg['Subject'] = f"[EcoGuide 모니터링] {event.title}"
        
        # 메시지 본문 작성
        body = f"""
EcoGuide 시스템에서 변경사항이 감지되었습니다.

{event.message}

확인 시간: {event.created_at}

자세한 내용은 관리자 대시보드에서 확인하실 수 있습니다.

---
EcoGuide 자동 모니터링 시스템
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # SMTP 서버 연결 및 발송
        server = smtplib.SMTP(notification_config.email_host, notification_config.email_port)
        server.starttls()
        server.login(notification_config.email_user, notification_config.email_password)
        server.send_message(msg)
        server.quit()
        
        log_info(
            LogCategory.SYSTEM, "notification_service", "send_email_notification",
            "이메일 알림 발송 성공", f"Event: {event.id}, Recipients: {len(notification_config.email_recipients)}"
        )
        
        return True
        
    except Exception as e:
        log_error(
            LogCategory.SYSTEM, "notification_service", "send_email_notification",
            "이메일 알림 발송 실패", f"Event: {event.id}, Error: {str(e)}", error=e
        )
        return False

def log_notification(event: NotificationEvent) -> bool:
    """
    알림 이벤트를 로그에 기록합니다.
    
    Args:
        event: 알림 이벤트
        
    Returns:
        로깅 성공 여부
    """
    try:
        priority_symbols = {
            NotificationPriority.CRITICAL: "🚨",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.MEDIUM: "📝",
            NotificationPriority.LOW: "ℹ️"
        }
        
        symbol = priority_symbols.get(event.priority, "📋")
        
        log_info(
            LogCategory.SYSTEM, "notification_service", "monitoring_alert",
            f"{symbol} {event.title}", event.message
        )
        
        return True
        
    except Exception as e:
        log_error(
            LogCategory.SYSTEM, "notification_service", "log_notification",
            "알림 로깅 실패", f"Event: {event.id}, Error: {str(e)}", error=e
        )
        return False

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

def group_results_by_district(results: List[MonitoringResult]) -> Dict[str, List[MonitoringResult]]:
    """
    모니터링 결과를 지역별로 그룹화합니다.
    
    Args:
        results: 모니터링 결과 목록
        
    Returns:
        지역별로 그룹화된 결과
    """
    district_groups = {}
    for result in results:
        if result.district_key not in district_groups:
            district_groups[result.district_key] = []
        district_groups[result.district_key].append(result)
    return district_groups

def create_batch_notification_summary(district_groups: Dict[str, List[MonitoringResult]], 
                                     config: Optional[Config] = None) -> Dict[str, Any]:
    """
    배치 알림을 위한 요약 데이터를 생성합니다.
    
    Args:
        district_groups: 지역별 결과 그룹
        config: 앱 설정
        
    Returns:
        배치 요약 데이터
    """
    summary = {
        "total_districts": len(district_groups),
        "total_issues": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "error_count": 0,
        "change_count": 0,
        "districts_with_issues": [],
        "created_at": datetime.now().isoformat()
    }
    
    for district_key, results in district_groups.items():
        district_issues = []
        has_issues = False
        
        for result in results:
            if result.status == 'ok':
                continue
                
            has_issues = True
            summary["total_issues"] += 1
            
            # 우선순위별 카운트
            priority = determine_notification_priority(result)
            if priority == NotificationPriority.CRITICAL:
                summary["critical_count"] += 1
            elif priority == NotificationPriority.HIGH:
                summary["high_count"] += 1
            elif priority == NotificationPriority.MEDIUM:
                summary["medium_count"] += 1
            
            # 상태별 카운트
            if result.status in ['error', 'unreachable']:
                summary["error_count"] += 1
            elif result.status == 'changed':
                summary["change_count"] += 1
            
            # 이슈 상세 정보
            district_issues.append({
                "url_type": result.url_type,
                "status": result.status,
                "error_message": result.error_message,
                "change_type": result.change_type
            })
        
        if has_issues:
            summary["districts_with_issues"].append({
                "district_key": district_key,
                "issues": district_issues
            })
    
    return summary

def should_send_batch_email(batch_summary: Dict[str, Any], 
                           notification_config: NotificationConfig) -> bool:
    """
    배치 이메일 발송 여부를 결정합니다.
    
    Args:
        batch_summary: 배치 요약 데이터
        notification_config: 알림 설정
        
    Returns:
        발송 여부
    """
    if not notification_config.email_enabled:
        return False
    
    # 중요 이슈가 있으면 즉시 발송
    if batch_summary["critical_count"] > 0 and notification_config.critical_immediate:
        return True
    
    # 높은 우선순위 이슈가 있으면 발송
    if batch_summary["high_count"] > 0 and notification_config.high_daily_summary:
        return True
    
    # 전체 이슈 수가 임계값을 넘으면 발송 (5개 이상)
    if batch_summary["total_issues"] >= 5:
        return True
    
    return False

def send_batch_summary_email(batch_summary: Dict[str, Any], 
                            notification_config: NotificationConfig,
                            config: Optional[Config] = None) -> bool:
    """
    배치 요약 이메일을 발송합니다.
    
    Args:
        batch_summary: 배치 요약 데이터
        notification_config: 알림 설정
        config: 앱 설정
        
    Returns:
        발송 성공 여부
    """
    try:
        # 이메일 내용 생성
        subject = f"[EcoGuide] 모니터링 요약 - {batch_summary['total_issues']}개 이슈 발견"
        
        # 우선순위별 요약
        priority_summary = []
        if batch_summary["critical_count"] > 0:
            priority_summary.append(f"🚨 긴급: {batch_summary['critical_count']}개")
        if batch_summary["high_count"] > 0:
            priority_summary.append(f"⚠️ 높음: {batch_summary['high_count']}개")
        if batch_summary["medium_count"] > 0:
            priority_summary.append(f"📋 보통: {batch_summary['medium_count']}개")
        
        # 이메일 본문 구성
        body = f"""
EcoGuide 모니터링 시스템에서 다음과 같은 이슈들이 발견되었습니다.

📊 전체 요약:
- 검사 대상 지역: {batch_summary['total_districts']}개
- 발견된 이슈: {batch_summary['total_issues']}개
- 우선순위: {', '.join(priority_summary) if priority_summary else '없음'}
- 오류: {batch_summary['error_count']}개, 변경: {batch_summary['change_count']}개

🏢 이슈가 발견된 지역들:
"""
        
        for district_info in batch_summary["districts_with_issues"]:
            district_key = district_info["district_key"]
            issues = district_info["issues"]
            
            body += f"\n▶ {district_key} ({len(issues)}개 이슈)\n"
            for issue in issues:
                status_emoji = "🚫" if issue["status"] == "error" else "🔄" if issue["status"] == "changed" else "❓"
                body += f"  {status_emoji} {issue['url_type']}: {issue['status']}"
                if issue["error_message"]:
                    body += f" - {issue['error_message']}"
                body += "\n"
        
        body += f"\n\n검사 시간: {batch_summary['created_at']}\n"
        body += "\n자세한 내용은 EcoGuide 관리 시스템에서 확인하시기 바랍니다."
        
        # 이메일 발송
        msg = MIMEMultipart()
        msg['From'] = notification_config.email_user
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(notification_config.email_user, notification_config.email_password)
        
        for recipient in notification_config.email_recipients:
            msg['To'] = recipient
            server.send_message(msg)
            del msg['To']
        
        server.quit()
        
        log_info(
            LogCategory.SYSTEM, "notification_service", "send_batch_summary_email",
            "배치 요약 이메일 발송 성공", 
            f"Recipients: {len(notification_config.email_recipients)}, Issues: {batch_summary['total_issues']}"
        )
        
        return True
        
    except Exception as e:
        log_error(
            LogCategory.SYSTEM, "notification_service", "send_batch_summary_email",
            "배치 요약 이메일 발송 실패", f"Error: {str(e)}", error=e
        )
        return False

def process_monitoring_results(results: List[MonitoringResult], 
                              config: Optional[Config] = None,
                              notification_config: Optional[NotificationConfig] = None) -> Dict[str, Any]:
    """
    모니터링 결과들을 처리하여 적절한 알림을 발송합니다.
    
    Args:
        results: 모니터링 결과 목록
        config: 앱 설정
        notification_config: 알림 설정
        
    Returns:
        알림 처리 결과 요약
    """
    if notification_config is None:
        notification_config = load_notification_config(config)
    
    summary = {
        "total_events": 0,
        "sent_emails": 0,
        "logged_events": 0,
        "saved_events": 0,
        "errors": 0,
        "events_by_priority": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
    }
    
    # 결과를 지역별로 그룹화하여 배치 처리
    district_groups = group_results_by_district(results)
    batch_summary = create_batch_notification_summary(district_groups, config)
    
    # 개별 이벤트는 로그만 기록 (스팸 이메일 방지)
    for result in results:
        # 정상 상태는 알림 생성하지 않음
        if result.status == 'ok':
            continue
        
        # 알림 이벤트 생성
        event = create_notification_event(result, config)
        if not event:
            continue
        
        summary["total_events"] += 1
        summary["events_by_priority"][event.priority.value] += 1
        
        # 우선순위 필터링
        if event.priority.value == NotificationPriority.LOW.value and notification_config.min_priority != NotificationPriority.LOW:
            continue
        
        # 로그 알림만 실행 (개별 이메일 발송 안 함)
        if log_notification(event):
            summary["logged_events"] += 1
        
        # 이벤트 저장
        if save_notification_event(event, config):
            summary["saved_events"] += 1
        else:
            summary["errors"] += 1
    
    # 배치 요약 이메일 발송 (프로세스 완료 후 1개 이메일만)
    if should_send_batch_email(batch_summary, notification_config):
        if send_batch_summary_email(batch_summary, notification_config, config):
            summary["sent_emails"] = 1
            log_info(
                LogCategory.SYSTEM, "notification_service", "process_monitoring_results",
                "배치 요약 이메일 발송 완료", f"Districts: {len(district_groups)}, Issues: {batch_summary.get('total_issues', 0)}"
            )
    
    log_info(
        LogCategory.SYSTEM, "notification_service", "process_monitoring_results",
        "알림 처리 완료", 
        f"Events: {summary['total_events']}, Emails: {summary['sent_emails']}, Errors: {summary['errors']}"
    )
    
    return summary

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

def create_daily_summary_email(config: Optional[Config] = None) -> Optional[str]:
    """
    일일 요약 이메일 내용을 생성합니다.
    
    Args:
        config: 앱 설정
        
    Returns:
        이메일 내용 또는 None (전송할 내용이 없는 경우)
    """
    from src.services.monitoring_service import get_monitoring_summary
    
    try:
        # 최근 1일간 모니터링 요약
        monitoring_summary = get_monitoring_summary(config, days=1)
        notification_history = get_notification_history(config, days=1)
        
        if (monitoring_summary["recent_changes"] == [] and 
            monitoring_summary["error_districts"] == [] and 
            notification_history["summary"]["total"] == 0):
            return None  # 전송할 내용이 없음
        
        # 이메일 본문 생성
        email_content = f"""
EcoGuide 시스템 일일 모니터링 보고서
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== 전체 현황 ===
• 총 관리 지역: {monitoring_summary["overview"]["total_districts"]}개
• 정상 지역: {monitoring_summary["overview"].get("healthy_districts", 0)}개
• 문제 지역: {len(monitoring_summary["error_districts"])}개
• 마지막 검사: {monitoring_summary["overview"]["last_check"]}

=== 최근 24시간 변경사항 ===
"""
        
        if monitoring_summary["recent_changes"]:
            for change in monitoring_summary["recent_changes"][:10]:
                district_name = change["district"].replace('_', ' ')
                url_type_names = {
                    'info_url': '배출정보',
                    'system_url': '시스템',
                    'fee_url': '수수료',
                    'appliance_url': '폐가전제품'
                }
                url_type_name = url_type_names.get(change["url_type"], change["url_type"])
                
                email_content += f"• {district_name} - {url_type_name}: {change['change_type']} ({change['changed_at'][:16]})\n"
        else:
            email_content += "변경사항 없음\n"
        
        email_content += "\n=== 오류 및 주의사항 ===\n"
        
        if monitoring_summary["error_districts"]:
            for error in monitoring_summary["error_districts"]:
                district_name = error["district"].replace('_', ' ')
                email_content += f"• {district_name} - {error['url_type']}: {error['status']} ({error['error']})\n"
        else:
            email_content += "오류 없음\n"
        
        email_content += f"""

=== 알림 통계 ===
• 총 알림 수: {notification_history["summary"]["total"]}개
• 긴급: {notification_history["summary"]["by_priority"].get("critical", 0)}개
• 높음: {notification_history["summary"]["by_priority"].get("high", 0)}개
• 보통: {notification_history["summary"]["by_priority"].get("medium", 0)}개
• 낮음: {notification_history["summary"]["by_priority"].get("low", 0)}개

자세한 내용은 EcoGuide 관리자 대시보드에서 확인하실 수 있습니다.

---
EcoGuide 자동 모니터링 시스템
"""
        
        return email_content
        
    except Exception as e:
        log_error(
            LogCategory.SYSTEM, "notification_service", "create_daily_summary_email",
            "일일 요약 이메일 생성 실패", f"Error: {str(e)}", error=e
        )
        return None

def send_daily_summary_email(config: Optional[Config] = None, 
                            notification_config: Optional[NotificationConfig] = None) -> bool:
    """
    일일 요약 이메일을 발송합니다.
    
    Args:
        config: 앱 설정
        notification_config: 알림 설정
        
    Returns:
        발송 성공 여부
    """
    if notification_config is None:
        notification_config = load_notification_config(config)
    
    if not notification_config.email_enabled or not notification_config.high_daily_summary:
        return False
    
    email_content = create_daily_summary_email(config)
    if not email_content:
        log_info(
            LogCategory.SYSTEM, "notification_service", "send_daily_summary_email",
            "일일 요약 이메일", "전송할 내용이 없어 건너뜀"
        )
        return True  # 전송할 내용이 없는 것도 성공으로 처리
    
    try:
        msg = MIMEMultipart()
        msg['From'] = notification_config.email_user
        msg['To'] = ', '.join(notification_config.email_recipients)
        msg['Subject'] = f"[EcoGuide] 일일 모니터링 보고서 ({datetime.now().strftime('%Y-%m-%d')})"
        
        msg.attach(MIMEText(email_content, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(notification_config.email_host, notification_config.email_port)
        server.starttls()
        server.login(notification_config.email_user, notification_config.email_password)
        server.send_message(msg)
        server.quit()
        
        log_info(
            LogCategory.SYSTEM, "notification_service", "send_daily_summary_email",
            "일일 요약 이메일 발송 성공", f"Recipients: {len(notification_config.email_recipients)}"
        )
        
        return True
        
    except Exception as e:
        log_error(
            LogCategory.SYSTEM, "notification_service", "send_daily_summary_email",
            "일일 요약 이메일 발송 실패", f"Error: {str(e)}", error=e
        )
        return False

def send_test_email(test_recipient: str, config: Optional[Config] = None, 
                   notification_config: Optional[NotificationConfig] = None) -> Dict[str, Any]:
    """
    연결 테스트를 위한 간단한 이메일을 발송합니다.
    
    Args:
        test_recipient: 테스트 이메일 수신자
        config: 앱 설정
        notification_config: 알림 설정
    
    Returns:
        발송 결과 정보
    """
    if notification_config is None:
        notification_config = load_notification_config(config)
    
    if not notification_config.email_enabled:
        return {
            "success": False,
            "error": "이메일 설정이 비활성화되어 있습니다. SMTP 설정을 확인하세요."
        }
    
    if not test_recipient or '@' not in test_recipient:
        return {
            "success": False,
            "error": "올바른 이메일 주소를 입력하세요."
        }
    
    try:
        msg = MIMEMultipart()
        msg['From'] = notification_config.email_user
        msg['To'] = test_recipient
        msg['Subject'] = "[EcoGuide] 알림 시스템 테스트"
        
        # 테스트 메시지 작성
        body = f"""
EcoGuide 알림 시스템 연결 테스트입니다.

✨ 연결 상태: 정상 연결됨
📧 발송자: {notification_config.email_user}
📅 발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

이 테스트 이메일을 정상적으로 받으셨다면, EcoGuide 알림 시스템이 올바르게 설정되었습니다.

---
EcoGuide 자동 모니터링 시스템
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # SMTP 서버 연결 및 발송
        server = smtplib.SMTP(notification_config.email_host, notification_config.email_port)
        server.starttls()
        server.login(notification_config.email_user, notification_config.email_password)
        server.send_message(msg)
        server.quit()
        
        log_info(
            LogCategory.SYSTEM, "notification_service", "send_test_email",
            "테스트 이메일 발송 성공", f"Recipient: {test_recipient}"
        )
        
        return {
            "success": True,
            "message": f"{test_recipient}로 테스트 이메일을 성공적으로 발송했습니다.",
            "sent_at": datetime.now().isoformat(),
            "sender": notification_config.email_user
        }
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = "이메일 인증에 실패했습니다. Gmail 앱 비밀번호를 확인하세요."
        log_error(
            LogCategory.SYSTEM, "notification_service", "send_test_email",
            "테스트 이메일 인증 실패", f"Recipient: {test_recipient}, Error: {str(e)}", error=e
        )
        return {"success": False, "error": error_msg, "technical_error": str(e)}
        
    except smtplib.SMTPConnectError as e:
        error_msg = "SMTP 서버 연결에 실패했습니다. 인터넷 연결을 확인하세요."
        log_error(
            LogCategory.SYSTEM, "notification_service", "send_test_email",
            "테스트 이메일 연결 실패", f"Recipient: {test_recipient}, Error: {str(e)}", error=e
        )
        return {"success": False, "error": error_msg, "technical_error": str(e)}
        
    except Exception as e:
        error_msg = f"알 수 없는 오류가 발생했습니다: {str(e)}"
        log_error(
            LogCategory.SYSTEM, "notification_service", "send_test_email",
            "테스트 이메일 발송 실패", f"Recipient: {test_recipient}, Error: {str(e)}", error=e
        )
        return {"success": False, "error": error_msg, "technical_error": str(e)}