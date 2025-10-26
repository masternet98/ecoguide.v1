"""
관리자용 라벨링 데이터 대시보드

학습 데이터로 저장된 이미지와 라벨 정보를 분류별로 조회하고 관리하는 페이지입니다.
"""

import streamlit as st
from pathlib import Path
import json
from PIL import Image
from datetime import datetime
import logging

from src.app.core.app_factory import get_application
from src.app.core.error_handler import handle_errors, create_streamlit_error_ui, get_error_handler

logger = logging.getLogger(__name__)


@handle_errors(show_user_message=True, reraise=False)
def main():
    """라벨링 데이터 대시보드 메인 페이지"""
    # 페이지 설정
    st.set_page_config(
        page_title="EcoGuide.v1 - 라벨링 데이터 관리",
        page_icon="📊",
        layout="wide"
    )

    # 애플리케이션 컨텍스트 초기화
    try:
        app_context = get_application()
    except Exception as e:
        st.error("애플리케이션 초기화에 실패했습니다.")
        create_streamlit_error_ui(get_error_handler().handle_error(e))
        return

    st.title("📊 라벨링 데이터 관리 대시보드")
    st.markdown("학습 데이터로 수집된 이미지와 분류 정보를 조회하고 관리합니다.")
    st.markdown("---")

    # 라벨링 서비스 초기화
    labeling_service = app_context.get_service('labeling_service')
    if not labeling_service:
        st.error("라벨링 서비스를 초기화할 수 없습니다.")
        return

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📈 통계", "🏷️ 데이터 조회", "📋 상세 정보", "🗑️ 데이터 삭제"])

    with tab1:
        _render_statistics(labeling_service)

    with tab2:
        _render_data_browser(labeling_service)

    with tab3:
        _render_details(labeling_service)

    with tab4:
        _render_deletion(labeling_service)


def _render_statistics(labeling_service) -> None:
    """라벨링 통계를 표시합니다."""
    st.subheader("📈 라벨링 통계")

    try:
        stats = labeling_service.get_category_statistics()

        # 전체 통계
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "총 라벨링 데이터",
                stats['total_labels'],
                help="저장된 전체 라벨링 데이터 개수"
            )

        with col2:
            st.metric(
                "마지막 업데이트",
                datetime.fromisoformat(stats['last_updated']).strftime("%Y-%m-%d %H:%M:%S"),
                help="라벨링 데이터 마지막 저장 시간"
            )

        st.markdown("---")

        # 카테고리별 통계
        st.markdown("### 주 카테고리별 현황")

        category_names = {
            'FURN': '가구',
            'APPL': '가전',
            'HLTH': '건강/의료용품',
            'LIFE': '생활/주방용품',
            'SPOR': '스포츠/레저',
            'MUSC': '악기',
            'HOBB': '조경/장식',
            'MISC': '기타'
        }

        # 카테고리별 데이터 표 생성
        category_data = []
        by_category = stats.get('by_primary_category', {})

        for cat_code, cat_info in by_category.items():
            cat_name = category_names.get(cat_code, cat_code)
            category_data.append({
                '분류코드': cat_code,
                '분류명': cat_name,
                '라벨 개수': cat_info['count'],
                '세부 카테고리': len(cat_info.get('subcategories', {}))
            })

        if category_data:
            st.dataframe(
                category_data,
                use_container_width=True,
                hide_index=True
            )

            # 막대 그래프
            import pandas as pd
            df = pd.DataFrame(category_data)
            st.bar_chart(df.set_index('분류명')['라벨 개수'])
        else:
            st.info("아직 라벨링된 데이터가 없습니다.")

    except Exception as e:
        st.error(f"통계 조회 실패: {e}")
        logger.error(f"Failed to load statistics: {e}", exc_info=True)


