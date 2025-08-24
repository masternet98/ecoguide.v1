"""
Streamlit 애플리케이션을 위한 UI 구성 요소를 제공하는 모듈입니다.
설치 가이드 UI를 포함합니다.
"""
import streamlit as st

def installation_guide_ui():
    """설치 지침을 보여주기 위한 UI입니다."""
    with st.expander("📦 설치 가이드", expanded=False):
        st.markdown(
            """
            **필수 패키지:**
            ```bash
            pip install streamlit openai pillow
            ```
            **외부 공유 (선택 사항):**
            - **Windows:** `winget install Cloudflare.cloudflared`
            - **macOS:** `brew install cloudflared`
            - **Linux:** [공식 문서](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) 참고

            **앱 실행:**
            ```bash
            streamlit run app.py
            ```
            """
        )
