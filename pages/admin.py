"""
Streamlit 애플리케이션의 관리자 페이지를 정의하는 모듈입니다.
Cloudflared 터널 관리, 로그 보기, 환경 변수 다시 로드 기능과
시군구별 대형폐기물 배출 신고 링크 자동 수집 기능을 제공합니다.
"""
import os
import streamlit as st
from src.components.tunnel_ui import tunnel_sidebar_ui
from src.components.link_collector_ui import link_collector_ui
from src.core.utils import get_app_state
from src.core.config import load_config

# 페이지 타이틀 설정
config = load_config()
st.title("🔧 Admin - 관리 페이지")
st.caption("터널 및 디버깅 도구를 관리합니다.")

# 앱 상태 가져오기
app_state = get_app_state(config=config)
tunnel_state = app_state.tunnel

st.header("Cloudflared 터널 제어")
# 중앙 집중식 터널 제어(사이드바 또는 메인)를 표시합니다.
tunnel_sidebar_ui(tunnel_state)

st.divider()
st.header("로그 다운로드 / 보기")
# 프로젝트 루트의 logs 디렉토리에서 로그 파일 찾기 (도커/클라우드 배포 호환)
project_root = os.path.dirname(os.path.dirname(__file__))
log_path = os.path.join(project_root, "logs", "cloudflared_tunnel.log")
if os.path.isfile(log_path):
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            log_data = fh.read()
    except Exception as e:
        st.error(f"로그를 읽는 중 오류가 발생했습니다: {e}")
        log_data = ""

    st.text_area("cloudflared_tunnel.log (최근 내용)", value=log_data[-20000:], height=300)
    st.download_button("로그 파일 다운로드", data=log_data, file_name="cloudflared_tunnel.log", mime="text/plain")
else:
    st.info("로그 파일이 없습니다. 터널을 시작하면 생성됩니다.")

st.divider()

# 링크 수집기 UI 표시
try:
    link_collector_ui()
except Exception as e:
    st.error(f"링크 수집기 UI 로드 중 오류가 발생했습니다: {str(e)}")
    st.write("자세한 오류 정보:")
    st.code(str(e))

st.divider()
st.header("환경 및 키 설정")
st.write("현재 .env 로드 우선순위: Streamlit secrets → 환경변수 → .env 파일")
if st.button("환경변수(.env) 다시 로드"):
    # resolve_api_key가 .env / env var를 다시 읽도록 다시 실행하는 간단한 방법입니다.
    # Guard for Streamlit versions that may not expose experimental_rerun.
    # If available, call it; otherwise set a small session_state toggle to
    # encourage a rerun without raising AttributeError.
    try:
        rerun_fn = getattr(st, "experimental_rerun", None)
        if callable(rerun_fn):
            rerun_fn()
        else:
            # Fallback: toggle a session key (this won't force a true rerun in all
            # Streamlit versions, but prevents AttributeError and keeps behavior safe).
            st.session_state["_admin_rerun_toggle"] = not st.session_state.get("_admin_rerun_toggle", False)
    except Exception:
        # Swallow unexpected errors here to avoid breaking admin UI.
        pass
