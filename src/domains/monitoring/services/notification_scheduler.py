"""모니터링 결과를 알림 이벤트로 변환하는 스케줄러 유틸리티입니다."""
from __future__ import annotations

from datetime import datetime
from src.app.core.config import Config
from typing import Any, Dict, List, Optional

from src.app.core.logger import LogCategory, log_error, log_info
from src.domains.monitoring.services.monitoring_service import MonitoringResult
from src.domains.analysis.services.notification_config import (
    NotificationConfig,
    NotificationEvent,
    NotificationPriority,
)

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

__all__ = [
    'determine_notification_priority',
    'create_notification_event',
    'log_notification',
    'group_results_by_district',
    'create_batch_notification_summary',
    'should_send_batch_email',
]
