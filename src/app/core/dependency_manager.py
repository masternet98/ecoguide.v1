"""
애플리케이션 의존성 관리 시스템.

선택적 의존성을 체크하고, 런타임에 기능을 활성화/비활성화하며,
사용자에게 친화적인 오류 메시지를 제공합니다.
"""
import importlib
import subprocess
import sys
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DependencyStatus(Enum):
    """의존성 상태"""
    AVAILABLE = "available"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


@dataclass
class DependencyInfo:
    """의존성 정보"""
    name: str
    import_name: str
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    install_command: Optional[str] = None
    description: str = ""
    is_optional: bool = False
    status: DependencyStatus = DependencyStatus.UNKNOWN
    installed_version: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DependencyGroup:
    """기능별 의존성 그룹"""
    name: str
    display_name: str
    description: str
    dependencies: List[DependencyInfo]
    is_critical: bool = False


class DependencyChecker:
    """의존성 체크 및 관리 클래스"""
    
    def __init__(self):
        self.dependency_groups: Dict[str, DependencyGroup] = {}
        self._setup_default_dependencies()
    
    def _setup_default_dependencies(self):
        """기본 의존성 그룹들을 설정합니다."""
        
        # Core 의존성 (필수)
        core_deps = [
            DependencyInfo(
                name="streamlit",
                import_name="streamlit",
                min_version="1.33.0",
                install_command="pip install streamlit>=1.33.0",
                description="웹 UI 프레임워크",
                is_optional=False
            ),
            DependencyInfo(
                name="openai",
                import_name="openai", 
                min_version="1.40.0",
                install_command="pip install openai>=1.40.0",
                description="OpenAI API 클라이언트",
                is_optional=False
            ),
            DependencyInfo(
                name="pillow",
                import_name="PIL",
                min_version="10.0.0",
                install_command="pip install Pillow>=10.0.0",
                description="이미지 처리 라이브러리",
                is_optional=False
            )
        ]
        
        self.dependency_groups["core"] = DependencyGroup(
            name="core",
            display_name="핵심 기능",
            description="애플리케이션 실행에 필수적인 라이브러리들",
            dependencies=core_deps,
            is_critical=True
        )
        
        # Vision 의존성 (선택적, 무거운 의존성)
        vision_deps = [
            DependencyInfo(
                name="torch",
                import_name="torch",
                install_command="pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
                description="PyTorch 딥러닝 프레임워크",
                is_optional=True
            ),
            DependencyInfo(
                name="ultralytics",
                import_name="ultralytics",
                min_version="8.0.20",
                install_command="pip install ultralytics==8.0.20",
                description="YOLO 객체 검출 모델",
                is_optional=True
            ),
            DependencyInfo(
                name="rembg",
                import_name="rembg",
                min_version="2.0.57",
                install_command="pip install rembg==2.0.57",
                description="배경 제거 라이브러리",
                is_optional=True
            ),
            DependencyInfo(
                name="mediapipe",
                import_name="mediapipe",
                min_version="0.10.14",
                install_command="pip install mediapipe==0.10.14",
                description="Google MediaPipe (손 검출)",
                is_optional=True
            ),
            DependencyInfo(
                name="opencv-python",
                import_name="cv2",
                install_command="pip install opencv-python-headless",
                description="OpenCV 컴퓨터 비전 라이브러리",
                is_optional=True
            )
        ]
        
        self.dependency_groups["vision"] = DependencyGroup(
            name="vision",
            display_name="비전 분석",
            description="로컬 컴퓨터 비전 분석을 위한 라이브러리들 (용량이 큽니다)",
            dependencies=vision_deps,
            is_critical=False
        )
        
        # Web/Data 의존성 (필수이지만 가벼운 의존성)
        web_deps = [
            DependencyInfo(
                name="requests",
                import_name="requests",
                min_version="2.28.0",
                install_command="pip install requests>=2.28.0",
                description="HTTP 요청 라이브러리",
                is_optional=False
            ),
            DependencyInfo(
                name="beautifulsoup4",
                import_name="bs4",
                min_version="4.11.0",
                install_command="pip install beautifulsoup4>=4.11.0",
                description="HTML 파싱 라이브러리",
                is_optional=False
            ),
            DependencyInfo(
                name="pandas",
                import_name="pandas",
                min_version="2.0.0",
                install_command="pip install pandas>=2.0.0",
                description="데이터 분석 라이브러리",
                is_optional=False
            )
        ]
        
        self.dependency_groups["web_data"] = DependencyGroup(
            name="web_data",
            display_name="웹/데이터",
            description="웹 크롤링 및 데이터 처리를 위한 라이브러리들",
            dependencies=web_deps,
            is_critical=True
        )
    
    def check_dependency(self, dep_info: DependencyInfo) -> DependencyInfo:
        """개별 의존성을 체크합니다."""
        try:
            module = importlib.import_module(dep_info.import_name)
            
            # 버전 체크 (가능한 경우)
            version = self._get_module_version(module, dep_info.import_name)
            dep_info.installed_version = version
            
            if version and dep_info.min_version:
                if self._compare_versions(version, dep_info.min_version) < 0:
                    dep_info.status = DependencyStatus.INCOMPATIBLE
                    dep_info.error_message = f"버전이 너무 낮습니다 (현재: {version}, 필요: {dep_info.min_version}+)"
                    return dep_info
            
            dep_info.status = DependencyStatus.AVAILABLE
            logger.debug(f"Dependency available: {dep_info.name} ({version or 'unknown version'})")
            
        except ImportError as e:
            dep_info.status = DependencyStatus.MISSING
            dep_info.error_message = f"모듈을 가져올 수 없습니다: {e}"
            logger.debug(f"Dependency missing: {dep_info.name}")
            
        except Exception as e:
            dep_info.status = DependencyStatus.UNKNOWN
            dep_info.error_message = f"의존성 체크 중 오류: {e}"
            logger.warning(f"Error checking dependency {dep_info.name}: {e}")
        
        return dep_info
    
    def _get_module_version(self, module, import_name: str) -> Optional[str]:
        """모듈 버전을 가져옵니다."""
        version_attrs = ['__version__', 'version', 'VERSION']
        
        for attr in version_attrs:
            if hasattr(module, attr):
                version = getattr(module, attr)
                if isinstance(version, str):
                    return version
                elif hasattr(version, '__str__'):
                    return str(version)
        
        # 특별한 경우들 처리
        if import_name == 'cv2':
            try:
                return module.cv2.__version__
            except:
                pass
        
        return None
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """버전을 비교합니다. -1, 0, 1을 반환합니다."""
        try:
            from packaging import version
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
                
        except ImportError:
            # packaging이 없으면 간단한 문자열 비교
            if version1 < version2:
                return -1
            elif version1 > version2:
                return 1
            else:
                return 0
    
    def check_group(self, group_name: str) -> DependencyGroup:
        """의존성 그룹을 체크합니다."""
        if group_name not in self.dependency_groups:
            raise ValueError(f"Unknown dependency group: {group_name}")
        
        group = self.dependency_groups[group_name]
        
        for dep in group.dependencies:
            self.check_dependency(dep)
        
        logger.info(f"Checked dependency group: {group_name}")
        return group
    
    def check_all_groups(self) -> Dict[str, DependencyGroup]:
        """모든 의존성 그룹을 체크합니다."""
        results = {}
        
        for group_name in self.dependency_groups:
            results[group_name] = self.check_group(group_name)
        
        return results
    
    def get_missing_critical_dependencies(self) -> List[DependencyInfo]:
        """누락된 중요 의존성들을 반환합니다."""
        missing_deps = []
        
        for group in self.dependency_groups.values():
            if group.is_critical:
                for dep in group.dependencies:
                    if not dep.is_optional and dep.status == DependencyStatus.MISSING:
                        missing_deps.append(dep)
        
        return missing_deps
    
    def get_installation_commands(self, group_name: str) -> List[str]:
        """의존성 그룹의 설치 명령어 목록을 반환합니다."""
        if group_name not in self.dependency_groups:
            return []
        
        group = self.dependency_groups[group_name]
        commands = []
        
        for dep in group.dependencies:
            if dep.status == DependencyStatus.MISSING and dep.install_command:
                commands.append(dep.install_command)
        
        return commands
    
    def generate_requirements_txt(self, group_names: List[str] = None) -> str:
        """requirements.txt 형식의 문자열을 생성합니다."""
        if group_names is None:
            group_names = list(self.dependency_groups.keys())
        
        requirements = []
        
        for group_name in group_names:
            if group_name in self.dependency_groups:
                group = self.dependency_groups[group_name]
                requirements.append(f"# {group.display_name}")
                
                for dep in group.dependencies:
                    req_line = dep.name
                    if dep.min_version:
                        req_line += f">={dep.min_version}"
                    if dep.max_version:
                        req_line += f",<{dep.max_version}"
                    requirements.append(req_line)
                
                requirements.append("")  # 빈 줄
        
        return "\n".join(requirements)
    
    def can_enable_feature(self, feature_name: str) -> Tuple[bool, List[str]]:
        """기능을 활성화할 수 있는지 확인합니다."""
        feature_deps_map = {
            "vision_analysis": ["vision"],
            "openai_vision": ["core"],
            "district_management": ["web_data"],
            "link_collector": ["web_data"],
        }
        
        required_groups = feature_deps_map.get(feature_name, [])
        missing_deps = []
        
        for group_name in required_groups:
            if group_name in self.dependency_groups:
                group = self.check_group(group_name)
                
                for dep in group.dependencies:
                    if not dep.is_optional and dep.status != DependencyStatus.AVAILABLE:
                        missing_deps.append(f"{dep.name}: {dep.error_message}")
        
        return len(missing_deps) == 0, missing_deps


