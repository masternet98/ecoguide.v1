"""
이 모듈은 Cloudflare 터널 관리를 위한 Streamlit UI 컴포넌트를 제공합니다.
"""
import io
import streamlit as st
import qrcode
from src.app.core.utils import TunnelState
from src.domains.infrastructure.services.tunnel_service import start_cloudflared_tunnel, stop_cloudflared_tunnel

def tunnel_sidebar_ui(state: TunnelState):
    """Cloudflare 터널 관리를 위한 UI - 사이드바 또는 메인 관리자 페이지에서 사용할 수 있습니다."""
    st.subheader("🌐 외부 공유 URL (Cloudflare Tunnel)")
    st.caption("로컬 앱을 임시 공개 URL로 노출합니다 (cloudflared 필요).")

    # 현재 터널 상태 표시
    if state.running:
        st.success("✅ 터널 상태: 실행 중")
    else:
        st.error("❌ 터널 상태: 중지됨")

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
        if state.url:
            st.success("✅ 공유 URL이 생성되었습니다!")
            
            # URL 정보 표시
            st.info(f"🔗 **공개 URL**: {state.url}")
            
            # 액션 버튼들
            col1, col2 = st.columns(2)
            with col1:
                st.link_button("🌐 브라우저에서 열기", state.url, use_container_width=True)
            with col2:
                if st.button("📋 URL 복사", use_container_width=True):
                    st.toast("URL이 클립보드에 복사되었습니다!", icon="📋")
            
            # URL 코드 박스
            st.code(state.url, language=None)

            # QR 코드 생성 (기본 표시)
            st.subheader("📱 QR 코드로 바로가기")
            try:
                qr_img = qrcode.make(state.url)
                buf = io.BytesIO()
                qr_img.save(buf, format='PNG')
                buf.seek(0)

                # 중앙정렬을 위한 컬럼 구성
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.image(buf, caption="QR 코드를 스캔하여 바로 접속하세요", width=600)
            except Exception as e:
                st.error(f"QR 코드 생성 실패: {e}")
        else:
            st.info("⏳ 터널 시작 중... 공개 URL을 대기하고 있습니다.")
            st.caption("잠시만 기다려주세요. 터널이 활성화되고 URL이 생성되는데 몇 초가 걸릴 수 있습니다.")
    else:
        st.info("💤 터널이 중지되어 있습니다.")
        st.caption("터널을 시작하여 외부에서 접속 가능한 URL을 생성하세요.")
