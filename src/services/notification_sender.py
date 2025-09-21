"""알림 이메일 발송을 담당하는 모듈입니다."""
from __future__ import annotations

import smtplib
from datetime import datetime
from src.core.config import Config
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from src.core.logger import LogCategory, log_error, log_info
from src.services.monitoring_service import get_monitoring_summary
from src.services.notification_config import (
    NotificationConfig,
    NotificationEvent,
    get_notification_history,
    load_notification_config,
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

__all__ = [
    'send_email_notification',
    'send_batch_summary_email',
    'create_daily_summary_email',
    'send_daily_summary_email',
    'send_test_email',
]
