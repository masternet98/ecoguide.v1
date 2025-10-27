"""
District Link 세부내역 UI 컴포넌트입니다.
웹페이지 내용을 복사해서 붙여넣으면 AI가 요약해서 저장합니다.
"""

import streamlit as st
from typing import Dict, Any, Optional
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
    세부내역 관리 UI (웹페이지 콘텐츠 AI 분석 방식)

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

    with st.container():
        # 저장된 데이터 표시
        st.subheader("📋 저장된 데이터")
        if current_detail:
            with st.expander("✅ 저장된 정보 보기", expanded=True):
                _show_detail_viewer(current_detail, district_key, content_type, service)
        else:
            st.info("💡 저장된 데이터가 없습니다. 아래에서 웹페이지 내용을 붙여넣어주세요.")

        st.divider()

        # 입력 섹션
        st.subheader("📝 웹페이지 내용 붙여넣기")

        # 등록된 URL 표시
        current_link_info = registered_links.get(district_key, {})
        url_key = f"{content_type}_url"
        registered_url = current_link_info.get(url_key, "")

        if registered_url:
            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"📄 **링크**: {registered_url}")

                with col2:
                    st.link_button(
                        "🌐 열기",
                        url=registered_url,
                        use_container_width=True,
                        help="새 창에서 페이지를 열어 내용을 복사하세요"
                    )

            st.divider()

        # 콘텐츠 입력
        if content_type == 'info':
            _show_info_input(district_key, content_type, service)
        else:  # fee
            _show_fee_input(district_key, content_type, service)

        return False


def _show_detail_viewer(
    current_detail: Dict[str, Any],
    district_key: str,
    content_type: str,
    service: DetailContentService
):
    """
    저장된 데이터를 표시합니다.

    Args:
        current_detail: 저장된 세부내역
        district_key: 지역 키
        content_type: 'info' 또는 'fee'
        service: DetailContentService 인스턴스
    """
    # 메타데이터 표시
    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            source = current_detail.get('source', 'unknown')
            if source == 'ai_analyzed':
                source_label = "🤖 AI 분석 결과"
            elif source == 'ai_generated':
                source_label = "🤖 AI 자동 추출 (레거시)"
            elif source == 'manual':
                source_label = "✍️ 수동 입력"
            else:
                source_label = "❓ 미분류"
            st.write(f"**출처**: {source_label}")

        with col2:
            if current_detail.get('created_at'):
                st.write(f"**생성일**: {current_detail.get('created_at')[:10]}")

    st.divider()

    # 마크다운 콘텐츠 표시
    if isinstance(current_detail, dict) and 'content' in current_detail:
        # 새 형식: 마크다운
        content_text = current_detail.get('content', '')
        st.markdown(content_text)
    else:
        # 레거시 형식 호환성 (JSON)
        st.info("💡 레거시 형식 데이터입니다. 마크다운 형식으로 재분석을 권장합니다.")

    st.divider()

    # 삭제 버튼
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 2])

        with col1:
            if st.button("🗑️ 삭제", key=f"delete_detail_{district_key}_{content_type}"):
                if service.delete_detail_content(district_key, content_type):
                    st.success("✅ 세부내역이 삭제되었습니다!")
                    st.rerun()
                else:
                    st.error("❌ 삭제 실패했습니다.")


