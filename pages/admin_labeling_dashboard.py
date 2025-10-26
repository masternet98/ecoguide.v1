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
    tab1, tab2, tab3 = st.tabs(["📈 통계", "🏷️ 데이터 조회", "📋 상세 정보"])

    with tab1:
        _render_statistics(labeling_service)

    with tab2:
        _render_data_browser(labeling_service)

    with tab3:
        _render_details(labeling_service)


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
        for cat_code, cat_info in by_category.items():
            cat_name = category_names.get(cat_code, cat_code)
            primary_options[cat_code] = f"{cat_name} ({cat_info['count']}개)"

        col1, col2 = st.columns(2)

        with col1:
            selected_primary = st.selectbox(
                "주 카테고리 선택",
                options=list(primary_options.keys()),
                format_func=lambda x: primary_options[x],
                key="primary_category_select"
            )

        # 세부 카테고리 선택
        subcategories = by_category[selected_primary].get('subcategories', {})
        sub_options = {k: f"{k} ({v}개)" for k, v in subcategories.items()}

        with col2:
            selected_secondary = st.selectbox(
                "세부 카테고리 선택 (선택사항)",
                options=[""] + list(sub_options.keys()),
                format_func=lambda x: "전체" if x == "" else sub_options.get(x, x),
                key="secondary_category_select"
            )

        st.markdown("---")

        # 데이터 로드 및 표시
        if selected_secondary:
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
                # 이미지 표시
                image_path = label['image_path']
                try:
                    img = Image.open(image_path)
                    st.image(img, use_container_width=True)
                except Exception as e:
                    st.warning(f"이미지를 불러올 수 없습니다: {e}")

                # 정보 표시
                st.markdown(f"**ID**: {label['file_id'][:8]}...")
                st.markdown(f"**물품**: {label['classification']['object_name']}")
                st.markdown(f"**분류**: {label['classification']['primary_category_name']}")
                st.markdown(f"**신뢰도**: {label['confidence']:.0%}")

                # 크기 정보 표시
                dimensions = label.get('dimensions', {})
                if any(dimensions.values()):
                    st.markdown("**📏 크기:**")
                    size_info = []
                    if dimensions.get('width_cm'):
                        size_info.append(f"가로: {dimensions['width_cm']}cm")
                    if dimensions.get('height_cm'):
                        size_info.append(f"세로: {dimensions['height_cm']}cm")
                    if dimensions.get('depth_cm'):
                        size_info.append(f"높이: {dimensions['depth_cm']}cm")
                    if size_info:
                        st.caption(" / ".join(size_info))

                # 상세 보기 버튼
                if st.button(
                    "📋 상세 보기",
                    key=f"detail_{label['file_id']}"
                ):
                    st.session_state.selected_file_id = label['file_id']

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
                    st.write(f"**주 카테고리**: {classification['primary_category_name']} ({classification['primary_category']})")
                    st.write(f"**세부 카테고리**: {classification['secondary_category']}")

                    # 신뢰도
                    confidence = label['confidence']
                    st.metric("신뢰도", f"{confidence:.0%}")

                    # 크기 정보 - 더 명확하게 표시
                    dimensions = label['dimensions']
                    if any(dimensions.values()):
                        st.markdown("#### 📏 크기 정보")

                        # 3열로 크기 정보 표시
                        size_col1, size_col2, size_col3 = st.columns(3)

                        with size_col1:
                            width = dimensions.get('width_cm')
                            if width:
                                st.metric("가로", f"{width} cm")
                            else:
                                st.metric("가로", "-")

                        with size_col2:
                            height = dimensions.get('height_cm')
                            if height:
                                st.metric("세로", f"{height} cm")
                            else:
                                st.metric("세로", "-")

                        with size_col3:
                            depth = dimensions.get('depth_cm')
                            if depth:
                                st.metric("높이", f"{depth} cm")
                            else:
                                st.metric("높이", "-")

                        # 합계 표시
                        dim_sum = dimensions.get('dimension_sum_cm')
                        if dim_sum:
                            st.info(f"📐 **합계**: {dim_sum} cm (가로 + 세로 + 높이)")
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


if __name__ == "__main__":
    main()
