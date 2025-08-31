"""
시군구별 대형폐기물 링크 수동 관리를 위한 Streamlit UI 컴포넌트입니다.
개선된 UI/UX를 통해 시/도, 시/군/구 단계별 선택을 지원하고,
확장된 데이터 모델(여러 URL, 설명)을 관리하는 기능을 제공합니다.
"""
import streamlit as st
import pandas as pd
from urllib.parse import quote
import json
from datetime import datetime
from collections import OrderedDict

# 서비스 모듈 import
from src.services.link_collector_service import (
    get_districts_data,
    load_registered_links,
    save_link,
    delete_link
)

def initialize_session_state():
    """UI 상호작용을 위한 세션 상태를 초기화합니다."""
    if 'selected_sido' not in st.session_state:
        st.session_state.selected_sido = None
    if 'selected_sigungu_key' not in st.session_state:
        st.session_state.selected_sigungu_key = None

def create_google_search_url(region: str, district: str) -> str:
    """Google 검색을 위한 URL을 생성합니다."""
    query = f'"{region} {district}" 대형폐기물 배출신고'
    return f"https://www.google.com/search?q={quote(query)}"

def show_data_export(registered_links_data: dict):
    """등록된 데이터를 내보내는 UI를 표시합니다."""
    st.subheader("📤 데이터 내보내기")
    
    links = registered_links_data.get("links", {})
    if not links:
        st.info("내보낼 데이터가 없습니다.")
        return

    export_format = st.selectbox("내보내기 형식", ["CSV", "JSON"])

    export_data = []
    for key, value in links.items():
        region, district = key.split('_', 1) if '_' in key else (key, '')
        export_data.append({
            "시도명": region,
            "시군구명": district,
            "정보_URL": value.get("info_url"),
            "시스템_URL": value.get("system_url"),
            "수수료_URL": value.get("fee_url"),
            "설명": value.get("description"),
            "마지막_수정일": value.get("updated_at")
        })

    if not export_data:
        st.warning("내보낼 데이터가 없습니다.")
        return

    if export_format == "CSV":
        df = pd.DataFrame(export_data)
        csv_string = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv_string,
            file_name=f"manual_waste_links_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )
    elif export_format == "JSON":
        json_string = json.dumps(registered_links_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON 다운로드",
            data=json_string,
            file_name=f"manual_waste_links_{datetime.now().strftime('%Y%m%d')}.json",
            mime='application/json'
        )

def show_sigungu_editor(sigungu_info: dict, registered_links: dict):
    """선택된 시군구의 상세 정보 관리 패널을 표시합니다."""
    region = sigungu_info.get("시도명")
    name = sigungu_info.get("시군구명")
    district_key = f"{region}_{name}"
    
    current_link_info = registered_links.get(district_key, {})

    with st.container(border=True):
        search_url = create_google_search_url(region, name)
        st.markdown(f'''<a href="{search_url}" target="_blank"><button style="width:100%; margin-bottom: 10px;">'{region} {name}' (으)로 새 창에서 검색 🔎</button></a>''', unsafe_allow_html=True)

        # --- 정보 URL ---
        info_url_cols = st.columns([1, 3, 1])
        with info_url_cols[0]:
            st.markdown("<div style='text-align: center; margin-top: 8px;'>배출정보 URL</div>", unsafe_allow_html=True)
        with info_url_cols[1]:
            info_url = st.text_input("배출정보 URL", value=current_link_info.get("info_url", ""), key=f"info_url_{district_key}", label_visibility="collapsed", placeholder="안내 페이지 등")
        with info_url_cols[2]:
            st.link_button("바로가기", url=info_url, use_container_width=True, disabled=not info_url)

        # --- 시스템 URL ---
        system_url_cols = st.columns([1, 3, 1])
        with system_url_cols[0]:
            st.markdown("<div style='text-align: center; margin-top: 8px;'>시스템 URL</div>", unsafe_allow_html=True)
        with system_url_cols[1]:
            system_url = st.text_input("시스템 URL", value=current_link_info.get("system_url", ""), key=f"system_url_{district_key}", label_visibility="collapsed", placeholder="실제 신고 사이트")
        with system_url_cols[2]:
            st.link_button("바로가기", url=system_url, use_container_width=True, disabled=not system_url)

        # --- 수수료 URL ---
        fee_url_cols = st.columns([1, 3, 1])
        with fee_url_cols[0]:
            st.markdown("<div style='text-align: center; margin-top: 8px;'>수수료 URL</div>", unsafe_allow_html=True)
        with fee_url_cols[1]:
            fee_url = st.text_input("수수료 URL", value=current_link_info.get("fee_url", ""), key=f"fee_url_{district_key}", label_visibility="collapsed", placeholder="요금 안내 페이지")
        with fee_url_cols[2]:
            st.link_button("바로가기", url=fee_url, use_container_width=True, disabled=not fee_url)

        # --- 설명 ---
        description = st.text_area(
            "설명 (메모)",
            value=current_link_info.get("description", ""),
            key=f"desc_{district_key}"
        )

        # --- 액션 버튼 ---
        btn_col1, btn_col2, _ = st.columns([1, 1, 5])
        with btn_col1:
            if st.button("💾 저장", key=f"save_{district_key}", use_container_width=True, type="primary"):
                link_data = {
                    "info_url": info_url,
                    "system_url": system_url,
                    "fee_url": fee_url,
                    "description": description
                }
                if save_link(district_key, link_data):
                    st.toast(f"{name} 링크가 저장되었습니다.", icon="✅")
                    st.rerun()
                else:
                    st.error("저장에 실패했습니다.")
        
        with btn_col2:
            if st.button("🗑️ 삭제", key=f"delete_{district_key}", use_container_width=True):
                if delete_link(district_key):
                    st.toast(f"{name} 링크가 삭제되었습니다.", icon="🗑️")
                    st.session_state.selected_sigungu_key = None # 선택 해제
                    st.rerun()
                else:
                    st.error("삭제에 실패했습니다.")

