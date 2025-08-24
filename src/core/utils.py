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

from src.core.config import Config


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
    """Streamlit 시크릿, 환경 변수 또는 로컬 .env 파일에서 API 키를 확인합니다.

    우선 순위:
    1. Streamlit 시크릿 (OPENAI_API_KEY, OPEN_API_KEY)
    2. 환경 변수 (OPENAI_API_KEY, OPEN_API_KEY)
    3. 현재 작업 디렉터리의 .env 파일 (OPENAI_API_KEY 또는 OPEN_API_KEY 포함)
    """
    # 1) Streamlit 시크릿
    try:
        if "OPENAI_API_KEY" in st.secrets and st.secrets["OPENAI_API_KEY"]:
            return st.secrets["OPENAI_API_KEY"]
        if "OPEN_API_KEY" in st.secrets and st.secrets["OPENAI_API_KEY"]:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    # 2) 환경 변수
    for name in ("OPENAI_API_KEY", "OPEN_API_KEY"):
        val = os.getenv(name)
        if val and val.strip():
            return val.strip()

    # 3) .env 파일 (간단한 구문 분석, 종속성 없음)
    try:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k in ("OPENAI_API_KEY", "OPEN_API_KEY") and v:
                        return v
    except Exception:
        pass

    return None
