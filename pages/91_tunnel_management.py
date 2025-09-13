"""
Cloudflared 터널 관리 전용 페이지
터널 시작/중지, 상태 모니터링, 로그 보기 및 다운로드 기능을 제공합니다.
"""
import os
import streamlit as st
from src.components.tunnel_ui import tunnel_sidebar_ui
from src.core.utils import get_app_state
from src.core.config import load_config

# 페이지 설정
st.set_page_config(
    page_title="터널 관리",
    page_icon="🌐",
    layout="wide"
)

# 페이지 타이틀 설정
config = load_config()
st.title("🌐 Cloudflared 터널 관리")
st.caption("Cloudflared 터널의 시작, 중지 및 상태 모니터링을 관리합니다.")

st.divider()

# 앱 상태 가져오기
app_state = get_app_state(config=config)
tunnel_state = app_state.tunnel

# 터널 상태 요약 표시
col1, col2, col3 = st.columns(3)

with col1:
    if tunnel_state.running:
        st.success("✅ 터널 상태: 실행 중")
    else:
        st.error("❌ 터널 상태: 중지됨")

with col2:
    if tunnel_state.url:
        st.info(f"🔗 공개 URL: {tunnel_state.url}")
    else:
        st.info("🔗 공개 URL: 없음")

with col3:
    if tunnel_state.logs and any("error" in log.lower() for log in tunnel_state.logs[-5:]):
        recent_errors = [log for log in tunnel_state.logs[-5:] if "error" in log.lower()]
        st.warning(f"⚠️ 최근 오류: {recent_errors[-1][:50]}..." if recent_errors else "⚠️ 로그에서 오류 발견")
    else:
        st.success("✅ 오류 없음")

st.divider()

# 터널 제어 UI
st.header("🎮 터널 제어")
tunnel_sidebar_ui(tunnel_state)

st.divider()

# 터널 로그 관리
st.header("📋 터널 로그 관리")

# 프로젝트 루트의 logs 디렉토리에서 로그 파일 찾기
project_root = os.path.dirname(os.path.dirname(__file__))
log_path = os.path.join(project_root, "logs", "cloudflared_tunnel.log")

if os.path.isfile(log_path):
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            log_data = fh.read()
        
        # 로그 파일 정보 표시
        log_size = len(log_data)
        log_lines = len(log_data.splitlines())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("파일 크기", f"{log_size:,} bytes")
        with col2:
            st.metric("총 라인 수", f"{log_lines:,} lines")
        with col3:
            if log_data:
                last_modified = os.path.getmtime(log_path)
                import datetime
                last_mod_time = datetime.datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S")
                st.metric("마지막 수정", last_mod_time)
        
        st.subheader("📄 로그 내용 (최근 20,000자)")
        
        # 로그 레벨별 필터링 옵션
        log_filter = st.selectbox(
            "로그 레벨 필터", 
            ["전체", "ERROR", "WARN", "INFO", "DEBUG"],
            index=0
        )
        
        # 필터링된 로그 표시
        filtered_log = log_data
        if log_filter != "전체":
            log_lines_filtered = [line for line in log_data.splitlines() if log_filter in line]
            filtered_log = "\n".join(log_lines_filtered)
        
        # 표시할 로그 데이터 (마지막 20,000자)
        display_log = filtered_log[-20000:] if filtered_log else "로그 데이터가 없습니다."
        
        st.text_area(
            "cloudflared_tunnel.log", 
            value=display_log, 
            height=400,
            help="실시간으로 업데이트되지 않습니다. 새로고침하여 최신 로그를 확인하세요."
        )
        
        # 액션 버튼들
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                "📥 전체 로그 다운로드",
                data=log_data,
                file_name="cloudflared_tunnel.log",
                mime="text/plain",
                use_container_width=True
            )
        
        with col2:
            if st.button("🔄 로그 새로고침", use_container_width=True):
                st.rerun()
        
        with col3:
            if st.button("🗑️ 로그 파일 삭제", use_container_width=True, type="secondary"):
                if st.session_state.get("confirm_log_delete", False):
                    try:
                        os.remove(log_path)
                        st.success("로그 파일이 삭제되었습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"로그 파일 삭제 중 오류 발생: {e}")
                else:
                    st.session_state.confirm_log_delete = True
                    st.warning("다시 클릭하면 로그 파일이 삭제됩니다.")
    
    except Exception as e:
        st.error(f"로그를 읽는 중 오류가 발생했습니다: {e}")
        st.code(str(e))

else:
    st.info("📭 로그 파일이 없습니다.")
    st.write("터널을 시작하면 로그 파일이 생성됩니다.")
    
    # 로그 디렉토리 생성 버튼
    logs_dir = os.path.join(project_root, "logs")
    if not os.path.exists(logs_dir):
        if st.button("📁 로그 디렉토리 생성"):
            try:
                os.makedirs(logs_dir, exist_ok=True)
                st.success(f"로그 디렉토리가 생성되었습니다: {logs_dir}")
            except Exception as e:
                st.error(f"로그 디렉토리 생성 중 오류 발생: {e}")

st.divider()

# 터널 설정 정보
st.header("⚙️ 터널 설정 정보")

if hasattr(config, 'tunnel') and config.tunnel:
    st.json({
        "도메인": getattr(config.tunnel, 'domain', 'N/A'),
        "포트": getattr(config.tunnel, 'port', 'N/A'),
        "로컬 URL": getattr(config.tunnel, 'local_url', 'N/A'),
        "설정 파일": getattr(config.tunnel, 'config_path', 'N/A')
    })
else:
    st.info("터널 설정 정보를 찾을 수 없습니다.")

# 환경변수 재로드
st.divider()
st.header("🔧 환경 설정")
st.write("현재 .env 로드 우선순위: Streamlit secrets → 환경변수 → .env 파일")

if st.button("🔄 환경변수(.env) 다시 로드"):
    try:
        # 페이지 새로고침을 통해 환경변수 재로드
        st.rerun()
    except Exception:
        # 안전한 fallback
        st.session_state["_tunnel_env_rerun_toggle"] = not st.session_state.get("_tunnel_env_rerun_toggle", False)
        st.success("환경변수가 다시 로드됩니다.")