def _show_info_input(
    district_key: str,
    content_type: str,
    service: DetailContentService
):
    """배출정보 입력 (웹페이지 콘텐츠 AI 분석)"""
    st.caption("페이지에서 배출정보 관련 내용을 **모두 선택해서 복사**한 후 아래에 붙여넣으세요.")

    # 콘텐츠 입력
    content = st.text_area(
        "배출정보 (복사 붙여넣기)",
        key=f"info_content_{district_key}",
        height=300,
        placeholder="페이지에서 복사한 배출정보 내용을 여기에 붙여넣으세요...",
        help="최소 100자 이상 입력해주세요"
    )

    st.divider()

    # AI 분석 버튼
    if content and len(content) >= 100:
        if st.button("🤖 AI로 분석", key=f"analyze_info_{district_key}", type="primary", use_container_width=True):
            with st.spinner("🔄 배출정보를 분석하고 있습니다..."):
                # 지역 정보 추출
                region, sigungu = district_key.split('_', 1) if '_' in district_key else (district_key, '')
                district_info = {"sido": region, "sigungu": sigungu}

                detail_data = service.generate_detail_content(content, content_type, district_info)

                if detail_data:
                    st.session_state[f"analyzed_detail_{content_type}_{district_key}"] = detail_data
                    st.success("✅ 분석 완료!")
                    st.rerun()
                else:
                    st.error("❌ 분석 실패. OpenAI API 키를 확인하세요.")
    elif content:
        st.warning(f"⚠️ {100 - len(content)}자 더 입력해주세요 (최소 100자 필요)")

    # 분석 결과 표시 및 저장
    if f"analyzed_detail_{content_type}_{district_key}" in st.session_state:
        markdown_content = st.session_state.get(f"analyzed_detail_{content_type}_{district_key}")

        st.divider()
        st.subheader("✨ 분석 결과 검토 및 저장")

        # 마크다운 형식으로 표시
        with st.expander("📋 분석된 정보 (미리보기)", expanded=True):
            st.markdown(markdown_content)

        # 저장 버튼
        with st.container():
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.button("💾 저장", key=f"save_info_{district_key}", type="primary"):
                    if service.save_detail_content(district_key, content_type, markdown_content):
                        st.success("✅ 세부내역이 저장되었습니다!")
                        st.info(f"📁 저장 위치: `waste_links/detail_contents.json`")

                        # 세션 상태 정리
                        st.session_state.pop(f"analyzed_detail_{content_type}_{district_key}", None)

                        st.rerun()
                    else:
                        st.error("❌ 저장 실패했습니다.")

            with col2:
                if st.button("🔙 취소", key=f"cancel_info_{district_key}"):
                    st.session_state.pop(f"analyzed_detail_{content_type}_{district_key}", None)
                    st.rerun()


def _show_fee_input(
    district_key: str,
    content_type: str,
    service: DetailContentService
):
    """수수료 정보 입력 (웹페이지 콘텐츠 AI 분석)"""
    st.caption("페이지에서 수수료 정보 관련 내용을 **모두 선택해서 복사**한 후 아래에 붙여넣으세요.")

    # 콘텐츠 입력
    content = st.text_area(
        "수수료 정보 (복사 붙여넣기)",
        key=f"fee_content_{district_key}",
        height=300,
        placeholder="페이지에서 복사한 수수료 정보 내용을 여기에 붙여넣으세요...",
        help="최소 100자 이상 입력해주세요"
    )

    st.divider()

    # AI 분석 버튼
    if content and len(content) >= 100:
        if st.button("🤖 AI로 분석", key=f"analyze_fee_{district_key}", type="primary", use_container_width=True):
            with st.spinner("🔄 수수료 정보를 분석하고 있습니다..."):
                # 지역 정보 추출
                region, sigungu = district_key.split('_', 1) if '_' in district_key else (district_key, '')
                district_info = {"sido": region, "sigungu": sigungu}

                detail_data = service.generate_detail_content(content, content_type, district_info)

                if detail_data:
                    st.session_state[f"analyzed_detail_{content_type}_{district_key}"] = detail_data
                    st.success("✅ 분석 완료!")
                    st.rerun()
                else:
                    st.error("❌ 분석 실패. OpenAI API 키를 확인하세요.")
    elif content:
        st.warning(f"⚠️ {100 - len(content)}자 더 입력해주세요 (최소 100자 필요)")

    # 분석 결과 표시 및 저장
    if f"analyzed_detail_{content_type}_{district_key}" in st.session_state:
        markdown_content = st.session_state.get(f"analyzed_detail_{content_type}_{district_key}")

        st.divider()
        st.subheader("✨ 분석 결과 검토 및 저장")

        # 마크다운 형식으로 표시
        with st.expander("📋 분석된 정보 (미리보기)", expanded=True):
            st.markdown(markdown_content)

        # 저장 버튼
        with st.container():
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.button("💾 저장", key=f"save_fee_{district_key}", type="primary"):
                    if service.save_detail_content(district_key, content_type, markdown_content):
                        st.success("✅ 세부내역이 저장되었습니다!")
                        st.info(f"📁 저장 위치: `waste_links/detail_contents.json`")

                        # 세션 상태 정리
                        st.session_state.pop(f"analyzed_detail_{content_type}_{district_key}", None)

                        st.rerun()
                    else:
                        st.error("❌ 저장 실패했습니다.")

            with col2:
                if st.button("🔙 취소", key=f"cancel_fee_{district_key}"):
                    st.session_state.pop(f"analyzed_detail_{content_type}_{district_key}", None)
                    st.rerun()
