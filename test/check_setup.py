#!/usr/bin/env python3
"""
EcoGuide 설정 진단 도구

이 스크립트는 애플리케이션 실행 전 필수 설정과 의존성을 확인합니다.
"""
import os
import sys
import importlib.util
from pathlib import Path
from typing import List, Tuple, Dict, Any
import subprocess

# 색상 코드
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def print_status(status: str, message: str) -> None:
    """상태에 따라 색상이 있는 메시지 출력"""
    color_map = {
        "✓": Colors.GREEN,
        "⚠": Colors.YELLOW,
        "✗": Colors.RED,
        "ℹ": Colors.BLUE
    }
    color = color_map.get(status, "")
    print(f"{color}{status} {message}{Colors.ENDC}")

def check_python_version() -> bool:
    """Python 버전 확인"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_status("✓", f"Python 버전: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_status("✗", f"Python 버전이 부족합니다: {version.major}.{version.minor}.{version.micro} (3.8+ 필요)")
        return False

def check_core_dependencies() -> Tuple[bool, List[str]]:
    """핵심 의존성 확인"""
    core_deps = [
        "streamlit", "openai", "pillow", "qrcode", 
        "numpy", "python-dotenv", "pandas", "requests"
    ]
    
    missing = []
    installed = []
    
    for dep in core_deps:
        # qrcode는 qrcode[pil]로 설치되므로 별도 처리
        module_name = "qrcode" if dep == "qrcode" else dep.replace("-", "_")
        
        if importlib.util.find_spec(module_name):
            installed.append(dep)
            print_status("✓", f"핵심 의존성: {dep}")
        else:
            missing.append(dep)
            print_status("✗", f"누락된 핵심 의존성: {dep}")
    
    return len(missing) == 0, missing

def check_vision_dependencies() -> Tuple[bool, List[str]]:
    """비전 의존성 확인 (선택적)"""
    vision_deps = [
        ("torch", "PyTorch"),
        ("ultralytics", "YOLO"),
        ("rembg", "Background Removal"),
        ("cv2", "OpenCV"),
        ("mediapipe", "MediaPipe"),
        ("beautifulsoup4", "BeautifulSoup")
    ]
    
    missing = []
    installed = []
    
    for module_name, display_name in vision_deps:
        # OpenCV는 cv2로 import
        check_name = "cv2" if module_name == "cv2" else module_name
        
        if importlib.util.find_spec(check_name):
            installed.append(display_name)
            print_status("✓", f"비전 의존성: {display_name}")
        else:
            missing.append(display_name)
            print_status("⚠", f"누락된 비전 의존성: {display_name}")
    
    return len(missing) == 0, missing

def check_environment_variables() -> Tuple[bool, Dict[str, Any]]:
    """환경 변수 확인"""
    env_status = {}
    all_good = True
    
    # OpenAI API Key 확인
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        # 키가 적절한 형식인지 확인
        if openai_key.startswith("sk-") and len(openai_key) > 20:
            print_status("✓", "OpenAI API Key 설정됨")
            env_status["openai_api_key"] = "valid"
        else:
            print_status("⚠", "OpenAI API Key 형식이 올바르지 않을 수 있습니다")
            env_status["openai_api_key"] = "invalid_format"
            all_good = False
    else:
        print_status("⚠", "OpenAI API Key가 설정되지 않았습니다")
        env_status["openai_api_key"] = "missing"
        all_good = False
    
    # .env 파일 확인
    env_file = Path(".env")
    if env_file.exists():
        print_status("✓", ".env 파일 존재")
        env_status["env_file"] = True
    else:
        print_status("⚠", ".env 파일이 없습니다")
        env_status["env_file"] = False
    
    return all_good, env_status

def check_file_structure() -> Tuple[bool, List[str]]:
    """필수 파일/디렉토리 구조 확인"""
    required_paths = [
        "app.py",
        "src/",
        "src/core/",
        "src/services/",
        "src/components/",
        "requirements.txt"
    ]
    
    missing = []
    
    for path in required_paths:
        if Path(path).exists():
            print_status("✓", f"파일/디렉토리: {path}")
        else:
            missing.append(path)
            print_status("✗", f"누락된 파일/디렉토리: {path}")
    
    return len(missing) == 0, missing

def run_config_validation() -> bool:
    """설정 검증 실행"""
    try:
        # 설정 모듈 로드 및 검증 시도
        sys.path.insert(0, os.getcwd())
        from src.core.config import load_config
        from src.core.config_validator import validate_config
        
        config = load_config()
        _, validation_results = validate_config(config, auto_fix=False)
        
        has_errors = False
        for result in validation_results:
            if result.is_valid:
                print_status("✓", f"설정 검증: {result.field_name}")
            else:
                if result.severity.value == "critical":
                    print_status("✗", f"심각한 설정 오류: {result.field_name} - {result.message}")
                    has_errors = True
                elif result.severity.value == "error":
                    print_status("✗", f"설정 오류: {result.field_name} - {result.message}")
                    has_errors = True
                else:
                    print_status("⚠", f"설정 경고: {result.field_name} - {result.message}")
        
        return not has_errors
        
    except Exception as e:
        print_status("✗", f"설정 검증 실패: {str(e)}")
        return False

def generate_install_commands(missing_core: List[str], missing_vision: List[str]) -> None:
    """설치 명령어 생성"""
    if missing_core or missing_vision:
        print(f"\n{Colors.BOLD}📦 설치 명령어:{Colors.ENDC}")
        
        if missing_core:
            print("\n핵심 의존성 설치:")
            print(f"pip install -r requirements.txt")
        
        if missing_vision:
            print("\n비전 의존성 설치 (선택적):")
            vision_packages = {
                "PyTorch": "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
                "YOLO": "ultralytics",
                "Background Removal": "rembg",
                "OpenCV": "opencv-python-headless",
                "MediaPipe": "mediapipe",
                "BeautifulSoup": "beautifulsoup4"
            }
            
            for missing in missing_vision:
                if missing in vision_packages:
                    print(f"pip install {vision_packages[missing]}")

def generate_environment_setup() -> None:
    """환경 설정 안내"""
    print(f"\n{Colors.BOLD}🔧 환경 설정:{Colors.ENDC}")
    print("1. .env 파일 생성 또는 편집:")
    print("   OPENAI_API_KEY=your-openai-api-key-here")
    print("\n2. 또는 환경 변수 직접 설정:")
    print("   export OPENAI_API_KEY=your-openai-api-key-here")

def main():
    """메인 진단 함수"""
    print(f"{Colors.BOLD}🔍 EcoGuide 설정 진단 시작{Colors.ENDC}")
    print("=" * 50)
    
    all_checks_passed = True
    
    # 1. Python 버전 확인
    print(f"\n{Colors.BOLD}🐍 Python 환경:{Colors.ENDC}")
    if not check_python_version():
        all_checks_passed = False
    
    # 2. 파일 구조 확인
    print(f"\n{Colors.BOLD}📁 파일 구조:{Colors.ENDC}")
    structure_ok, missing_files = check_file_structure()
    if not structure_ok:
        all_checks_passed = False
    
    # 3. 핵심 의존성 확인
    print(f"\n{Colors.BOLD}📦 핵심 의존성:{Colors.ENDC}")
    core_ok, missing_core = check_core_dependencies()
    if not core_ok:
        all_checks_passed = False
    
    # 4. 비전 의존성 확인 (선택적)
    print(f"\n{Colors.BOLD}👁️  비전 의존성 (선택적):{Colors.ENDC}")
    vision_ok, missing_vision = check_vision_dependencies()
    
    # 5. 환경 변수 확인
    print(f"\n{Colors.BOLD}🔐 환경 변수:{Colors.ENDC}")
    env_ok, env_status = check_environment_variables()
    
    # 6. 설정 검증 (핵심 의존성이 있을 때만)
    if core_ok:
        print(f"\n{Colors.BOLD}⚙️  설정 검증:{Colors.ENDC}")
        config_ok = run_config_validation()
        if not config_ok:
            all_checks_passed = False
    
    # 결과 요약
    print("\n" + "=" * 50)
    
    if all_checks_passed and core_ok:
        print_status("✓", f"{Colors.BOLD}모든 필수 확인 사항이 통과했습니다!{Colors.ENDC}")
        print_status("ℹ", "애플리케이션을 실행할 수 있습니다: streamlit run app.py")
        
        if not vision_ok:
            print_status("ℹ", f"비전 기능은 제한됩니다 ({len(missing_vision)}개 의존성 누락)")
    else:
        print_status("✗", f"{Colors.BOLD}일부 확인 사항에서 문제가 발견되었습니다{Colors.ENDC}")
        
        # 해결 방법 제시
        if missing_core or missing_vision:
            generate_install_commands(missing_core, missing_vision)
        
        if not env_ok:
            generate_environment_setup()
        
        print(f"\n{Colors.BOLD}❓ 문제 해결 후 다시 실행하세요:{Colors.ENDC}")
        print("python check_setup.py")
    
    return 0 if all_checks_passed else 1

if __name__ == "__main__":
    sys.exit(main())