"""
라벨링 시스템 테스트 페이지

라벨링 기능이 정상 작동하는지 확인합니다.
"""

import streamlit as st
from PIL import Image
import io
from datetime import datetime

from src.app.core.app_factory import get_application
from src.app.core.error_handler import handle_errors, create_streamlit_error_ui, get_error_handler

@handle_errors(show_user_message=True, reraise=False)
def main():
    st.set_page_config(
        page_title="라벨링 시스템 테스트",
        page_icon="🧪",
        layout="wide"
    )

    st.title("🧪 라벨링 시스템 테스트")
    st.markdown("라벨링 서비스의 기능을 테스트합니다.")
    st.markdown("---")

    # 애플리케이션 컨텍스트 초기화
    try:
        app_context = get_application()
    except Exception as e:
        st.error("애플리케이션 초기화에 실패했습니다.")
        create_streamlit_error_ui(get_error_handler().handle_error(e))
        return

    # 라벨링 서비스 가져오기
    labeling_service = app_context.get_service('labeling_service')
    if not labeling_service:
        st.error("❌ 라벨링 서비스를 초기화할 수 없습니다.")
        return

    st.success("✅ 라벨링 서비스가 정상 작동합니다.")
    st.markdown("---")

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📊 통계", "💾 테스트 데이터 저장", "🔍 저장된 데이터 확인"])

    with tab1:
        st.subheader("📊 현재 통계")
        stats = labeling_service.get_category_statistics()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("총 라벨 개수", stats['total_labels'])
        with col2:
            st.metric("마지막 업데이트", datetime.fromisoformat(stats['last_updated']).strftime("%Y-%m-%d %H:%M:%S"))

        st.write("**카테고리별 분포:**")
        st.json(stats['by_primary_category'])

    with tab2:
        st.subheader("💾 테스트 데이터 저장")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**테스트 이미지 생성**")
            # 테스트 이미지 색상 선택
            color = st.color_picker("이미지 색상 선택", "#FF0000")
            test_image = Image.new('RGB', (200, 200), color=color)
            st.image(test_image, caption="테스트 이미지")

        with col2:
            st.write("**분석 결과 입력**")

            object_name = st.text_input("물품명", "테스트 물품", key="obj_name")
            primary_cat = st.selectbox(
                "주 카테고리",
                ["FURN", "APPL", "HLTH", "LIFE", "SPOR", "MUSC", "HOBB", "MISC"],
                key="primary_cat"
            )
            secondary_cat = st.text_input("세부 카테고리", "TEST_ITEM", key="secondary_cat")
            confidence = st.slider("신뢰도", 0.0, 1.0, 0.85, key="conf")

        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            width = st.number_input("가로 (cm)", 0, 500, 100, key="width")
        with col2:
            height = st.number_input("세로 (cm)", 0, 500, 100, key="height")
        with col3:
            depth = st.number_input("높이 (cm)", 0, 500, 100, key="depth")

        feedback = st.text_area("피드백 (선택사항)", "", key="feedback")

        st.markdown("---")

        if st.button("💾 라벨 저장", use_container_width=True, key="save_btn"):
            # 이미지를 바이트로 변환
            img_bytes = io.BytesIO()
            test_image.save(img_bytes, format='JPEG')
            image_bytes = img_bytes.getvalue()

            # 분석 결과 구성
            analysis_result = {
                'object_name': object_name,
                'primary_category': primary_cat,
                'secondary_category': secondary_cat,
                'confidence': confidence,
                'dimensions': {
                    'width_cm': width if width > 0 else None,
                    'height_cm': height if height > 0 else None,
                    'depth_cm': depth if depth > 0 else None,
                    'dimension_sum_cm': width + height + depth
                },
                'reasoning': '테스트 저장'
            }

            # 사용자 피드백
            user_feedback = {
                'notes': feedback,
                'timestamp': datetime.now().isoformat()
            }

            # 라벨 저장
            with st.spinner("💾 라벨을 저장 중입니다..."):
                result = labeling_service.save_label(
                    image_bytes=image_bytes,
                    analysis_result=analysis_result,
                    user_feedback=user_feedback
                )

            if result.get('success'):
                st.success(f"✅ 라벨이 저장되었습니다!")
                st.write(f"**파일 ID:** {result.get('file_id')}")
                st.write(f"**이미지 경로:** {result.get('image_path')}")
                st.write(f"**라벨 경로:** {result.get('label_path')}")
            else:
                st.error(f"❌ 저장 실패: {result.get('error')}")

    with tab3:
        st.subheader("🔍 저장된 데이터 확인")

        stats = labeling_service.get_category_statistics()
        categories = stats['by_primary_category']

        if not categories:
            st.info("아직 저장된 라벨이 없습니다.")
            return

        # 카테고리 선택
        selected_cat = st.selectbox(
            "카테고리 선택",
            list(categories.keys()),
            key="check_cat"
        )

        # 라벨 로드
        labels = labeling_service.get_labels_by_primary_category(selected_cat)

        if labels:
            st.write(f"**{selected_cat} 카테고리의 라벨: {len(labels)}개**")

            for idx, label in enumerate(labels):
                with st.expander(f"라벨 {idx + 1}: {label['classification']['object_name']}", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**이미지**")
                        try:
                            img = Image.open(label['image_path'])
                            st.image(img, use_container_width=True)
                        except Exception as e:
                            st.warning(f"이미지 로드 실패: {e}")

                    with col2:
                        st.write("**정보**")
                        st.write(f"- **ID:** {label['file_id'][:12]}...")
                        st.write(f"- **물품:** {label['classification']['object_name']}")
                        st.write(f"- **분류:** {label['classification']['primary_category_name']}")
                        st.write(f"- **신뢰도:** {label['confidence']:.0%}")
                        st.write(f"- **품질 점수:** {label['metadata']['labeling_quality']:.0%}")
                        st.write(f"- **저장 시간:** {label['timestamp']}")

                    st.json(label)
        else:
            st.info(f"{selected_cat} 카테고리에 라벨이 없습니다.")


if __name__ == "__main__":
    main()
