"""
이 모듈은 Cloudflared 터널의 핵심 로직을 제공합니다.
터널 시작, 중지, 로그 읽기 등 서비스 관련 기능을 포함합니다.
"""
import os
import re
import time
import threading
import subprocess
import shlex
from typing import Optional

from src.core.utils import TunnelState

def _find_cloudflared_path() -> Optional[str]:
    """PATH 또는 일반적인 설치 위치에서 cloudflared를 찾습니다."""
    try:
        from shutil import which
        path = which("cloudflared")
        if path:
            return path
    except ImportError:
        pass  # 최소 환경을 위한 대체

    if os.name == "nt":
        common_paths = [
            r"C:\\Program Files\\cloudflared\\cloudflared.exe",
            r"C:\\Program Files (x86)\\cloudflared\\cloudflared.exe",
            r"%LOCALAPPDATA%\\cloudflared\\cloudflared.exe",
        ]
        for p in common_paths:
            expanded_p = os.path.expandvars(p)
            if os.path.isfile(expanded_p):
                return expanded_p
    return None


def _cloudflared_reader(proc: subprocess.Popen, state: TunnelState):
    """cloudflared stdout을 읽고, URL을 구문 분석하고, 로그를 디스크에 저장하고, 찾으면 state.url을 설정합니다."""
    primary_pattern = re.compile(r"https?://[a-zA-Z0-9\-]+\.trycloudflare.com")
    cfargo_pattern = re.compile(r"https?://[a-zA-Z0-9\-]+\.cfargotunnel.com")
    generic_url = re.compile(r"https?://[^\s,\"']+")
    json_url = re.compile(r'"url"\s*:\s*"(?P<url>https?://[^"]+)"')
    short_mention = re.compile(r"(https?://[a-zA-Z0-9\-]+\.trycloudflare.com)")

    # 프로젝트 루트의 logs 디렉토리에 로그 파일 저장 (도커/클라우드 배포 호환)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "cloudflared_tunnel.log")
    logfile = None
    try:
        logfile = open(log_path, "a", encoding="utf-8", errors="replace")
    except Exception:
        logfile = None

    try:
        if proc.stdout is None:
            return
        for line in iter(proc.stdout.readline, ""):
            s = line.rstrip("\n")
            if not s:
                continue

            try:
                state.logs.append(s)
            except Exception:
                pass

            if logfile:
                try:
                    logfile.write(s + "\n")
                    logfile.flush()
                except Exception:
                    pass

            if state.url:
                continue

            m = primary_pattern.search(s)
            if m:
                state.url = m.group(0)
                if logfile:
                    logfile.write(f"[info] URL 감지됨: {state.url}\n")
                    logfile.flush()
                continue

            m = cfargo_pattern.search(s)
            if m:
                state.url = m.group(0)
                if logfile:
                    logfile.write(f"[info] CFARGO URL 감지됨: {state.url}\n")
                    logfile.flush()
                continue

            m = json_url.search(s)
            if m:
                candidate = m.group("url")
                if "trycloudflare" in candidate or "cfargotunnel" in candidate:
                    state.url = candidate
                    if logfile:
                        logfile.write(f"[info] JSON URL 감지됨: {state.url}\n")
                        logfile.flush()
                    continue

            m = generic_url.search(s)
            if m:
                candidate = m.group(0)
                if "trycloudflare" in candidate or "cfargotunnel" in candidate:
                    state.url = candidate
                    if logfile:
                        logfile.write(f"[info] 일반 URL 감지됨: {state.url}\n")
                        logfile.flush()
                    continue

            m = short_mention.search(s)
            if m:
                state.url = m.group(1)
                if logfile:
                    logfile.write(f"[info] 짧은 언급 감지됨: {state.url}\n")
                    logfile.flush()
                continue

        proc.wait()
    except Exception as e:
        try:
            state.logs.append(f"[reader-error] {e}")
        except Exception:
            pass
        if logfile:
            try:
                logfile.write(f"[reader-error] {e}\n")
                logfile.flush()
            except Exception:
                pass
    finally:
        if logfile:
            try:
                logfile.close()
            except Exception:
                pass
        if proc.poll() is not None and state.running:
            state.running = False
            state.proc = None


def start_cloudflared_tunnel(state: TunnelState, wait_for_url_seconds: int = 10) -> None:
    """cloudflared 빠른 터널을 시작하고 선택적으로 공개 URL을 잠시 기다립니다."""
    if state.proc is not None:
        try:
            if state.proc.poll() is None:
                state.running = True
                return
            else:
                state.proc = None
                state.running = False
        except Exception:
            state.proc = None
            state.running = False

    cpath = _find_cloudflared_path()
    if not cpath:
        raise FileNotFoundError(
            "cloudflared 실행 파일을 찾을 수 없습니다. PATH에 추가하거나 공식 문서에 따라 설치하세요."
        )

    # 입력 검증 및 보안 강화
    if not isinstance(state.port, int) or state.port < 1 or state.port > 65535:
        raise ValueError(f"유효하지 않은 포트: {state.port}")
    
    # 안전한 명령어 구성 (shlex를 통한 이스케이핑)
    url_arg = f"http://localhost:{state.port}"
    cmd = [cpath, "tunnel", "--url", url_arg, "--no-autoupdate", "--loglevel", "info"]

    state.url = ""
    state.logs = []

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8'
    )

    state.proc = proc
    state.running = True

    t = threading.Thread(target=_cloudflared_reader, args=(proc, state), daemon=True)
    t.start()

    deadline = time.time() + float(wait_for_url_seconds)
    while time.time() < deadline:
        if state.url:
            break
        time.sleep(0.2)


def stop_cloudflared_tunnel(state: TunnelState) -> None:
    """cloudflared 터널 프로세스를 중지하고 런타임 상태를 지웁니다."""
    if state.proc:
        try:
            state.proc.terminate()
            try:
                state.proc.wait(timeout=5)
            except Exception:
                state.proc.kill()
        except Exception:
            try:
                state.proc.kill()
            except Exception:
                pass

    state.proc = None
    state.running = False
    state.url = ""
