"""
프롬프트 관리를 위한 관리자 페이지입니다.

관리자가 프롬프트를 생성, 수정, 삭제하고 기능에 매핑할 수 있는 인터페이스를 제공합니다.
"""
import streamlit as st
from src.core.app_factory import get_application
from src.components.prompt_admin_ui import PromptAdminUI
from src.core.error_handler import handle_errors, create_streamlit_error_ui, get_error_handler


@handle_errors(show_user_message=True, reraise=False)
def main():
    """프롬프트 관리 페이지의 메인 함수입니다."""
    # 페이지 설정
    st.set_page_config(
        page_title="프롬프트 관리 - 관리자",
        page_icon="🎯",
        layout="wide"
    )
    
    # 애플리케이션 컨텍스트 초기화
    try:
        app_context = get_application()
    except Exception as e:
        st.error("애플리케이션 초기화에 실패했습니다.")
        create_streamlit_error_ui(
            get_error_handler().handle_error(e)
        )
        st.stop()
    
    # 프롬프트 서비스 가져오기
    prompt_service = app_context.get_service('prompt_service')
    if not prompt_service:
        st.error("프롬프트 서비스를 사용할 수 없습니다.")
        st.info("설정에서 프롬프트 관리 기능이 활성화되어 있는지 확인하세요.")
        st.stop()
    
    # 페이지 헤더
    st.title("🎯 프롬프트 관리 시스템")
    st.caption("LLM 프롬프트를 관리하고 애플리케이션 기능에 연결합니다.")
    
    # 사이드바에 서비스 상태 표시
    with st.sidebar:
        st.header("🔧 시스템 상태")
        
        # 프롬프트 서비스 상태
        if prompt_service:
            st.success("✅ 프롬프트 서비스 활성화")
            
            # 기본 통계 표시
            all_prompts = prompt_service.list_prompts()
            active_prompts = len([p for p in all_prompts if p.status.value == "active"])
            
            st.metric("전체 프롬프트", len(all_prompts))
            st.metric("활성 프롬프트", active_prompts)
        else:
            st.error("❌ 프롬프트 서비스 비활성화")
        
        # 기능 레지스트리 상태 표시
        st.markdown("---")
        st.subheader("📋 기능 레지스트리")
        
        try:
            from src.core.prompt_feature_registry import get_prompt_feature_registry
            feature_registry = get_prompt_feature_registry()
            
            features = feature_registry.list_features()
            active_count = len([f for f in features if f.is_active])
            
            st.metric("등록된 기능", len(features))
            st.metric("활성 기능", active_count)
            
            # 기능 목록 표시
            for feature in features:
                status_text = "ACTIVE" if feature.is_active else "INACTIVE"
                st.write(f"• {feature.name}: {status_text}")
                
        except Exception as e:
            st.error(f"기능 레지스트리 조회 실패: {e}")
    
    # 메인 컨텐츠
    try:
        prompt_admin_ui = PromptAdminUI(prompt_service)
        prompt_admin_ui.render()
        
    except Exception as e:
        st.error("프롬프트 관리 UI 렌더링에 실패했습니다.")
        
        # 디버깅을 위한 상세 오류 정보 표시
        import traceback
        
        st.subheader("🔍 DEBUG: 디버깅 정보")
        st.text(f"오류 타입: {type(e).__name__}")
        st.text(f"오류 메시지: {str(e)}")
        
        # Full traceback 표시
        st.subheader("📋 TRACEBACK: 상세 추적 정보")
        full_traceback = traceback.format_exc()
        st.code(full_traceback, language="python")
        
        # 추가 시스템 정보
        st.subheader("💻 SYSTEM: 시스템 정보")
        import sys
        import platform
        st.text(f"Python 버전: {sys.version}")
        st.text(f"플랫폼: {platform.system()} {platform.version()}")
        st.text(f"인코딩: {sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else 'Unknown'}")
        
        # 기존 오류 처리도 함께 실행 (추가 정보용)
        with st.expander("기존 오류 처리 정보", expanded=False):
            try:
                error_info = get_error_handler().handle_error(e)
                create_streamlit_error_ui(error_info)
            except Exception as handler_error:
                st.error(f"오류 처리기에서도 오류 발생: {handler_error}")


if __name__ == "__main__":
    main()