def link_collector_ui():
    """링크 수동 관리자 메인 UI"""
    st.header("🔗 대형폐기물 배출신고 링크 관리")
    st.caption("시/도, 시/군/구 단계별로 링크를 선택하고 관리합니다.")

    initialize_session_state()

    # 데이터 로드
    all_districts = get_districts_data()
    registered_links_data = load_registered_links()
    registered_links = registered_links_data.get("links", {})

    if not all_districts:
        st.error("처리할 시군구 데이터가 없습니다. 먼저 [행정구역 설정] 페이지에서 데이터를 준비해주세요.")
        return

    # 시도별 데이터 그룹핑
    sido_map = OrderedDict()
    for d in all_districts:
        sido = d.get("시도명")
        if sido not in sido_map:
            sido_map[sido] = []
        sido_map[sido].append(d)

    tab1, tab2 = st.tabs(["📝 링크 관리", "📤 데이터 내보내기"])

    with tab1:
        # 1단계: 시/도 선택
        sido_list = ["전체"] + list(sido_map.keys())

        def on_sido_change():
            """시/도 선택 변경 시 호출되는 콜백 함수"""
            st.session_state.selected_sigungu_key = None

        st.subheader("1️⃣ 필터 선택")
        filter_cols = st.columns(2)
        with filter_cols[0]:
            selected_sido = st.selectbox(
                "시/도", 
                sido_list,
                index=0 if not st.session_state.selected_sido else sido_list.index(st.session_state.selected_sido),
                on_change=on_sido_change
            )
        with filter_cols[1]:
            filter_option = st.selectbox("등록여부", ["전체", "등록", "미등록"])
        
        st.session_state.selected_sido = selected_sido

        st.divider()

        # 2단계: 통계 정보 및 시/군/구 목록 표시
        sigungus_in_sido = []
        if selected_sido == "전체":
            for sido_name in sido_map:
                sigungus_in_sido.extend(sido_map[sido_name])
        else:
            sigungus_in_sido = sido_map.get(selected_sido, [])

        # 등록 여부 필터링 적용
        sigungus_to_display = []
        for d in sigungus_in_sido:
            is_registered = f"{d.get('시도명')}_{d.get('시군구명')}" in registered_links
            if filter_option == "등록" and not is_registered:
                continue
            if filter_option == "미등록" and is_registered:
                continue
            sigungus_to_display.append(d)

        if not sigungus_to_display:
            st.warning("표시할 시/군/구가 없습니다.")
            return

        # 통계 계산
        total_count = len(sigungus_to_display)
        registered_count = sum(1 for d in sigungus_to_display if f"{d.get('시도명')}_{d.get('시군구명')}" in registered_links)
        unregistered_count = total_count - registered_count

        st.info(f"총 {total_count}개 시/군/구 중 ✅ 등록: {registered_count}개 / ❌ 미등록: {unregistered_count}개")

        # 2단 레이아웃
        col1, col2 = st.columns([1, 2])

        # 왼쪽 열: 시/군/구 목록
        with col1:
            st.subheader("2️⃣ 시/군/구 선택")
            # 스크롤 가능한 컨테이너 추가
            with st.container(height=600):
                for i, sigungu in enumerate(sigungus_to_display):
                    region = sigungu.get("시도명")
                    name = sigungu.get("시군구명")
                    district_key = f"{region}_{name}"
                    is_registered = district_key in registered_links
                    status_icon = "✅" if is_registered else "❌"
                    
                    if st.button(f"{status_icon} {region} {name}", key=district_key, use_container_width=True):
                        st.session_state.selected_sigungu_key = district_key
        
        # 오른쪽 열: 상세 정보 편집기
        with col2:
            if st.session_state.selected_sigungu_key:
                selected_info = next((d for d in all_districts if f"{d.get('시도명')}_{d.get('시군구명')}" == st.session_state.selected_sigungu_key), None)
                if selected_info:
                    st.subheader("3️⃣ 링크 정보 관리")
                    show_sigungu_editor(selected_info, registered_links)
            else:
                st.info("왼쪽 목록에서 관리할 시/군/구를 선택하세요.")

    with tab2:
        show_data_export(registered_links_data)