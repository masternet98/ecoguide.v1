"""
프롬프트 관리를 위한 관리자 UI 컴포넌트입니다.

프롬프트 생성, 수정, 삭제 및 기능 매핑 관리를 위한 Streamlit UI를 제공합니다.
"""
import streamlit as st
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.app.core.prompt_types import PromptTemplate, PromptCategory, PromptStatus, FeaturePromptMapping
from src.domains.prompts.services.prompt_service import PromptService
from src.app.core.logger import get_logger


class PromptAdminUI:
    """프롬프트 관리 관리자 UI 클래스입니다."""
    
    def __init__(self, prompt_service: PromptService):
        """
        프롬프트 관리 UI를 초기화합니다.
        
        Args:
            prompt_service: 프롬프트 서비스 인스턴스
        """
        self.prompt_service = prompt_service
        self.logger = get_logger(__name__)
    
    def render(self):
        """프롬프트 관리 UI를 렌더링합니다."""
        st.header("🎯 프롬프트 관리")
        st.markdown("---")
        
        # 탭 메뉴
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📝 프롬프트 목록", 
            "➕ 프롬프트 생성", 
            "🔗 기능 매핑", 
            "🔧 기능 관리",
            "📊 통계"
        ])
        
        with tab1:
            self._render_prompt_list()
        
        with tab2:
            self._render_prompt_create()
        
        with tab3:
            self._render_feature_mapping()
        
        with tab4:
            self._render_feature_management()
        
        with tab5:
            self._render_statistics()
    
    def _render_prompt_list(self):
        """프롬프트 목록 UI를 렌더링합니다."""
        st.subheader("프롬프트 목록")
        
        # 필터링 옵션
        col1, col2, col3 = st.columns(3)
        
        with col1:
            category_filter = st.selectbox(
                "카테고리 필터",
                options=[None] + [cat.value for cat in PromptCategory],
                format_func=lambda x: "전체" if x is None else self._get_category_display_name(x)
            )
        
        with col2:
            status_filter = st.selectbox(
                "상태 필터",
                options=[None] + [status.value for status in PromptStatus],
                format_func=lambda x: "전체" if x is None else self._get_status_display_name(x)
            )
        
        with col3:
            search_query = st.text_input("검색", placeholder="이름, 설명, 태그로 검색...")
        
        # 프롬프트 조회
        if search_query:
            prompts = self.prompt_service.search_prompts(search_query)
        else:
            category_enum = PromptCategory(category_filter) if category_filter else None
            status_enum = PromptStatus(status_filter) if status_filter else None
            prompts = self.prompt_service.list_prompts(category=category_enum, status=status_enum)
        
        if not prompts:
            st.info("조건에 맞는 프롬프트가 없습니다.")
            return
        
        # 프롬프트 목록 표시
        for prompt in prompts:
            with st.expander(f"📝 {prompt.name} ({self._get_category_display_name(prompt.category.value)})"):
                self._render_prompt_detail(prompt)
    
    def _render_prompt_detail(self, prompt: PromptTemplate):
        """프롬프트 상세 정보를 렌더링합니다."""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**설명:** {prompt.description}")
            st.write(f"**상태:** {self._get_status_display_name(prompt.status.value)}")
            st.write(f"**생성자:** {prompt.created_by}")
            st.write(f"**생성일:** {prompt.created_at.strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**수정일:** {prompt.updated_at.strftime('%Y-%m-%d %H:%M')}")
            
            if prompt.tags:
                st.write(f"**태그:** {', '.join(prompt.tags)}")
            
            if prompt.variables:
                st.write(f"**변수:** {', '.join(prompt.variables)}")
        
        with col2:
            # 편집 버튼
            if st.button(f"✏️ 편집", key=f"edit_{prompt.id}"):
                st.session_state.editing_prompt = prompt.id
            
            # 삭제 버튼
            if st.button(f"🗑️ 삭제", key=f"delete_{prompt.id}"):
                if st.session_state.get(f"confirm_delete_{prompt.id}", False):
                    self.prompt_service.delete_prompt(prompt.id)
                    st.success(f"프롬프트 '{prompt.name}'이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{prompt.id}"] = True
                    st.warning("삭제를 확인하려면 다시 클릭하세요.")
        
        # 프롬프트 템플릿 표시
        st.text_area(
            "프롬프트 템플릿",
            value=prompt.template,
            height=100,
            disabled=True,
            key=f"template_view_{prompt.id}"
        )
        
        # 편집 모드
        if st.session_state.get("editing_prompt") == prompt.id:
            self._render_prompt_edit(prompt)
    
    def _render_prompt_edit(self, prompt: PromptTemplate):
        """프롬프트 편집 UI를 렌더링합니다."""
        st.markdown("---")
        st.subheader("✏️ 프롬프트 편집")
        
        with st.form(f"edit_prompt_{prompt.id}"):
            # 편집 가능한 필드들
            new_name = st.text_input("프롬프트 이름", value=prompt.name)
            new_description = st.text_area("설명", value=prompt.description)
            
            new_status = st.selectbox(
                "상태",
                options=[status.value for status in PromptStatus],
                index=list(PromptStatus).index(prompt.status),
                format_func=self._get_status_display_name
            )
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.form_submit_button("📝 대형폐기물 예시 적용"):
                    new_template_value = self._get_enhanced_waste_template()
                else:
                    new_template_value = prompt.template

            new_template = st.text_area(
                "프롬프트 템플릿",
                value=new_template_value,
                height=250,
                help="변수는 {변수명} 형태로 사용하세요."
            )
            
            new_tags = st.text_input(
                "태그 (쉼표로 구분)",
                value=", ".join(prompt.tags)
            )
            
            # 메타데이터 편집
            metadata_json = st.text_area(
                "메타데이터 (JSON)",
                value=json.dumps(prompt.metadata, ensure_ascii=False, indent=2),
                height=100
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("💾 저장"):
                    try:
                        # 메타데이터 파싱
                        new_metadata = json.loads(metadata_json) if metadata_json.strip() else {}
                        
                        # 태그 파싱
                        parsed_tags = [tag.strip() for tag in new_tags.split(",") if tag.strip()]
                        
                        # 프롬프트 업데이트
                        updated_prompt = self.prompt_service.update_prompt(
                            prompt.id,
                            name=new_name,
                            description=new_description,
                            status=PromptStatus(new_status),
                            template=new_template,
                            tags=parsed_tags,
                            metadata=new_metadata
                        )
                        
                        if updated_prompt:
                            st.success("프롬프트가 성공적으로 수정되었습니다.")
                            del st.session_state.editing_prompt
                            st.rerun()
                        else:
                            st.error("프롬프트 수정에 실패했습니다.")
                    
                    except json.JSONDecodeError:
                        st.error("메타데이터 JSON 형식이 올바르지 않습니다.")
                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {e}")
            
            with col2:
                if st.form_submit_button("❌ 취소"):
                    del st.session_state.editing_prompt
                    st.rerun()
    
    def _render_prompt_create(self):
        """프롬프트 생성 UI를 렌더링합니다."""
        st.subheader("새 프롬프트 생성")

        # 예시 적용 버튼 (폼 외부)
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("📝 대형폐기물 분석 예시 적용", key="apply_example_outside_form"):
                st.session_state['waste_template_applied'] = True
                st.session_state['applied_template'] = self._get_enhanced_waste_template()
                st.session_state['suggested_name'] = "향상된 대형폐기물 분석"
                st.session_state['suggested_description'] = "인천광역시 서구 지역의 대형폐기물 배출을 위한 정밀 이미지 분석"
                st.session_state['suggested_tags'] = "폐기물분류, 인천서구, 대형폐기물, 정밀분석, JSON응답"
                st.success("대형폐기물 분석 프롬프트 예시가 적용되었습니다!")
        
        with st.form("create_prompt"):
            # 기본 정보
            name = st.text_input(
                "프롬프트 이름*",
                value=st.session_state.get('suggested_name', ''),
                placeholder="예: 이미지 객체 분석"
            )
            description = st.text_area(
                "설명*",
                value=st.session_state.get('suggested_description', ''),
                placeholder="이 프롬프트의 용도를 설명하세요."
            )

            category = st.selectbox(
                "카테고리*",
                options=[cat.value for cat in PromptCategory],
                index=3 if st.session_state.get('waste_template_applied') else 0,  # waste_classification 선택
                format_func=self._get_category_display_name
            )

            # 프롬프트 템플릿
            template = st.text_area(
                "프롬프트 템플릿*",
                value=st.session_state.get('applied_template', ''),
                height=300,
                placeholder="프롬프트 내용을 입력하세요. 변수는 {변수명} 형태로 사용하세요.",
                help="위의 '대형폐기물 분석 예시 적용' 버튼을 클릭하면 개선된 프롬프트가 입력됩니다."
            )

            # 선택적 정보
            tags = st.text_input(
                "태그 (쉼표로 구분)",
                value=st.session_state.get('suggested_tags', ''),
                placeholder="예: 객체인식, 크기분석, 분류"
            )
            
            created_by = st.text_input("생성자", value="admin")
            
            # 메타데이터
            metadata_json = st.text_area(
                "메타데이터 (JSON, 선택사항)",
                placeholder='{"model": "gpt-4o", "temperature": 0.7}',
                height=100
            )
            
            if st.form_submit_button("🎯 프롬프트 생성"):
                if not all([name, description, template]):
                    st.error("필수 필드를 모두 입력해주세요.")
                    return
                
                try:
                    # 메타데이터 파싱
                    metadata = json.loads(metadata_json) if metadata_json.strip() else {}
                    
                    # 태그 파싱
                    parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
                    
                    # 프롬프트 생성
                    new_prompt = self.prompt_service.create_prompt(
                        name=name,
                        description=description,
                        category=PromptCategory(category),
                        template=template,
                        created_by=created_by,
                        tags=parsed_tags,
                        metadata=metadata
                    )
                    
                    st.success(f"프롬프트 '{new_prompt.name}'이 성공적으로 생성되었습니다!")

                    # 변수 정보 표시
                    if new_prompt.variables:
                        st.info(f"감지된 변수: {', '.join(new_prompt.variables)}")

                    # 세션 상태 정리
                    for key in ['waste_template_applied', 'applied_template', 'suggested_name', 'suggested_description', 'suggested_tags']:
                        if key in st.session_state:
                            del st.session_state[key]
                
                except json.JSONDecodeError:
                    st.error("메타데이터 JSON 형식이 올바르지 않습니다.")
                except Exception as e:
                    st.error(f"프롬프트 생성 중 오류가 발생했습니다: {e}")
    
    def _render_feature_mapping(self):
        """기능 매핑 UI를 렌더링합니다."""
        st.subheader("기능-프롬프트 매핑 관리")
        
        # 동적 기능 목록 조회 (프롬프트 기능 레지스트리에서 가져옴)
        from src.app.core.prompt_feature_registry import get_prompt_feature_registry
        
        feature_registry = get_prompt_feature_registry()
        available_features = feature_registry.get_feature_ids(active_only=True)
        
        # 현재 매핑 표시
        st.write("**현재 매핑 상태:**")
        
        if not available_features:
            st.warning("활성화된 기능이 없습니다. 기능 레지스트리를 확인해주세요.")
            return
        
        for feature_id in available_features:
            # 기능 정보 조회
            feature_info = feature_registry.get_feature_display_info(feature_id)
            prompts = self.prompt_service.get_prompts_for_feature(feature_id)
            default_prompt = self.prompt_service.get_default_prompt_for_feature(feature_id)
            
            # 기능명과 설명을 포함한 확장 가능한 섹션
            with st.expander(f"🔧 {feature_info['name']} ({feature_id})"):
                # 기능 설명 표시
                st.markdown(f"**설명:** {feature_info['description']}")
                st.markdown(f"**카테고리:** {feature_info['category']}")
                if feature_info.get('required_services') and feature_info['required_services'] != "없음":
                    st.markdown(f"**필요 서비스:** {feature_info['required_services']}")
                
                st.markdown("---")
                
                if prompts:
                    st.markdown("**매핑된 프롬프트:**")
                    for i, prompt in enumerate(prompts):
                        is_default = default_prompt and prompt.id == default_prompt.id
                        status_icon = "[기본]" if is_default else "[매핑]"
                        
                        # 프롬프트 기본 정보
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{status_icon} **{prompt.name}** ({prompt.category.value})")
                            if is_default:
                                st.caption("🔹 기본 프롬프트")
                        
                        with col2:
                            # 매핑 제거 버튼
                            if st.button(f"🗑️ 제거", key=f"remove_{feature_id}_{prompt.id}"):
                                success = self.prompt_service.unmap_feature_from_prompt(feature_id, prompt.id)
                                if success:
                                    st.success(f"매핑이 제거되었습니다.")
                                    st.rerun()
                                else:
                                    st.error("매핑 제거에 실패했습니다.")
                        
                        # 프롬프트 내용 표시 (접을 수 있는 형태)
                        with st.expander(f"📄 프롬프트 내용 보기"):
                            st.markdown(f"**설명:** {prompt.description}")
                            st.markdown("**프롬프트 템플릿:**")
                            st.code(prompt.template, language="text")
                            
                            if prompt.variables:
                                st.markdown(f"**변수:** {', '.join(prompt.variables)}")
                            
                            if prompt.tags:
                                st.markdown(f"**태그:** {', '.join(prompt.tags)}")
                        
                        st.markdown("---")
                else:
                    st.info("매핑된 프롬프트가 없습니다.")
        
        st.markdown("---")
        
        # 새 매핑 추가
        st.write("**새 매핑 추가:**")
        
        with st.form("add_mapping"):
            # 기능 선택을 위한 옵션 생성 (표시명 포함)
            feature_options = {}
            for feature_id in available_features:
                feature_info = feature_registry.get_feature_display_info(feature_id)
                display_text = f"{feature_info['name']} ({feature_id}) - {feature_info['category']}"
                feature_options[feature_id] = display_text
            
            selected_feature = st.selectbox(
                "기능 선택", 
                options=list(feature_options.keys()),
                format_func=lambda x: feature_options[x]
            )
            
            # 활성 프롬프트 목록
            active_prompts = self.prompt_service.list_prompts(status=PromptStatus.ACTIVE)
            
            if active_prompts:
                prompt_options = {p.id: f"{p.name} ({p.category.value})" for p in active_prompts}
                selected_prompt_id = st.selectbox(
                    "프롬프트 선택",
                    options=list(prompt_options.keys()),
                    format_func=lambda x: prompt_options[x]
                )
                
                is_default = st.checkbox("기본 프롬프트로 설정")
                priority = st.number_input("우선순위", min_value=0, value=0, help="낮은 숫자가 높은 우선순위")
                
                if st.form_submit_button("🔗 매핑 추가"):
                    success = self.prompt_service.map_feature_to_prompt(
                        feature_id=selected_feature,
                        prompt_id=selected_prompt_id,
                        is_default=is_default,
                        priority=priority
                    )
                    
                    if success:
                        st.success("매핑이 성공적으로 추가되었습니다!")
                        st.rerun()
                    else:
                        st.error("매핑 추가에 실패했습니다.")
            else:
                st.warning("활성화된 프롬프트가 없습니다. 먼저 프롬프트를 생성하세요.")
    
    def _render_feature_management(self):
        """기능 관리 UI를 렌더링합니다."""
        st.subheader("기능 관리")
        st.markdown("프롬프트 기능을 추가, 수정, 삭제할 수 있습니다.")
        
        from src.app.core.prompt_feature_registry import get_prompt_feature_registry
        from src.app.core.prompt_feature_manager import get_prompt_feature_manager
        
        feature_registry = get_prompt_feature_registry()
        feature_manager = get_prompt_feature_manager()
        
        # 기능 목록 표시
        st.write("**현재 등록된 기능:**")
        
        features = feature_registry.list_features(active_only=False)
        
        if not features:
            st.info("등록된 기능이 없습니다.")
        else:
            for feature in features:
                with st.expander(f"🔧 {feature.name} ({feature.feature_id})", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**설명:** {feature.description}")
                        st.markdown(f"**카테고리:** {feature.category}")
                        st.markdown(f"**상태:** {'활성' if feature.is_active else '비활성'}")
                        
                        if feature.required_services:
                            st.markdown(f"**필요 서비스:** {', '.join(feature.required_services)}")
                        
                        if feature.default_prompt_template:
                            st.markdown("**기본 프롬프트 템플릿:**")
                            st.code(feature.default_prompt_template[:200] + "..." if len(feature.default_prompt_template) > 200 else feature.default_prompt_template, language="text")
                    
                    with col2:
                        # 활성화/비활성화 토글
                        current_status = feature.is_active
                        new_status = st.toggle(
                            "활성화",
                            value=current_status,
                            key=f"toggle_{feature.feature_id}"
                        )
                        
                        if new_status != current_status:
                            if new_status:
                                success = feature_manager.activate_feature(feature.feature_id)
                            else:
                                success = feature_manager.deactivate_feature(feature.feature_id)
                            
                            if success:
                                st.success("상태가 변경되었습니다.")
                                st.rerun()
                            else:
                                st.error("상태 변경에 실패했습니다.")
                        
                        # 기능 삭제 버튼
                        if st.button(f"🗑️ 삭제", key=f"delete_feature_{feature.feature_id}"):
                            if st.session_state.get(f"confirm_delete_feature_{feature.feature_id}", False):
                                success = feature_registry.unregister_feature(feature.feature_id)
                                if success:
                                    st.success(f"기능 '{feature.name}'이 삭제되었습니다.")
                                    st.rerun()
                                else:
                                    st.error("기능 삭제에 실패했습니다.")
                            else:
                                st.session_state[f"confirm_delete_feature_{feature.feature_id}"] = True
                                st.warning("삭제를 확인하려면 다시 클릭하세요.")
        
        st.markdown("---")
        
        # 새 기능 추가
        st.write("**새 기능 추가:**")
        
        with st.form("add_new_feature"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_feature_id = st.text_input("기능 ID*", placeholder="예: custom_analysis")
                new_feature_name = st.text_input("기능 이름*", placeholder="예: 맞춤형 분석")
                new_feature_category = st.selectbox(
                    "카테고리*",
                    options=["analysis", "input", "output", "processing", "interface", "management", "custom"],
                    index=6
                )
            
            with col2:
                new_feature_description = st.text_area(
                    "기능 설명*",
                    placeholder="이 기능이 무엇을 하는지 설명하세요...",
                    height=100
                )
                new_required_services = st.text_input(
                    "필요 서비스 (쉼표로 구분)",
                    placeholder="예: openai_service, vision_service"
                )
            
            new_default_template = st.text_area(
                "기본 프롬프트 템플릿",
                placeholder="이 기능에 사용할 기본 프롬프트 템플릿을 입력하세요...",
                height=100
            )
            
            if st.form_submit_button("🔧 기능 추가"):
                if not all([new_feature_id, new_feature_name, new_feature_description]):
                    st.error("필수 필드를 모두 입력해주세요.")
                else:
                    # 서비스 목록 파싱
                    services = [s.strip() for s in new_required_services.split(",") if s.strip()]
                    
                    # 기능 등록
                    success = feature_registry.register_feature(
                        feature_id=new_feature_id,
                        name=new_feature_name,
                        description=new_feature_description,
                        category=new_feature_category,
                        required_services=services,
                        default_prompt_template=new_default_template,
                        is_active=True
                    )
                    
                    if success:
                        st.success(f"기능 '{new_feature_name}'이 성공적으로 추가되었습니다!")
                        st.rerun()
                    else:
                        st.error("기능 추가에 실패했습니다.")
    
    def _render_statistics(self):
        """통계 UI를 렌더링합니다."""
        st.subheader("사용 통계")
        
        # 프롬프트 통계
        all_prompts = self.prompt_service.list_prompts()
        total_prompts = len(all_prompts)
        active_prompts = len([p for p in all_prompts if p.status == PromptStatus.ACTIVE])
        
        # 기능 레지스트리 통계
        from src.app.core.prompt_feature_registry import get_prompt_feature_registry
        feature_registry = get_prompt_feature_registry()
        feature_stats = feature_registry.get_statistics()
        
        # 프롬프트 통계
        st.write("**프롬프트 통계:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("전체 프롬프트", total_prompts)
        
        with col2:
            st.metric("활성 프롬프트", active_prompts)
        
        with col3:
            inactive_prompts = total_prompts - active_prompts
            st.metric("비활성 프롬프트", inactive_prompts)
        
        st.markdown("---")
        
        # 기능 레지스트리 통계
        st.write("**기능 레지스트리 통계:**")
        col4, col5, col6 = st.columns(3)
        
        with col4:
            st.metric("전체 기능", feature_stats['total_features'])
        
        with col5:
            st.metric("활성 기능", feature_stats['active_features'])
        
        with col6:
            st.metric("비활성 기능", feature_stats['inactive_features'])
        
        # 카테고리별 통계
        st.write("**프롬프트 카테고리별 분포:**")
        category_counts = {}
        for prompt in all_prompts:
            category = prompt.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in category_counts.items():
            st.write(f"• {self._get_category_display_name(category)}: {count}개")
        
        # 기능 카테고리별 통계
        if feature_stats['category_distribution']:
            st.write("**기능 카테고리별 분포:**")
            for category, count in feature_stats['category_distribution'].items():
                st.write(f"• {category}: {count}개")
        
        # 사용 통계 (사용 추적이 활성화된 경우)
        if self.prompt_service.config.usage_tracking_enabled:
            st.markdown("---")
            st.write("**사용 통계:**")
            
            usage_data = []
            for prompt in all_prompts:
                stats = self.prompt_service.get_usage_stats(prompt.id)
                if stats and stats.usage_count > 0:
                    usage_data.append({
                        'name': prompt.name,
                        'usage_count': stats.usage_count,
                        'last_used': stats.last_used.strftime('%Y-%m-%d %H:%M') if stats.last_used else 'N/A'
                    })
            
            if usage_data:
                # 사용량 순으로 정렬
                usage_data.sort(key=lambda x: x['usage_count'], reverse=True)
                
                for data in usage_data[:10]:  # 상위 10개만 표시
                    st.write(f"• {data['name']}: {data['usage_count']}회 (마지막: {data['last_used']})")
            else:
                st.info("사용 통계가 없습니다.")
    
    def _get_category_display_name(self, category_value: str) -> str:
        """카테고리 값을 표시용 이름으로 변환합니다."""
        category_names = {
            "vision_analysis": "이미지 분석",
            "object_detection": "객체 탐지",
            "size_estimation": "크기 추정",
            "waste_classification": "폐기물 분류",
            "general_analysis": "일반 분석",
            "custom": "사용자 정의"
        }
        return category_names.get(category_value, category_value)
    
    def _get_status_display_name(self, status_value: str) -> str:
        """상태 값을 표시용 이름으로 변환합니다."""
        status_names = {
            "active": "활성",
            "inactive": "비활성",
            "draft": "초안",
            "deprecated": "사용 중단"
        }
        return status_names.get(status_value, status_value)

    def _get_enhanced_waste_template(self) -> str:
        """개선된 대형폐기물 분석 프롬프트 템플릿을 반환합니다."""
        return '''당신은 인천광역시 서구 지역의 대형폐기물 배출 전문가입니다. 이미지에 있는 물체를 정밀 분석하여 적절한 폐기물 분류와 배출 안내를 제공해주세요.

### 분석 대상
이미지에서 가장 주요한 폐기물 대상을 식별하세요. 여러 물체가 있다면 가장 큰 물체나 중앙에 위치한 주요 물체를 우선 분석하세요.

### 분류 기준 (다음 카테고리 중 선택)
**가구**: 침대/매트리스, 소파, 거실장/테이블/서랍장, 옷장/붙박이장/장롱, 책상, 의자, 책장, 선반/수납가구, 화장대, 기타 가구

**가전**: 냉장고/냉동고, 세탁기/건조기, 에어컨, TV/모니터, 주방가전, 청소기, 컴퓨터/사무기기, 오디오, 기타 가전

**건강/의료용품**: 병원 침대, 휠체어/보행기, 재활/운동 보조기구, 기타 의료용품

**생활/주방용품**: 주방용품, 욕실/세면용품, 보관/정리 용품, 의류·침구류, 생활잡화, 유아용품, 기타 생활용품

**스포츠/레저**: 운동기구, 자전거/킥보드, 캠핑용품, 수상레저, 기타 레저용품

**악기**: 피아노, 전자건반, 현악기, 관악기, 타악기, 기타 악기

**조경/장식/행사용품**: 대형 화분/조경용품, 장식용 트리/조형물, 행사/무대 장비, 대형 오락기기, 기타 대형 장식품

**기타**: 공업/사업용, 건축자재, 전기설비, 환경설비, 특수폐기물, 분류불가

### 분석 항목
1. **물체 식별**: 정확한 물체명
2. **대분류**: 위 8개 카테고리 중 선택
3. **세분류**: 해당 카테고리의 구체적 하위 분류
4. **크기 추정**:
   - 소형 (가로/세로/높이 모두 50cm 미만)
   - 중형 (한 변이 50cm-150cm)
   - 대형 (한 변이 150cm 이상)
5. **재질**: 주요 재질 (목재, 금속, 플라스틱, 유리, 복합재료 등)
6. **상태**: 신품/양호/사용감있음/손상됨/부분파손
7. **배출 난이도**: 쉬움/보통/어려움 (크기, 무게, 해체 필요성 기준)

### 인천광역시 서구 특화 안내
- 대형폐기물은 인터넷 신고 후 배출
- 크기와 재질에 따라 수수료 차등 적용
- 가전제품은 무료 수거 가능한 품목도 있음

### 출력 형식 (JSON)
반드시 다음 JSON 형식으로만 응답하세요:

{
  "object_name": "구체적인 물체명",
  "category": "대분류명",
  "subcategory": "세분류명",
  "size": "소형/중형/대형",
  "material": "주요재질",
  "condition": "상태",
  "disposal_difficulty": "쉬움/보통/어려움",
  "estimated_dimensions": "예상 크기 (가로×세로×높이 cm)",
  "incheon_seogu_notes": "인천 서구 지역 특화 배출 안내",
  "confidence": "0.0-1.0 (분석 신뢰도)"
}

### 주의사항
- JSON 외의 다른 텍스트는 포함하지 마세요
- 분석이 어려운 경우 "분류불가"로 처리하고 confidence를 낮게 설정하세요
- 크기 추정 시 배경의 일반적인 물체들(손, 가구 등)을 참고하여 비례적으로 계산하세요'''