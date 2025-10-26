"""
District Link 세부내역 UI 컴포넌트입니다.
자동 추출, 수동 입력, 조회 기능을 제공합니다.
"""

import streamlit as st
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json

from src.app.core.config import Config
from src.domains.infrastructure.services.detail_content_service import DetailContentService


def show_detail_content_editor(
    district_key: str,
    content_type: str,  # 'info' or 'fee'
    registered_links: Dict,
    config: Config
) -> bool:
    """
    세부내역 관리 UI (탭: 자동 추출 / 수동 입력 / 조회)

    Args:
        district_key: 지역 키 (예: "서울특별시_강남구")
        content_type: 'info' (배출정보) 또는 'fee' (수수료)
        registered_links: 등록된 링크 데이터
        config: 앱 설정

    Returns:
        저장 여부
    """
    service = DetailContentService(config)
    current_detail = service.get_detail_content(district_key, content_type)

    # 탭 이름 결정
    tab_names = ["🔄 자동 추출", "✍️ 수동 입력", "👁️ 조회"]
    tabs = st.tabs(tab_names)

    with tabs[0]:  # 자동 추출 탭
        return show_auto_extract_mode(district_key, content_type, config, registered_links)

    with tabs[1]:  # 수동 입력 탭
        return show_manual_input_mode(district_key, content_type, config, current_detail)

    with tabs[2]:  # 조회 탭
        show_detail_content_viewer(district_key, content_type, config, current_detail)
        return False


