"""
모니터링 시스템 관리 페이지입니다.
시군구별 등록 정보의 변경사항을 자동으로 감지하고 관리자에게 알림을 제공합니다.
"""
import streamlit as st

from src.app.core.config import load_config
from src.domains.monitoring.ui.monitoring_ui import show_monitoring_main, initialize_monitoring_system

# 페이지 설정
st.set_page_config(
    page_title="EcoGuide - 시스템 모니터링",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """모니터링 페이지 메인 함수"""
    try:
        # 설정 로드
        config = load_config()
        
        # 세션 상태에서 모니터링 시스템 초기화 상태 확인
        if "monitoring_initialized" not in st.session_state:
            # 모니터링 시스템 초기화 (배치 스케줄러는 수동 시작)
            initialize_monitoring_system(config, start_batch=False)
            st.session_state.monitoring_initialized = True
        
        # 사이드바에 시스템 정보 표시
        with st.sidebar:
            st.header("🔧 시스템 정보")
            st.info("""
            **모니터링 시스템**
            
            • 자동 변경 감지
            • 이메일 알림 발송
            • 배치 작업 스케줄링
            • 실시간 모니터링 대시보드
            
            시군구별 URL 및 파일 변경사항을 
            자동으로 모니터링합니다.
            """)
            
            st.header("📚 도움말")
            with st.expander("사용법"):
                st.write("""
                **대시보드**: 전체 시스템 상태 확인
                
                **수동 검사**: 즉시 모니터링 실행
                
                **배치 관리**: 자동 스케줄 관리
                
                **알림 이력**: 과거 알림 내역 확인
                
                **설정**: 이메일 알림 설정
                """)
            
            with st.expander("주의사항"):
                st.warning("""
                • 이메일 알림은 환경변수 설정 필요
                • 배치 스케줄러는 수동으로 시작
                • 대량 검사 시 서버 부하 주의
                """)
        
        # 메인 모니터링 인터페이스 표시
        show_monitoring_main(config)
        
    except Exception as e:
        st.error(f"모니터링 페이지 로드 중 오류가 발생했습니다: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()