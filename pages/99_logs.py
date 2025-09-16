"""
시스템 로그 뷰어 페이지
애플리케이션의 모든 로그를 모니터링하고 분석할 수 있습니다.
"""
import streamlit as st
from src.components.log_viewer import render_log_viewer

# 페이지 설정
st.set_page_config(
    page_title="시스템 로그 - EcoGuide", 
    page_icon="📊", 
    layout="wide"
)

# 메인 로그 뷰어 렌더링
render_log_viewer()

# 사이드바 정보
with st.sidebar:
    st.header("📊 로그 시스템 정보")
    
    st.markdown("""
    ### 🔍 로그 카테고리
    - **SYSTEM**: 시스템 전반적인 로그
    - **CSV_PROCESSING**: CSV 파일 처리 관련
    - **WEB_SCRAPING**: 웹 스크래핑 관련
    - **API_CALL**: API 호출 관련
    - **FILE_OPERATION**: 파일 입출력 관련
    - **UI_INTERACTION**: 사용자 인터페이스 관련
    - **DATABASE**: 데이터베이스 관련
    - **VALIDATION**: 데이터 검증 관련
    
    ### 📈 로그 레벨
    - **DEBUG**: 디버깅 정보
    - **INFO**: 일반 정보
    - **WARNING**: 경고
    - **ERROR**: 오류
    - **CRITICAL**: 치명적 오류
    
    ### 💡 사용 팁
    - **실시간 로그**: 최신 로그를 실시간으로 확인
    - **에러 대시보드**: 에러 패턴 분석
    - **로그 검색**: 특정 조건으로 로그 필터링
    - **로그 관리**: 로그 파일 다운로드 및 관리
    """)
    
    st.divider()
    
    st.markdown("""
    ### 🚨 문제 해결
    **로그가 표시되지 않는 경우:**
    1. 애플리케이션에서 작업 수행
    2. 새로고침 버튼 클릭
    3. 필터 조건 확인
    
    **에러 분석 방법:**
    1. 에러 대시보드에서 패턴 확인
    2. 로그 검색으로 상세 조회
    3. 스택 트레이스 분석
    """)