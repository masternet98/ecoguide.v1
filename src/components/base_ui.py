"""
기본 UI 컴포넌트들을 제공하는 모듈입니다.
확장 가능한 컴포넌트 아키텍처의 기반을 제공합니다.
"""
import streamlit as st
from typing import Optional, Dict, Any, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class UIComponent:
    """UI 컴포넌트의 기본 구조를 정의합니다."""
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    enabled: bool = True


class BaseUIComponent(ABC):
    """모든 UI 컴포넌트의 기본 클래스입니다."""
    
    def __init__(self, component_info: UIComponent):
        self.info = component_info
        self.state_prefix = f"{self.__class__.__name__.lower()}_"
    
    @abstractmethod
    def render(self, **kwargs) -> Any:
        """컴포넌트를 렌더링합니다."""
        pass
    
    def is_enabled(self) -> bool:
        """컴포넌트가 활성화되어 있는지 확인합니다."""
        return self.info.enabled
    
    def get_state_key(self, key: str) -> str:
        """세션 상태 키를 생성합니다."""
        return f"{self.state_prefix}{key}"
    
    def set_state(self, key: str, value: Any) -> None:
        """세션 상태에 값을 저장합니다."""
        st.session_state[self.get_state_key(key)] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """세션 상태에서 값을 가져옵니다."""
        return st.session_state.get(self.get_state_key(key), default)


class ImageInputComponent(BaseUIComponent):
    """이미지 입력을 처리하는 컴포넌트입니다."""
    
    def __init__(self):
        super().__init__(UIComponent(
            title="이미지 입력",
            description="카메라 촬영 또는 갤러리에서 이미지를 선택합니다",
            icon="📷"
        ))
    
    def render(self, tab_options: List[str] = None) -> Optional[bytes]:
        """이미지 입력 인터페이스를 렌더링합니다."""
        if tab_options is None:
            tab_options = ["📷 카메라", "🖼️ 갤러리"]
        
        # 탭 선택
        selected_tab = st.radio(
            "이미지 입력 방법", 
            tab_options, 
            index=self.get_state("selected_tab_index", 0),
            key=self.get_state_key("tab_selector")
        )
        
        # 탭 인덱스 저장
        self.set_state("selected_tab_index", tab_options.index(selected_tab))
        
        # 선택된 탭에 따른 입력 방법
        if selected_tab == "📷 카메라":
            return self._render_camera_input()
        elif selected_tab == "🖼️ 갤러리":
            return self._render_gallery_input()
        
        return None
    
    def _render_camera_input(self) -> Optional[bytes]:
        """카메라 입력을 렌더링합니다."""
        st.info("아래 카메라 버튼으로 사진을 촬영하세요.")
        
        camera_photo = st.camera_input(
            "사진 촬영", 
            key=self.get_state_key("camera_input")
        )
        
        if camera_photo:
            image_bytes = camera_photo.getvalue()
            self.set_state("current_image", image_bytes)
            self.set_state("image_source", "camera")
            return image_bytes
        
        return self.get_state("current_image")
    
    def _render_gallery_input(self) -> Optional[bytes]:
        """갤러리 입력을 렌더링합니다."""
        gallery_photo = st.file_uploader(
            "사진 파일을 업로드하세요",
            type=["png", "jpg", "jpeg"],
            key=self.get_state_key("gallery_uploader")
        )
        
        if gallery_photo:
            image_bytes = gallery_photo.getvalue()
            self.set_state("current_image", image_bytes)
            self.set_state("image_source", "gallery")
            return image_bytes
        
        return self.get_state("current_image")