def _render_data_browser(labeling_service) -> None:
    """라벨링 데이터를 분류별로 조회합니다."""
    st.subheader("🏷️ 라벨링 데이터 조회")

    try:
        stats = labeling_service.get_category_statistics()
        by_category = stats.get('by_primary_category', {})

        if not by_category:
            st.info("아직 라벨링된 데이터가 없습니다.")
            return

        category_names = {
            'FURN': '가구',
            'APPL': '가전',
            'HLTH': '건강/의료용품',
            'LIFE': '생활/주방용품',
            'SPOR': '스포츠/레저',
            'MUSC': '악기',
            'HOBB': '조경/장식',
            'MISC': '기타'
        }

        # 주 카테고리 선택
        primary_options = {}
        total_count = 0
        for cat_code, cat_info in by_category.items():
            cat_name = category_names.get(cat_code, cat_code)
            primary_options[cat_code] = f"{cat_name} ({cat_info['count']}개)"
            total_count += cat_info['count']

        col1, col2 = st.columns(2)

        with col1:
            # 전체 옵션을 포함한 선택지 구성
            primary_select_options = [""] + list(primary_options.keys())
            selected_primary = st.selectbox(
                "주 카테고리 선택",
                options=primary_select_options,
                format_func=lambda x: f"전체 ({total_count}개)" if x == "" else primary_options[x],
                key="primary_category_select"
            )

        # 세부 카테고리 선택 (주 카테고리가 선택되었을 때만 표시)
        with col2:
            if selected_primary:
                subcategories = by_category[selected_primary].get('subcategories', {})
                sub_options = {k: f"{k} ({v}개)" for k, v in subcategories.items()}

                selected_secondary = st.selectbox(
                    "세부 카테고리 선택 (선택사항)",
                    options=[""] + list(sub_options.keys()),
                    format_func=lambda x: "전체" if x == "" else sub_options.get(x, x),
                    key="secondary_category_select"
                )
            else:
                st.selectbox(
                    "세부 카테고리 선택 (선택사항)",
                    options=[""],
                    format_func=lambda x: "전체 카테고리 선택 시 사용 가능",
                    key="secondary_category_select",
                    disabled=True
                )
                selected_secondary = ""

        st.markdown("---")

        # 데이터 로드 및 표시
        if selected_primary == "":
            # 전체 카테고리의 모든 라벨 조회
            labels = []
            for cat_code in by_category.keys():
                labels.extend(labeling_service.get_labels_by_primary_category(cat_code))
        elif selected_secondary:
            labels = labeling_service.get_labels_by_secondary_category(
                selected_primary, selected_secondary
            )
        else:
            labels = labeling_service.get_labels_by_primary_category(selected_primary)

        if not labels:
            st.warning("선택한 분류에 라벨링 데이터가 없습니다.")
            return

        st.markdown(f"### {len(labels)}개의 라벨링 데이터")

        # 이미지와 정보를 그리드로 표시
        cols = st.columns(3)
        for idx, label in enumerate(labels):
            col = cols[idx % 3]

            with col:
                # 컨테이너 생성 (카드 스타일)
                with st.container(border=True):
                    # 이미지 표시
                    image_path = label['image_path']
                    try:
                        img = Image.open(image_path)
                        st.image(img, use_container_width=True)
                    except Exception as e:
                        st.warning(f"이미지를 불러올 수 없습니다: {e}")

                    # 정보 표시
                    st.markdown("**📌 정보:**")
                    st.markdown(f"**물품**: {label['classification']['object_name']}")
                    st.markdown(f"**분류**: {label['classification']['primary_category_name']}")
                    st.markdown(f"**세분류**: {label['classification']['secondary_category']}")
                    st.markdown(f"**신뢰도**: {label['confidence']:.0%}")

                    # 크기 정보 표시
                    dimensions = label.get('dimensions', {})
                    if any(dimensions.values()):
                        st.markdown("**📏 크기:**")
                        size_info = []
                        w_val = dimensions.get('w_cm') or dimensions.get('width_cm')
                        h_val = dimensions.get('h_cm') or dimensions.get('height_cm')
                        d_val = dimensions.get('d_cm') or dimensions.get('depth_cm')

                        if w_val:
                            size_info.append(f"가로(W): {w_val}cm")
                        if h_val:
                            size_info.append(f"높이(H): {h_val}cm")
                        if d_val:
                            size_info.append(f"깊이(D): {d_val}cm")
                        if size_info:
                            st.caption(" / ".join(size_info))

                    # 사용자 피드백 표시
                    user_feedback = label.get('user_feedback', {})
                    if user_feedback and user_feedback.get('notes'):
                        st.markdown("**💬 사용자 의견:**")
                        st.caption(user_feedback['notes'])

                    # UUID 전체 표시 (복사 가능)
                    st.markdown("**🔑 파일 ID:**")
                    st.code(label['file_id'], language="text")

                    # 버튼 그룹
                    btn_col1, btn_col2, btn_col3 = st.columns(3)

                    with btn_col1:
                        # 상세 보기 버튼
                        if st.button(
                            "📋",
                            key=f"detail_{label['file_id']}",
                            help="상세 정보 보기",
                            use_container_width=True
                        ):
                            st.session_state.selected_file_id = label['file_id']

                    with btn_col2:
                        # 복사 버튼
                        if st.button(
                            "📋",
                            key=f"copy_{label['file_id']}",
                            help="ID 복사",
                            use_container_width=True
                        ):
                            st.write(label['file_id'])
                            st.info("✅ 위 텍스트를 복사하세요")

                    with btn_col3:
                        # 삭제 버튼
                        if st.button(
                            "🗑️",
                            key=f"delete_{label['file_id']}",
                            help="이 항목 삭제",
                            use_container_width=True
                        ):
                            st.session_state[f"confirm_delete_{label['file_id']}"] = True

                    # 삭제 확인 팝업
                    if st.session_state.get(f"confirm_delete_{label['file_id']}", False):
                        st.warning(f"⚠️ 정말로 삭제하시겠습니까?")
                        col_confirm1, col_confirm2 = st.columns(2)

                        with col_confirm1:
                            if st.button(
                                "✅ 삭제 확인",
                                key=f"confirm_yes_{label['file_id']}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                result = labeling_service.delete_label(label['file_id'])
                                if result['success']:
                                    st.success(result['message'])
                                    st.session_state[f"confirm_delete_{label['file_id']}"] = False
                                    st.rerun()
                                else:
                                    st.error(result['message'])
                                    st.session_state[f"confirm_delete_{label['file_id']}"] = False

                        with col_confirm2:
                            if st.button(
                                "❌ 취소",
                                key=f"confirm_no_{label['file_id']}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                st.session_state[f"confirm_delete_{label['file_id']}"] = False
                                st.rerun()

    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        logger.error(f"Failed to browse data: {e}", exc_info=True)


def _render_details(labeling_service) -> None:
    """라벨 상세 정보를 표시합니다."""
    st.subheader("📋 라벨 상세 정보")

    try:
        # 파일 ID로 검색
        col1, col2 = st.columns([3, 1])

        with col1:
            file_id = st.text_input(
                "파일 ID 입력",
                placeholder="UUID를 입력하세요 (예: 550e8400-e29b-41d4-a716-446655440000)",
                key="file_id_input"
            )

        with col2:
            search_btn = st.button("🔍 검색", use_container_width=True)

        if search_btn and file_id:
            label = labeling_service.get_label_details(file_id)

            if label:
                # 이미지 표시
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 분석 이미지")
                    try:
                        img = Image.open(label['image_path'])
                        st.image(img, use_container_width=True)
                    except Exception as e:
                        st.warning(f"이미지를 불러올 수 없습니다: {e}")

                with col2:
                    st.markdown("### 분류 정보")

                    # 분류 정보
                    classification = label['classification']
                    st.write(f"**물품명**: {classification['object_name']}")

                    # 분류 계층 구조 표시
                    st.markdown(f"**📁 분류 계층:**")
                    st.markdown(f"- **주 카테고리**: {classification['primary_category_name']}")
                    st.markdown(f"- **세부 카테고리**: {classification['secondary_category']}")

                    # 신뢰도
                    confidence = label['confidence']
                    st.metric("신뢰도", f"{confidence:.0%}")

                    # 크기 정보 - 명확한 3D 차원으로 표시
                    dimensions = label['dimensions']
                    if any(dimensions.values()):
                        st.markdown("#### 📏 크기 정보 (3D 차원)")

                        # 3열로 크기 정보 표시
                        size_col1, size_col2, size_col3 = st.columns(3)

                        with size_col1:
                            width = dimensions.get('w_cm') or dimensions.get('width_cm')
                            if width:
                                st.metric("가로(W)", f"{width} cm", help="정면에서 본 좌우 길이")
                            else:
                                st.metric("가로(W)", "-", help="정면에서 본 좌우 길이")

                        with size_col2:
                            height = dimensions.get('h_cm') or dimensions.get('height_cm')
                            if height:
                                st.metric("높이(H)", f"{height} cm", help="정면에서 본 상하 길이")
                            else:
                                st.metric("높이(H)", "-", help="정면에서 본 상하 길이")

                        with size_col3:
                            depth = dimensions.get('d_cm') or dimensions.get('depth_cm')
                            if depth:
                                st.metric("깊이(D)", f"{depth} cm", help="물체의 앞뒤 길이(깊이)")
                            else:
                                st.metric("깊이(D)", "-", help="물체의 앞뒤 길이(깊이)")
                    else:
                        st.info("📏 저장된 크기 정보가 없습니다")

                st.markdown("---")

                st.markdown("### 추가 정보")

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**저장 시간**: {label['timestamp']}")
                    st.write(f"**판단 근거**:\n{label.get('reasoning', '없음')}")

                with col2:
                    labeling_quality = label['metadata'].get('labeling_quality', 0)
                    st.metric("라벨링 품질", f"{labeling_quality:.0%}")

                    user_feedback = label.get('user_feedback', {})
                    if user_feedback.get('notes'):
                        st.write(f"**사용자 피드백**:\n{user_feedback['notes']}")

                # 원본 JSON 표시
                with st.expander("🔍 원본 JSON 보기"):
                    st.json(label)

            else:
                st.error("해당 파일 ID의 라벨 정보를 찾을 수 없습니다.")

    except Exception as e:
        st.error(f"상세 정보 조회 실패: {e}")
        logger.error(f"Failed to load details: {e}", exc_info=True)


def _render_deletion(labeling_service) -> None:
    """라벨링 데이터 삭제 기능을 제공합니다."""
    st.subheader("🗑️ 라벨링 데이터 삭제")

    st.warning(
        "⚠️ **주의**: 삭제된 데이터는 복구할 수 없습니다. 신중하게 선택해주세요.",
        icon="⚠️"
    )

    try:
        # 삭제 방식 선택
        deletion_mode = st.radio(
            "삭제 방식 선택",
            options=["개별 삭제", "카테고리 삭제", "전체 삭제"],
            help="삭제할 범위를 선택하세요"
        )

        st.markdown("---")

        if deletion_mode == "개별 삭제":
            _render_single_deletion(labeling_service)

        elif deletion_mode == "카테고리 삭제":
            _render_category_deletion(labeling_service)

        else:  # 전체 삭제
            _render_all_deletion(labeling_service)

    except Exception as e:
        st.error(f"삭제 기능 실패: {e}")
        logger.error(f"Failed to render deletion: {e}", exc_info=True)


def _render_single_deletion(labeling_service) -> None:
    """개별 라벨 삭제를 제공합니다."""
    st.subheader("📌 개별 삭제")
    st.caption("특정 파일 ID의 라벨링 데이터를 삭제합니다.")

    col1, col2 = st.columns([3, 1])

    with col1:
        file_id = st.text_input(
            "파일 ID 입력",
            placeholder="UUID를 입력하세요 (예: 550e8400-e29b-41d4-a716-446655440000)",
            key="deletion_file_id_input"
        )

    with col2:
        search_btn = st.button("🔍 확인", use_container_width=True, key="deletion_search_btn")

    if search_btn and file_id:
        # 라벨 정보 확인
        label = labeling_service.get_label_details(file_id)

        if label:
            st.info(f"삭제 대상: {label['classification']['object_name']} (파일 ID: {file_id[:8]}...)")

            col1, col2 = st.columns([1, 1])

            with col1:
                # 이미지 미리보기
                try:
                    img = Image.open(label['image_path'])
                    st.image(img, caption="이미지", use_container_width=True)
                except Exception:
                    st.warning("이미지를 불러올 수 없습니다")

            with col2:
                st.markdown("**삭제 정보:**")
                st.write(f"물품: {label['classification']['object_name']}")
                st.write(f"주 카테고리: {label['classification']['primary_category_name']}")
                st.write(f"세부 카테고리: {label['classification']['secondary_category']}")
                st.write(f"저장 시간: {label['timestamp']}")

            st.markdown("---")

            if st.button(
                "🗑️ 삭제하기",
                key="confirm_single_delete",
                type="secondary",
                use_container_width=True
            ):
                result = labeling_service.delete_label(file_id)

                if result['success']:
                    st.success(result['message'])
                    st.rerun()
                else:
                    st.error(result['message'])

        else:
            st.error("해당 파일 ID의 라벨 정보를 찾을 수 없습니다.")


def _render_category_deletion(labeling_service) -> None:
    """카테고리별 라벨 삭제를 제공합니다."""
    st.subheader("📁 카테고리 삭제")
    st.caption("특정 카테고리의 모든 라벨링 데이터를 삭제합니다.")

    try:
        stats = labeling_service.get_category_statistics()
        by_category = stats.get('by_primary_category', {})

        if not by_category:
            st.info("삭제할 라벨링 데이터가 없습니다.")
            return

        category_names = {
            'FURN': '가구',
            'APPL': '가전',
            'HLTH': '건강/의료용품',
            'LIFE': '생활/주방용품',
            'SPOR': '스포츠/레저',
            'MUSC': '악기',
            'HOBB': '조경/장식',
            'MISC': '기타'
        }

        col1, col2 = st.columns([2, 2])

        with col1:
            primary_options = {}
            for cat_code, cat_info in by_category.items():
                cat_name = category_names.get(cat_code, cat_code)
                primary_options[cat_code] = f"{cat_name} ({cat_info['count']}개)"

            selected_primary = st.selectbox(
                "주 카테고리 선택",
                options=list(primary_options.keys()),
                format_func=lambda x: primary_options[x],
                key="deletion_primary_select"
            )

        with col2:
            # 세부 카테고리 선택
            subcategories = by_category[selected_primary].get('subcategories', {})
            sub_options = {k: f"{k} ({v}개)" for k, v in subcategories.items()}

            selected_secondary = st.selectbox(
                "세부 카테고리 선택 (선택사항)",
                options=[""] + list(sub_options.keys()),
                format_func=lambda x: "전체" if x == "" else sub_options.get(x, x),
                key="deletion_secondary_select"
            )

        st.markdown("---")

        # 삭제할 데이터 수 표시
        if selected_secondary:
            count = sum(
                1 for label in labeling_service.label_index['labels']
                if label['primary_category'] == selected_primary
                and label['secondary_category'] == selected_secondary
            )
            category_display = f"{selected_primary}/{selected_secondary}"
        else:
            count = by_category[selected_primary]['count']
            category_display = selected_primary

        st.warning(f"삭제 예정: **{category_display}** 분류의 **{count}개** 라벨링 데이터")

        # 삭제 버튼
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button(
                f"🗑️ {count}개 삭제하기",
                key="confirm_category_delete",
                type="secondary",
                use_container_width=True,
                disabled=(count == 0)
            ):
                if selected_secondary:
                    result = labeling_service.delete_labels_by_secondary_category(
                        selected_primary, selected_secondary
                    )
                else:
                    result = labeling_service.delete_labels_by_primary_category(selected_primary)

                if result['success']:
                    st.success(result['message'])
                    st.rerun()
                else:
                    st.error(result['message'])

    except Exception as e:
        st.error(f"카테고리 삭제 실패: {e}")
        logger.error(f"Failed to render category deletion: {e}", exc_info=True)


def _render_all_deletion(labeling_service) -> None:
    """전체 라벨 삭제를 제공합니다."""
    st.subheader("🗑️🗑️ 전체 삭제")
    st.caption("모든 라벨링 데이터를 삭제합니다. (개발/테스트 목적)")

    try:
        stats = labeling_service.get_category_statistics()
        total_count = stats['total_labels']

        if total_count == 0:
            st.info("삭제할 라벨링 데이터가 없습니다.")
            return

        st.error(
            f"⚠️ **주의**: {total_count}개의 모든 라벨링 데이터를 삭제합니다. 이 작업은 되돌릴 수 없습니다!",
            icon="🚨"
        )

        # 확인 입력
        st.markdown("### 삭제 확인")
        confirmation_text = st.text_input(
            "다음 텍스트를 정확히 입력하여 삭제를 확인하세요:",
            placeholder="'모든 라벨링 데이터를 삭제합니다'",
            key="deletion_confirmation_input"
        )

        st.markdown("---")

        # 삭제 버튼
        if st.button(
            f"🗑️🗑️ {total_count}개 모두 삭제",
            key="confirm_all_delete",
            type="secondary",
            use_container_width=True,
            disabled=(confirmation_text != "모든 라벨링 데이터를 삭제합니다")
        ):
            result = labeling_service.delete_all_labels()

            if result['success']:
                st.success(result['message'])
                st.success("모든 라벨링 데이터가 삭제되었습니다.")
                st.rerun()
            else:
                st.error(result['message'])

    except Exception as e:
        st.error(f"전체 삭제 실패: {e}")
        logger.error(f"Failed to render all deletion: {e}", exc_info=True)


if __name__ == "__main__":
    main()
