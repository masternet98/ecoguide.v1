"""모니터링 결과에 대한 알림 발송을 관리하는 서비스 모듈입니다."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.app.core.config import Config
from src.app.core.logger import LogCategory, log_info
from src.domains.monitoring.services.monitoring_service import MonitoringResult
from src.domains.monitoring.services.notification_config import (
    NotificationConfig,
    NotificationEvent,
    NotificationPriority,
    get_notification_history,
    get_notification_history_path,
    get_notification_settings_path,
    get_notification_storage_path,
    load_notification_config,
    load_notification_settings,
    save_notification_event,
    save_notification_settings,
)
from src.domains.monitoring.services.notification_scheduler import (
    create_batch_notification_summary,
    create_notification_event,
    determine_notification_priority,
    group_results_by_district,
    log_notification,
    should_send_batch_email,
)
from src.domains.monitoring.services.notification_sender import (
    create_daily_summary_email,
    send_batch_summary_email,
    send_daily_summary_email,
    send_email_notification,
    send_test_email,
)

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

__all__ = [
    'NotificationConfig',
    'NotificationEvent',
    'NotificationPriority',
    'create_daily_summary_email',
    'create_notification_event',
    'determine_notification_priority',
    'get_notification_history',
    'get_notification_history_path',
    'get_notification_settings_path',
    'get_notification_storage_path',
    'group_results_by_district',
    'load_notification_config',
    'load_notification_settings',
    'process_monitoring_results',
    'save_notification_event',
    'save_notification_settings',
    'send_batch_summary_email',
    'send_daily_summary_email',
    'send_email_notification',
    'send_test_email',
    'should_send_batch_email',
]
