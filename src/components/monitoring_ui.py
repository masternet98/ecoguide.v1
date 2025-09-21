"""
모니터링 시스템 관리를 위한 UI 컴포넌트입니다.
관리자가 시군구별 URL 및 파일 변경사항을 모니터링하고 배치 작업을 관리할 수 있습니다.
"""
import streamlit as st

from src.core.config import Config
from src.core.logger import log_error, log_info, LogCategory
from src.services.batch_service import BatchConfig, initialize_batch_system

from .monitoring_dashboard import (
    show_batch_management,
    show_manual_monitoring,
    show_monitoring_dashboard,
    show_monitoring_settings,
    show_notification_history,
)


def show_monitoring_main(config: Config):
    """
    모니터링 시스템의 메인 인터페이스를 표시합니다.
    """
    st.title("📊 시스템 모니터링")
    
    # 탭 구성
    tabs = st.tabs([
        "📈 대시보드",
        "🔍 수동 검사", 
        "⚙️ 배치 관리",
        "📧 알림 이력",
        "⚙️ 설정"
    ])
    
    with tabs[0]:
        show_monitoring_dashboard(config)
    
    with tabs[1]:
        show_manual_monitoring(config)
    
    with tabs[2]:
        show_batch_management(config)
    
    with tabs[3]:
        show_notification_history(config)
    
    with tabs[4]:
        show_monitoring_settings(config)

# 초기화 함수
def initialize_monitoring_system(config: Config, start_batch: bool = False):
    """
    모니터링 시스템을 초기화합니다.
    
    Args:
        config: 애플리케이션 설정
        start_batch: 배치 스케줄러 자동 시작 여부
    """
    try:
        # 배치 시스템 초기화
        batch_config = BatchConfig(
            enabled=True,
            enable_monitoring_check=True,
            enable_daily_summary=True
        )
        
        initialize_batch_system(config, batch_config, start_scheduler=start_batch)
        
        log_info(
            LogCategory.SYSTEM, "monitoring_ui", "initialize_monitoring_system",
            "모니터링 시스템 초기화 완료", f"Batch scheduler started: {start_batch}"
        )
        
    except Exception as e:
        log_error(
            LogCategory.SYSTEM, "monitoring_ui", "initialize_monitoring_system",
            "모니터링 시스템 초기화 실패", f"Error: {str(e)}", error=e
        )
