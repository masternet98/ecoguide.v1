"""
이 모듈은 Cloudflare 터널 관리를 위한 Streamlit UI 컴포넌트를 제공합니다.
"""
import io
import streamlit as st
import qrcode
from src.core.utils import TunnelState
from src.services.tunnel_service import start_cloudflared_tunnel, stop_cloudflared_tunnel

def tunnel_sidebar_ui(state: TunnelState):
    """Cloudflare 터널 관리를 위한 UI - 사이드바 또는 메인 관리자 페이지에서 사용할 수 있습니다."""
    st.subheader("🌐 외부 공유 URL (Cloudflare Tunnel)")
    st.caption("로컬 앱을 임시 공개 URL로 노출합니다 (cloudflared 필요).")

    col_port, col_auto = st.columns(2)
    state.port = col_port.number_input(
        "로컬 포트", 1, 65535, state.port, help="Streamlit 기본 포트는 8501입니다."
    )
    state.auto_start = col_auto.toggle("앱 시작 시 자동 실행", value=state.auto_start)

    run_col, stop_col = st.columns(2)
    if run_col.button("▶️ 터널 시작", use_container_width=True, disabled=state.running):
        try:
            start_cloudflared_tunnel(state, wait_for_url_seconds=8)
            st.toast("Cloudflared 터널을 시작했습니다.", icon="✅")
            st.rerun()
        except FileNotFoundError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"터널 시작 실패: {e}")

    if stop_col.button("⏹️ 터널 중지", use_container_width=True, disabled=not state.running):
        stop_cloudflared_tunnel(state)
        st.toast("Cloudflared 터널을 중지했습니다.", icon="🛑")
        st.rerun()

    if state.running:
        st.info("터널 실행 중...")
        if state.url:
            st.success("공유 URL이 생성되었습니다.")
            st.link_button("브라우저에서 열기", state.url, use_container_width=True)
            st.code(state.url, language=None)

            with st.expander("📱 QR 코드로 바로가기"):
                qr_img = qrcode.make(state.url)
                buf = io.BytesIO()
                qr_img.save(buf)
                st.image(buf, width=400)
        else:
            st.info("임시 주소를 대기 중입니다...")
    else:
        st.warning("터널 중지됨")
