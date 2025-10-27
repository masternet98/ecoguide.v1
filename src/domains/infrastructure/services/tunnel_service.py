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

from src.app.core.utils import TunnelState

def _find_cloudflared_path() -> Optional[str]:
    """
    cloudflared 바이너리를 찾거나 자동으로 다운로드합니다.

    우선순위:
    1. pycloudflared의 cloudflared 바이너리 (다운로드 가능)
    2. 시스템 PATH의 cloudflared
    3. 플랫폼별 일반적인 설치 위치
    """
    # 1. pycloudflared에서 제공하는 cloudflared 바이너리 확인
    try:
        from pycloudflared.util import get_info, download, Info

        info = get_info()

        # 파일이 이미 있는지 확인
        if os.path.isfile(info.executable):
            return info.executable

        # pycloudflared의 패키지 디렉토리 확인
        import pycloudflared
        pycf_dir = os.path.dirname(pycloudflared.__file__)

        # 플랫폼별로 가능한 파일명 확인
        possible_names = []
        if os.name == "nt":
            # Windows: cloudflared-windows-amd64.exe, cloudflared-windows-arm64.exe 등
            possible_names.extend([
                "cloudflared-windows-amd64.exe",
                "cloudflared-windows-arm64.exe",
                "cloudflared.exe",
            ])
        elif os.uname().sysname == "Darwin":
            # macOS: cloudflared
            possible_names.extend(["cloudflared"])
        else:
            # Linux: cloudflared-linux-amd64, cloudflared-linux-arm64 등
            possible_names.extend([
                "cloudflared-linux-amd64",
                "cloudflared-linux-arm64",
                "cloudflared",
            ])

        for fname in possible_names:
            fpath = os.path.join(pycf_dir, fname)
            if os.path.isfile(fpath):
                return fpath

        # 파일을 찾지 못했으므로 자동으로 다운로드
        print("[INFO] cloudflared를 자동으로 다운로드하고 있습니다...")
        cloudflared_path = download(info)
        if os.path.isfile(cloudflared_path):
            return cloudflared_path

    except ImportError:
        pass  # pycloudflared 미설치
    except Exception as e:
        print(f"[WARNING] pycloudflared에서 cloudflared를 찾을 수 없습니다: {e}")

    # 2. 시스템 PATH에서 cloudflared 찾기
    try:
        from shutil import which
        path = which("cloudflared")
        if path:
            return path
    except (ImportError, Exception):
        pass  # 최소 환경을 위한 대체

    # 3. 플랫폼별 일반적인 설치 위치
    if os.name == "nt":
        common_paths = [
            r"C:\Program Files\cloudflared\cloudflared.exe",
            r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
            r"%LOCALAPPDATA%\cloudflared\cloudflared.exe",
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
            "cloudflared 실행 파일을 찾을 수 없습니다.\n"
            "\n설치 방법:\n"
            "1. pip install -r requirements.txt 실행 (pycloudflared 포함)\n"
            "2. 또는 다음 명령어로 수동 설치:\n"
            "   - Linux: sudo apt-get install cloudflared\n"
            "   - macOS: brew install cloudflare/cloudflare/cloudflared\n"
            "   - Windows: choco install cloudflared\n"
            "   - 또는: pip install pycloudflared"
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