def create_streamlit_dependency_ui(checker: DependencyChecker):
    """Streamlit UI에 의존성 상태를 표시합니다."""
    try:
        import streamlit as st
        
        st.subheader("📦 의존성 상태")
        
        results = checker.check_all_groups()
        
        for group_name, group in results.items():
            with st.expander(f"{group.display_name} ({len(group.dependencies)}개 패키지)"):
                st.write(f"**설명:** {group.description}")
                
                all_available = True
                optional_missing = []
                
                for dep in group.dependencies:
                    if dep.status == DependencyStatus.AVAILABLE:
                        st.success(f"✅ {dep.name} ({dep.installed_version or 'unknown version'})")
                    elif dep.status == DependencyStatus.MISSING:
                        if dep.is_optional:
                            st.info(f"⏸️ {dep.name} (선택적, 미설치)")
                            optional_missing.append(dep)
                        else:
                            st.error(f"❌ {dep.name} - {dep.error_message}")
                            all_available = False
                    elif dep.status == DependencyStatus.INCOMPATIBLE:
                        st.warning(f"⚠️ {dep.name} - {dep.error_message}")
                        if not dep.is_optional:
                            all_available = False
                
                # 설치 명령어 표시
                if not all_available or optional_missing:
                    st.write("**설치 명령어:**")
                    commands = checker.get_installation_commands(group_name)
                    if commands:
                        for cmd in commands:
                            st.code(cmd)
                    
                    if optional_missing:
                        st.info("선택적 패키지들은 고급 기능에 필요하며, 설치하지 않아도 기본 기능은 사용 가능합니다.")
        
        # 전체 상태 요약
        critical_missing = checker.get_missing_critical_dependencies()
        if critical_missing:
            st.error("⚠️ 중요한 의존성이 누락되었습니다. 일부 기능이 제한될 수 있습니다.")
        else:
            st.success("✅ 모든 필수 의존성이 설치되어 있습니다.")
    
    except ImportError:
        logger.warning("Streamlit not available for dependency UI display")


def get_dependency_checker() -> DependencyChecker:
    """전역 의존성 체커 인스턴스를 반환합니다."""
    return DependencyChecker()