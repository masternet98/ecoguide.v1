"""
폐기물 분류 관리 페이지

waste_types.json 파일의 등록/수정/삭제를 관리하는 관리자 페이지입니다.
"""
import streamlit as st
import json
from typing import Dict, Any, List
from src.components.base import BaseComponent
from src.domains.analysis.services.waste_classification_service import WasteClassificationService


class WasteTypesManagementComponent(BaseComponent):
    """폐기물 분류 관리 컴포넌트"""

    def __init__(self, app_context):
        super().__init__(app_context)
        self.waste_service = self.get_service('waste_classification_service')

    def render(self) -> None:
        """관리 페이지를 렌더링합니다."""
        if not self.waste_service:
            st.error("폐기물 분류 서비스를 로드할 수 없습니다.")
            return

        st.title("🗂️ 폐기물 분류 관리")
        st.markdown("---")

        # 탭 구성
        tab1, tab2, tab3, tab4 = st.tabs(["📊 현황", "➕ 추가", "✏️ 수정", "📈 통계"])

        with tab1:
            self._render_current_status()

        with tab2:
            self._render_add_section()

        with tab3:
            self._render_edit_section()

        with tab4:
            self._render_statistics()

    def _render_current_status(self) -> None:
        """현재 분류 현황을 표시합니다."""
        st.subheader("📋 현재 폐기물 분류 현황")

        categories = self.waste_service.get_all_categories()

        if not categories:
            st.warning("폐기물 분류 데이터가 없습니다.")
            return

        # 전체 개요
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("주분류 수", len(categories))
        with col2:
            total_subs = sum(len(cat.get('세분류', [])) for cat in categories.values())
            st.metric("세분류 수", total_subs)
        with col3:
            total_examples = sum(
                sum(len(sub.get('예시', [])) for sub in cat.get('세분류', []))
                for cat in categories.values()
            )
            st.metric("예시 수", total_examples)

        st.markdown("---")

        # 분류별 상세 정보
        for main_cat, data in categories.items():
            with st.expander(f"🗂️ {main_cat} ({len(data.get('세분류', []))}개 세분류)"):
                st.write(f"**설명**: {data.get('설명', '설명 없음')}")

                subcategories = data.get('세분류', [])
                if subcategories:
                    for i, sub in enumerate(subcategories):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.write(f"**{sub.get('명칭', '명칭 없음')}**")
                        with col2:
                            examples = sub.get('예시', [])
                            if examples:
                                st.write(f"예시: {', '.join(examples[:3])}")
                                if len(examples) > 3:
                                    st.caption(f"... 외 {len(examples)-3}개")
                            else:
                                st.caption("예시 없음")

    def _render_add_section(self) -> None:
        """새 분류 추가 섹션을 렌더링합니다."""
        st.subheader("➕ 새 분류 추가")

        # 주분류 추가
        st.markdown("### 새 주분류 추가")
        with st.form("add_main_category"):
            new_main_name = st.text_input("주분류명", placeholder="예: 새로운 분류")
            new_main_desc = st.text_area("설명", placeholder="이 분류에 대한 설명을 입력하세요")

            if st.form_submit_button("주분류 추가"):
                if new_main_name and new_main_desc:
                    categories = self.waste_service.get_all_categories()
                    if new_main_name not in categories:
                        categories[new_main_name] = {
                            "설명": new_main_desc,
                            "세분류": []
                        }
                        if self.waste_service.update_waste_types(categories):
                            st.success(f"'{new_main_name}' 주분류가 추가되었습니다!")
                            st.rerun()
                        else:
                            st.error("주분류 추가에 실패했습니다.")
                    else:
                        st.warning("이미 존재하는 주분류명입니다.")
                else:
                    st.warning("주분류명과 설명을 모두 입력해주세요.")

        st.markdown("---")

        # 세분류 추가
        st.markdown("### 세분류 추가")
        main_categories = self.waste_service.get_main_categories()

        if main_categories:
            with st.form("add_subcategory"):
                selected_main = st.selectbox("주분류 선택", main_categories)
                new_sub_name = st.text_input("세분류명", placeholder="예: 새로운 세분류")
                new_examples = st.text_area(
                    "예시 (줄바꿈으로 구분)",
                    placeholder="예시 1\n예시 2\n예시 3"
                )

                if st.form_submit_button("세분류 추가"):
                    if new_sub_name:
                        categories = self.waste_service.get_all_categories()
                        subcategories = categories[selected_main]['세분류']

                        # 중복 확인
                        existing_names = [sub.get('명칭') for sub in subcategories]
                        if new_sub_name not in existing_names:
                            examples_list = [ex.strip() for ex in new_examples.split('\n') if ex.strip()]

                            new_subcategory = {
                                "명칭": new_sub_name,
                                "예시": examples_list
                            }

                            subcategories.append(new_subcategory)

                            if self.waste_service.update_waste_types(categories):
                                st.success(f"'{selected_main}'에 '{new_sub_name}' 세분류가 추가되었습니다!")
                                st.rerun()
                            else:
                                st.error("세분류 추가에 실패했습니다.")
                        else:
                            st.warning("이미 존재하는 세분류명입니다.")
                    else:
                        st.warning("세분류명을 입력해주세요.")
        else:
            st.info("먼저 주분류를 추가해주세요.")

    def _render_edit_section(self) -> None:
        """기존 분류 수정 섹션을 렌더링합니다."""
        st.subheader("✏️ 분류 수정")

        main_categories = self.waste_service.get_main_categories()
        if not main_categories:
            st.info("수정할 분류가 없습니다.")
            return

        # 주분류 선택
        selected_main = st.selectbox("수정할 주분류 선택", ["선택하세요"] + main_categories, key="edit_main_select")

        if selected_main != "선택하세요":
            category_info = self.waste_service.get_classification_info(selected_main)

            st.markdown("### 주분류 정보 수정")
            with st.form("edit_main_category"):
                current_desc = category_info.get('description', '')
                new_desc = st.text_area("설명 수정", value=current_desc)

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("설명 수정"):
                        categories = self.waste_service.get_all_categories()
                        categories[selected_main]['설명'] = new_desc
                        if self.waste_service.update_waste_types(categories):
                            st.success("주분류 설명이 수정되었습니다!")
                            st.rerun()
                        else:
                            st.error("수정에 실패했습니다.")

                with col2:
                    if st.form_submit_button("🗑️ 주분류 삭제", type="secondary"):
                        categories = self.waste_service.get_all_categories()
                        del categories[selected_main]
                        if self.waste_service.update_waste_types(categories):
                            st.success(f"'{selected_main}' 주분류가 삭제되었습니다!")
                            st.rerun()
                        else:
                            st.error("삭제에 실패했습니다.")

            st.markdown("---")

            # 세분류 수정
            st.markdown("### 세분류 수정")
            subcategories = self.waste_service.get_subcategories(selected_main)

            if subcategories:
                for i, sub in enumerate(subcategories):
                    sub_name = sub.get('명칭', '')
                    examples = sub.get('예시', [])

                    with st.expander(f"✏️ {sub_name}"):
                        with st.form(f"edit_sub_{i}"):
                            new_sub_name = st.text_input("세분류명", value=sub_name)
                            examples_text = '\n'.join(examples)
                            new_examples_text = st.text_area("예시 (줄바꿈으로 구분)", value=examples_text)

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("수정"):
                                    categories = self.waste_service.get_all_categories()
                                    new_examples_list = [ex.strip() for ex in new_examples_text.split('\n') if ex.strip()]

                                    categories[selected_main]['세분류'][i] = {
                                        "명칭": new_sub_name,
                                        "예시": new_examples_list
                                    }

                                    if self.waste_service.update_waste_types(categories):
                                        st.success(f"'{sub_name}' 세분류가 수정되었습니다!")
                                        st.rerun()
                                    else:
                                        st.error("수정에 실패했습니다.")

                            with col2:
                                if st.form_submit_button("🗑️ 삭제", type="secondary"):
                                    categories = self.waste_service.get_all_categories()
                                    del categories[selected_main]['세분류'][i]

                                    if self.waste_service.update_waste_types(categories):
                                        st.success(f"'{sub_name}' 세분류가 삭제되었습니다!")
                                        st.rerun()
                                    else:
                                        st.error("삭제에 실패했습니다.")
            else:
                st.info("세분류가 없습니다.")

    def _render_statistics(self) -> None:
        """통계 정보를 표시합니다."""
        st.subheader("📈 분류 통계")

        stats = self.waste_service.get_statistics()

        # 전체 통계
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 주분류", stats['main_categories_count'])
        with col2:
            st.metric("총 세분류", stats['total_subcategories'])
        with col3:
            st.metric("총 예시", stats['total_examples'])

        st.markdown("---")

        # 분류별 상세 통계
        st.markdown("### 분류별 상세 통계")

        for detail in stats['categories_detail']:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 3])

            with col1:
                st.write(f"**{detail['main_category']}**")
            with col2:
                st.write(f"세분류: {detail['subcategories_count']}개")
            with col3:
                st.write(f"예시: {detail['examples_count']}개")
            with col4:
                st.caption(detail['description'][:50] + "..." if len(detail['description']) > 50 else detail['description'])

        # JSON 다운로드
        st.markdown("---")
        st.markdown("### 💾 데이터 백업")

        categories = self.waste_service.get_all_categories()
        if categories:
            json_str = json.dumps(categories, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSON 파일 다운로드",
                data=json_str,
                file_name="waste_types_backup.json",
                mime="application/json"
            )