class AnalysisResultComponent(BaseUIComponent):
    """분석 결과를 표시하는 컴포넌트입니다."""
    
    def __init__(self):
        super().__init__(UIComponent(
            title="분석 결과",
            description="AI 이미지 분석 결과를 표시합니다",
            icon="📊"
        ))
    
    def render(self, result_data: Dict[str, Any]) -> None:
        """분석 결과를 렌더링합니다."""
        if not result_data:
            st.info("분석 결과가 없습니다.")
            return
        
        st.subheader(f"{self.info.icon} {self.info.title}")
        
        # 구조화된 결과 표시
        output_text = result_data.get("output_text")
        raw_response = result_data.get("raw_response")
        
        if output_text:
            self._render_structured_result(output_text)
        else:
            st.info("모델에서 직접적인 텍스트 응답을 찾지 못했습니다.")
        
        # 원시 응답 표시
        self._render_raw_response(raw_response)
    
    def _render_structured_result(self, output_text: str) -> None:
        """구조화된 결과를 표시합니다."""
        try:
            import json
            parsed_output = json.loads(output_text)
            
            # 객체 정보 표시
            object_name = parsed_output.get("object", "알 수 없음")
            category = parsed_output.get("category", "알 수 없음")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("인식된 물체", object_name)
            with col2:
                st.metric("카테고리", category)
            
            # 추가 정보가 있으면 표시
            for key, value in parsed_output.items():
                if key not in ["object", "category"]:
                    st.write(f"**{key}:** {value}")
                    
        except json.JSONDecodeError:
            st.warning("⚠️ JSON 형식이 아닌 응답입니다.")
            st.write(output_text)
        except Exception as e:
            st.error(f"응답 처리 중 오류 발생: {e}")
            st.write(output_text)
    
    def _render_raw_response(self, raw_response: Any) -> None:
        """원시 응답을 표시합니다."""
        with st.expander("🔍 원시 응답(JSON) 보기"):
            try:
                st.json(raw_response)
            except Exception:
                st.code(str(raw_response))


class SettingsSidebarComponent(BaseUIComponent):
    """설정 사이드바 컴포넌트입니다."""
    
    def __init__(self):
        super().__init__(UIComponent(
            title="설정",
            description="애플리케이션 설정을 관리합니다",
            icon="⚙️"
        ))
    
    def render(self, app_context, config) -> Dict[str, Any]:
        """설정 사이드바를 렌더링합니다."""
        with st.sidebar:
            st.header(f"{self.info.icon} {self.info.title}")
            
            # 모델 선택
            model = st.selectbox(
                "모델 선택", 
                options=config.vision_models, 
                index=0,
                key=self.get_state_key("model_selector")
            )
            
            # 서비스 상태 표시
            self._display_service_status(app_context)
            
            # 기능 상태 표시
            self._display_feature_status(app_context)
            
            return {
                "selected_model": model,
                "app_context": app_context
            }
    
    def _display_service_status(self, app_context) -> None:
        """서비스 상태를 표시합니다."""
        st.subheader("🔌 서비스 상태")
        
        try:
            openai_service = app_context.get_service('openai_service')
            
            if openai_service and openai_service.is_ready():
                if openai_service.has_api_key():
                    st.success("✅ OpenAI API 키가 설정되었습니다")
                else:
                    st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다")
                    st.info("환경변수 또는 Streamlit secrets에 OPENAI_API_KEY를 설정하세요")
            else:
                st.error("❌ OpenAI 서비스를 초기화할 수 없습니다")
        except Exception as e:
            st.error(f"서비스 상태 확인 실패: {e}")
    
    def _display_feature_status(self, app_context) -> None:
        """기능 상태를 표시합니다."""
        with st.expander("🔧 기능 상태"):
            features = app_context.feature_registry.list_features()
            
            for feature in features:
                status_emoji = "✅" if feature.status.value == "enabled" else "⏸️"
                st.write(f"{status_emoji} {feature.display_name}: {feature.status.value}")
                
                if feature.error_message:
                    st.error(f"오류: {feature.error_message}")


class AnalysisControlComponent(BaseUIComponent):
    """분석 제어 컴포넌트입니다."""
    
    def __init__(self):
        super().__init__(UIComponent(
            title="분석 제어",
            description="이미지 분석 옵션과 실행을 제어합니다",
            icon="🧠"
        ))
    
    def render(self, config, on_analyze: Callable = None) -> Dict[str, Any]:
        """분석 제어 인터페이스를 렌더링합니다."""
        st.subheader(f"{self.info.icon} {self.info.title}")
        
        # 분석 옵션
        col1, col2 = st.columns(2)
        
        with col1:
            max_size = st.number_input(
                "최대 변환 크기 (긴 변, px)",
                min_value=480,
                max_value=1280,
                value=config.max_image_size,
                step=64,
                key=self.get_state_key("max_size")
            )
        
        with col2:
            analyze_button = st.button(
                "🧠 이미지 분석",
                use_container_width=True,
                key=self.get_state_key("analyze_button")
            )
        
        # 분석 실행
        if analyze_button and on_analyze:
            return {
                "should_analyze": True,
                "max_size": max_size
            }
        
        return {
            "should_analyze": False,
            "max_size": max_size
        }