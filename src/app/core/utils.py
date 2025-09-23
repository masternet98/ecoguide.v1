"""
Streamlit 애플리케이션을 위한 공유 유틸리티 및 구성을 정의하는 모듈입니다.
애플리케이션 구성, 공유 상태 데이터 클래스 및 OpenAI API 키 확인을 위한
헬퍼 함수를 포함합니다.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List
import subprocess

import streamlit as st
from dotenv import load_dotenv

from src.app.core.config import Config


# =======================
# 공유 상태 데이터 클래스
# =======================

@dataclass
class TunnelState:
    """
    Cloudflared 터널의 상태를 나타냅니다.

    속성:
        running (bool): 터널이 현재 실행 중인지 여부.
        proc (Optional[subprocess.Popen]): 터널 프로세스.
        url (str): 터널의 공개 URL.
        logs (List[str]): 터널 프로세스의 로그 메시지 목록.
        auto_start (bool): 앱 시작 시 터널을 자동으로 시작할지 여부.
        port (int): 터널이 연결된 포트.
    """
    port: int
    running: bool = False
    proc: Optional[subprocess.Popen] = None
    url: str = ""
    logs: List[str] = field(default_factory=list)
    auto_start: bool = True


@dataclass
class AppState:
    """
    애플리케이션의 전체 상태를 나타냅니다.

    속성:
        tunnel (TunnelState): Cloudflared 터널의 상태.
    """
    config: Config
    tunnel: TunnelState = field(init=False)

    def __post_init__(self):
        self.tunnel = TunnelState(port=self.config.default_port)


def get_app_state(config: Config) -> AppState:
    """st.session_state에서 앱 상태를 초기화하거나 가져옵니다."""
    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState(config=config)
    return st.session_state.app_state


# =======================
# API 키 / .env 유틸리티
# =======================

def resolve_api_key() -> Optional[str]:
    """
    API 키를 확인하고 반환합니다.
    Streamlit Cloud secrets를 먼저 시도하고, 실패하면 로컬 환경(.env, 환경변수)으로 대체합니다.
    """
    try:
        # Cloud 환경이거나 로컬에 secrets.toml 파일이 있는 경우, 여기서 키를 가져옵니다.
        # 로컬에 secrets.toml이 없으면 st.secrets 접근 시 예외가 발생합니다.
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        # st.secrets 접근에 실패하면 로컬 환경으로 간주하고 다음 단계로 넘어갑니다.
        pass

    # 로컬 환경이거나 Cloud secrets에 키가 없는 경우, .env 및 환경 변수를 확인합니다.
    load_dotenv()
    return os.environ.get("OPENAI_API_KEY")