def show_auto_extract_mode(
    district_key: str,
    content_type: str,
    config: Config,
    registered_links: Dict
) -> bool:
    """
    자동 추출 모드: URL/PDF 입력 → 추출 → 검토 → 저장

    Args:
        district_key: 지역 키
        content_type: 'info' 또는 'fee'
        config: 앱 설정
        registered_links: 등록된 링크 데이터

    Returns:
        저장 성공 여부
    """
    service = DetailContentService(config)

    # 1단계: URL 또는 PDF 선택
    st.subheader("1️⃣ 소스 선택")

    source_type = st.radio(
        "소스 선택",
        ["URL", "PDF 파일"],
        horizontal=True,
        key=f"source_{content_type}_{district_key}"
    )

    content = None
    metadata = None

    if source_type == "URL":
        col1, col2 = st.columns([3, 1])

        with col1:
            url = st.text_input(
                f"{content_type} URL 입력",
                key=f"url_input_{content_type}_{district_key}",
                placeholder="https://..."
            )

        with col2:
            if url and st.button("🔗 추출", key=f"extract_url_{content_type}_{district_key}"):
                with st.spinner("🌐 URL에서 콘텐츠를 추출 중입니다..."):
                    content, metadata = service.extract_info_from_url(url)

                    if content:
                        st.success(f"✅ 추출 성공! ({len(content)} 자)")
                        st.session_state[f"extracted_content_{content_type}"] = content
                        st.session_state[f"extracted_metadata_{content_type}"] = metadata
                    else:
                        error_msg = metadata.get("error", "알 수 없는 오류") if metadata else "알 수 없는 오류"
                        st.error(f"❌ 추출 실패: {error_msg}")

    else:  # PDF 파일
        uploaded_file = st.file_uploader(
            "PDF 파일 업로드",
            type=['pdf'],
            key=f"pdf_upload_{content_type}_{district_key}"
        )

        if uploaded_file and st.button("📄 추출", key=f"extract_pdf_{content_type}_{district_key}"):
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name

            try:
                with st.spinner("📖 PDF에서 텍스트를 추출 중입니다..."):
                    content, metadata = service.extract_info_from_pdf(tmp_path)

                    if content:
                        st.success(f"✅ 추출 성공! ({len(content)} 자)")
                        st.session_state[f"extracted_content_{content_type}"] = content
                        st.session_state[f"extracted_metadata_{content_type}"] = metadata
                    else:
                        error_msg = metadata.get("error", "알 수 없는 오류") if metadata else "알 수 없는 오류"
                        st.error(f"❌ 추출 실패: {error_msg}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    # 2단계: 추출된 콘텐츠 표시
    if f"extracted_content_{content_type}" in st.session_state:
        content = st.session_state.get(f"extracted_content_{content_type}")
        metadata = st.session_state.get(f"extracted_metadata_{content_type}")

        st.divider()
        st.subheader("2️⃣ 추출된 콘텐츠 검토")

        with st.expander("📄 원본 콘텐츠 보기", expanded=False):
            st.text_area(
                "원본",
                value=content[:2000] + ("..." if len(content) > 2000 else ""),
                height=200,
                disabled=True,
                label_visibility="collapsed"
            )

        # 메타데이터 표시
        if metadata:
            with st.expander("📊 메타데이터", expanded=False):
                cols = st.columns(2)
                for idx, (key, value) in enumerate(metadata.items()):
                    with cols[idx % 2]:
                        if isinstance(value, (int, float)):
                            st.metric(key, value)
                        else:
                            st.write(f"**{key}**: {str(value)[:100]}")

        # 3단계: AI로 정리
        st.divider()
        st.subheader("3️⃣ AI로 정리")

        col1, col2 = st.columns([1, 4])

        with col1:
            if st.button("🤖 정리하기", key=f"generate_{content_type}_{district_key}"):
                with st.spinner(f"🔄 {content_type} 정보를 정리하고 있습니다..."):
                    # 지역 정보 추출
                    region, sigungu = district_key.split('_', 1) if '_' in district_key else (district_key, '')
                    district_info = {"sido": region, "sigungu": sigungu}

                    detail_data = service.generate_detail_content(content, content_type, district_info)

                    if detail_data:
                        st.session_state[f"generated_detail_{content_type}"] = detail_data
                        st.success("✅ 정리 완료!")
                    else:
                        st.error("❌ 정리 실패. OpenAI API 키를 확인하세요.")

        with col2:
            st.write("추출된 콘텐츠를 OpenAI로 분석하여 구조화된 정보로 변환합니다.")

    # 4단계: 생성된 정보 검토 및 저장
    if f"generated_detail_{content_type}" in st.session_state:
        detail_data = st.session_state.get(f"generated_detail_{content_type}")

        st.divider()
        st.subheader("4️⃣ 생성된 정보 검토 및 저장")

        # JSON 형식으로 표시
        with st.expander("📋 생성된 정보 (JSON)", expanded=True):
            st.json(detail_data)

        # 저장 버튼
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("💾 저장", key=f"save_auto_{content_type}_{district_key}", type="primary"):
                if service.save_detail_content(district_key, content_type, detail_data):
                    st.success("✅ 세부내역이 저장되었습니다!")

                    # 세션 상태 정리
                    st.session_state.pop(f"extracted_content_{content_type}", None)
                    st.session_state.pop(f"extracted_metadata_{content_type}", None)
                    st.session_state.pop(f"generated_detail_{content_type}", None)

                    st.rerun()
                else:
                    st.error("❌ 저장 실패했습니다.")

        with col2:
            if st.button("🔙 취소", key=f"cancel_auto_{content_type}_{district_key}"):
                st.session_state.pop(f"extracted_content_{content_type}", None)
                st.session_state.pop(f"extracted_metadata_{content_type}", None)
                st.session_state.pop(f"generated_detail_{content_type}", None)
                st.rerun()


def show_manual_input_mode(
    district_key: str,
    content_type: str,
    config: Config,
    current_detail: Optional[Dict[str, Any]]
) -> bool:
    """
    수동 입력 모드: 직접 작성 → 저장

    Args:
        district_key: 지역 키
        content_type: 'info' 또는 'fee'
        config: 앱 설정
        current_detail: 기존 세부내역 (수정 시)

    Returns:
        저장 성공 여부
    """
    service = DetailContentService(config)

    st.subheader("📝 수동으로 정보 입력")

    if content_type == 'info':
        detail_form = _create_info_input_form(current_detail)
    else:  # fee
        detail_form = _create_fee_input_form(current_detail)

    # 저장 버튼
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("💾 저장", key=f"save_manual_{content_type}_{district_key}", type="primary"):
            # 메타데이터 추가
            detail_form['source'] = 'manual'
            detail_form['extracted_at'] = datetime.now().isoformat()

            if service.save_detail_content(district_key, content_type, detail_form):
                st.success("✅ 세부내역이 저장되었습니다!")
                st.rerun()
            else:
                st.error("❌ 저장 실패했습니다.")

    with col2:
        if st.button("🔙 취소", key=f"cancel_manual_{content_type}_{district_key}"):
            st.rerun()

    return False


def _create_info_input_form(current_detail: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """배출정보 입력 폼"""
    col1, col2 = st.columns(2)

    with col1:
        배출_가능_물품 = st.text_area(
            "배출 가능 물품 (쉼표로 구분)",
            value=", ".join(current_detail.get('배출_가능_물품', [])) if current_detail else "",
            key="info_available_items"
        )

    with col2:
        배출_불가능_물품 = st.text_area(
            "배출 불가능 물품 (쉼표로 구분)",
            value=", ".join(current_detail.get('배출_불가능_물품', [])) if current_detail else "",
            key="info_unavailable_items"
        )

    배출_방법 = st.text_area(
        "배출 방법",
        value=current_detail.get('배출_방법', '') if current_detail else "",
        key="info_method"
    )

    수거_일정 = st.text_input(
        "수거 일정",
        value=current_detail.get('수거_일정', '') if current_detail else "",
        key="info_schedule"
    )

    st.subheader("신청 방법")
    col1, col2, col3 = st.columns(3)

    with col1:
        신청_온라인 = st.text_input(
            "온라인",
            value=current_detail.get('신청_방법', {}).get('온라인', '') if current_detail else "",
            key="info_online"
        )

    with col2:
        신청_전화 = st.text_input(
            "전화",
            value=current_detail.get('신청_방법', {}).get('전화', '') if current_detail else "",
            key="info_phone"
        )

    with col3:
        신청_방문 = st.text_input(
            "방문",
            value=current_detail.get('신청_방법', {}).get('방문', '') if current_detail else "",
            key="info_visit"
        )

    기본_수수료 = st.text_input(
        "기본 수수료",
        value=current_detail.get('기본_수수료', '') if current_detail else "",
        key="info_fee"
    )

    연락처 = st.text_input(
        "연락처",
        value=current_detail.get('연락처', '') if current_detail else "",
        key="info_contact"
    )

    운영_시간 = st.text_input(
        "운영 시간",
        value=current_detail.get('운영_시간', '') if current_detail else "",
        key="info_hours"
    )

    추가_정보 = st.text_area(
        "추가 정보",
        value=current_detail.get('추가_정보', '') if current_detail else "",
        key="info_additional"
    )

    신뢰도 = st.slider(
        "신뢰도",
        0.0, 1.0,
        value=current_detail.get('신뢰도', 0.8) if current_detail else 0.8,
        step=0.1,
        key="info_confidence"
    )

    return {
        "배출_가능_물품": [x.strip() for x in 배출_가능_물품.split(",") if x.strip()],
        "배출_불가능_물품": [x.strip() for x in 배출_불가능_물품.split(",") if x.strip()],
        "배출_방법": 배출_방법,
        "수거_일정": 수거_일정,
        "신청_방법": {
            "온라인": 신청_온라인,
            "전화": 신청_전화,
            "방문": 신청_방문
        },
        "기본_수수료": 기본_수수료,
        "연락처": 연락처,
        "운영_시간": 운영_시간,
        "추가_정보": 추가_정보,
        "신뢰도": 신뢰도
    }


def _create_fee_input_form(current_detail: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """수수료 정보 입력 폼"""
    배출_기준 = st.text_area(
        "배출 기준",
        value=current_detail.get('배출_기준', '') if current_detail else "",
        key="fee_criteria"
    )

    st.subheader("요금 표")

    # 기존 요금 표
    existing_fee_table = current_detail.get('요금_표', []) if current_detail else []

    # 요금 표 입력 (간단한 형식)
    fee_table_text = st.text_area(
        "요금 표 (한 줄에 하나 | 형식: 카테고리|기준|요금|설명)",
        value="\n".join([
            f"{item.get('카테고리', '')}|{item.get('기준', '')}|{item.get('요금', '')}|{item.get('설명', '')}"
            for item in existing_fee_table
        ]) if existing_fee_table else "",
        height=150,
        key="fee_table",
        help="예: 소파|길이 200cm 초과|50,000원|3인 이상 소파"
    )

    # 요금 표 파싱
    요금_표 = []
    if fee_table_text.strip():
        for line in fee_table_text.strip().split('\n'):
            if line.strip():
                parts = line.split('|')
                if len(parts) >= 3:
                    요금_표.append({
                        "카테고리": parts[0].strip(),
                        "기준": parts[1].strip(),
                        "요금": parts[2].strip(),
                        "설명": parts[3].strip() if len(parts) > 3 else ""
                    })

    예약_방법 = st.text_input(
        "예약 방법",
        value=current_detail.get('예약_방법', '') if current_detail else "",
        key="fee_booking"
    )

    결제_방법 = st.text_input(
        "결제 방법",
        value=current_detail.get('결제_방법', '') if current_detail else "",
        key="fee_payment"
    )

    할인 = st.text_input(
        "할인 정보",
        value=current_detail.get('할인', '') if current_detail else "",
        key="fee_discount"
    )

    추가_정보 = st.text_area(
        "추가 정보",
        value=current_detail.get('추가_정보', '') if current_detail else "",
        key="fee_additional"
    )

    신뢰도 = st.slider(
        "신뢰도",
        0.0, 1.0,
        value=current_detail.get('신뢰도', 0.8) if current_detail else 0.8,
        step=0.1,
        key="fee_confidence"
    )

    return {
        "배출_기준": 배출_기준,
        "요금_표": 요금_표,
        "예약_방법": 예약_방법,
        "결제_방법": 결제_방법,
        "할인": 할인,
        "추가_정보": 추가_정보,
        "신뢰도": 신뢰도
    }


def show_detail_content_viewer(
    district_key: str,
    content_type: str,
    config: Config,
    current_detail: Optional[Dict[str, Any]]
):
    """
    세부내역 조회/수정/삭제

    Args:
        district_key: 지역 키
        content_type: 'info' 또는 'fee'
        config: 앱 설정
        current_detail: 현재 세부내역
    """
    service = DetailContentService(config)

    if not current_detail:
        st.info("💡 저장된 세부내역이 없습니다.")
        return

    st.subheader("📋 저장된 정보")

    # 메타데이터 표시
    col1, col2, col3 = st.columns(3)

    with col1:
        source = current_detail.get('source', 'unknown')
        source_label = "🤖 AI 생성" if source == 'ai_generated' else "✍️ 수동 입력"
        st.write(f"**출처**: {source_label}")

    with col2:
        if current_detail.get('extracted_at'):
            st.write(f"**생성일**: {current_detail.get('extracted_at')[:10]}")

    with col3:
        신뢰도 = current_detail.get('신뢰도', 0)
        st.metric("신뢰도", f"{신뢰도:.0%}")

    st.divider()

    # 정보 표시
    if content_type == 'info':
        st.write("**배출 가능 물품**")
        st.write(", ".join(current_detail.get('배출_가능_물품', [])) or "미등록")

        st.write("**배출 불가능 물품**")
        st.write(", ".join(current_detail.get('배출_불가능_물품', [])) or "미등록")

        st.write("**배출 방법**")
        st.write(current_detail.get('배출_방법', '미등록'))

        st.write("**수거 일정**")
        st.write(current_detail.get('수거_일정', '미등록'))

        st.write("**신청 방법**")
        신청 = current_detail.get('신청_방법', {})
        st.write(f"- 온라인: {신청.get('온라인', '미등록')}")
        st.write(f"- 전화: {신청.get('전화', '미등록')}")
        st.write(f"- 방문: {신청.get('방문', '미등록')}")

        st.write("**기본 수수료**")
        st.write(current_detail.get('기본_수수료', '미등록'))

        st.write("**연락처**")
        st.write(current_detail.get('연락처', '미등록'))

        st.write("**운영 시간**")
        st.write(current_detail.get('운영_시간', '미등록'))

        st.write("**추가 정보**")
        st.write(current_detail.get('추가_정보', '없음'))

    else:  # fee
        st.write("**배출 기준**")
        st.write(current_detail.get('배출_기준', '미등록'))

        st.write("**요금 표**")
        요금_표 = current_detail.get('요금_표', [])
        if 요금_표:
            for item in 요금_표:
                st.write(f"- **{item.get('카테고리')}**: {item.get('기준')} → {item.get('요금')}")
                if item.get('설명'):
                    st.write(f"  {item.get('설명')}")
        else:
            st.write("미등록")

        st.write("**예약 방법**")
        st.write(current_detail.get('예약_방법', '미등록'))

        st.write("**결제 방법**")
        st.write(current_detail.get('결제_방법', '미등록'))

        st.write("**할인**")
        st.write(current_detail.get('할인', '없음'))

        st.write("**추가 정보**")
        st.write(current_detail.get('추가_정보', '없음'))

    st.divider()

    # 삭제 버튼
    if st.button("🗑️ 삭제", key=f"delete_{content_type}_{district_key}", help="저장된 세부내역을 삭제합니다"):
        if service.delete_detail_content(district_key, content_type):
            st.success("✅ 세부내역이 삭제되었습니다!")
            st.rerun()
        else:
            st.error("❌ 삭제 실패했습니다.")
