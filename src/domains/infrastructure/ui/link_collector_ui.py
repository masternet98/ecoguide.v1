"""
시군구별 대형폐기물 링크 수동 관리를 위한 Streamlit UI 컴포넌트입니다.
개선된 UI/UX를 통해 시/도, 시/군/구 단계별 선택을 지원하고,
확장된 데이터 모델(여러 URL, 설명)을 관리하는 기능을 제공합니다.
"""
import streamlit as st
import pandas as pd
from urllib.parse import quote
import json
import os
from datetime import datetime
from collections import OrderedDict

# 서비스 모듈 import
from src.domains.infrastructure.services.link_collector_service import (
    get_districts_data,
    load_registered_links,
    save_link,
    delete_link,
    save_url_attachment,
    delete_attachment,
    get_attachment_file_path
)
from src.domains.monitoring.services.monitoring_admin_integration import (
    get_district_error_status,
    get_filtered_districts,
    get_all_districts_error_summary,
    mark_error_as_acknowledged
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

def show_url_or_file_input(label: str, url_key: str, file_key: str, district_key: str, current_data: dict, placeholder: str = ""):
    """URL 입력 또는 파일 업로드 중 선택할 수 있는 UI 컴포넌트를 표시합니다."""
    
    # 현재 저장된 데이터 확인
    current_url = current_data.get(url_key, "")
    current_file = current_data.get(f"{url_key}_file")
    
    # 현재 상태 결정 (URL이 있으면 URL 모드, 파일이 있으면 파일 모드, 둘 다 없으면 URL 모드)
    has_url = bool(current_url)
    has_file = bool(current_file)
    default_mode = "URL" if has_url or not has_file else "파일"
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        st.markdown(f"<div style='text-align: center; margin-top: 8px;'>{label}</div>", unsafe_allow_html=True)
        
        # 입력 방식 선택
        input_mode = st.radio(
            f"{label} 입력방식", 
            ["URL", "파일"], 
            index=0 if default_mode == "URL" else 1,
            key=f"mode_{url_key}_{district_key}",
            horizontal=True,
            label_visibility="collapsed"
        )
    
    with col2:
        if input_mode == "URL":
            # URL 입력
            url_value = st.text_input(
                f"{label} URL", 
                value=current_url, 
                key=f"{url_key}_{district_key}",
                label_visibility="collapsed",
                placeholder=placeholder
            )
            file_value = None
            
            # 기존 파일이 있는 경우 경고 표시
            if has_file and not has_url:
                st.warning(f"기존 파일이 URL로 변경됩니다: {current_file.get('original_name', 'Unknown')}")
                
        else:
            # 파일 업로드 (RAG 기능을 위해 PDF만 허용)
            file_value = st.file_uploader(
                f"{label} 파일",
                key=f"{file_key}_{district_key}",
                type=['pdf'],
                help="RAG 기능 적용을 위해 PDF 파일만 업로드 가능합니다",
                label_visibility="collapsed"
            )
            url_value = ""
            
            # 기존 파일 표시
            if has_file and not file_value:
                original_name = current_file.get('original_name', 'Unknown')
                file_size_mb = current_file.get('size', 0) / (1024*1024)
                
                # 기존 파일이 PDF인지 확인
                is_pdf = original_name.lower().endswith('.pdf')
                
                if is_pdf:
                    st.info(f"기존 파일: {original_name} ({file_size_mb:.2f} MB) ✅ RAG 적용 가능")
                else:
                    st.warning(f"기존 파일: {original_name} ({file_size_mb:.2f} MB) ⚠️ RAG 미적용 (PDF가 아님)")
                    st.caption("RAG 기능을 사용하려면 PDF 파일로 다시 등록해주세요.")
            
            # 기존 URL이 있는 경우 경고 표시
            if has_url and not current_url:
                st.warning(f"기존 URL이 파일로 변경됩니다: {current_url}")
    
    with col3:
        # 바로가기 버튼 (URL인 경우만)
        if input_mode == "URL":
            st.link_button("바로가기", url=url_value, use_container_width=True, disabled=not url_value)
        else:
            # 파일 다운로드 버튼
            if has_file:
                try:
                    file_path = get_attachment_file_path(district_key, current_file.get('stored_name', ''))
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                        st.download_button(
                            "💾", 
                            data=file_data, 
                            file_name=current_file.get('original_name', 'file'), 
                            key=f"download_{url_key}_{district_key}",
                            help="파일 다운로드",
                            use_container_width=True
                        )
                    else:
                        st.button("💾", key=f"download_{url_key}_{district_key}", help="파일이 존재하지 않습니다", disabled=True)
                except Exception as e:
                    st.button("💾", key=f"download_{url_key}_{district_key}", help=f"다운로드 오류: {str(e)}", disabled=True)
            else:
                st.write("")  # 빈 공간
    
    return {
        "mode": input_mode,
        "url": url_value if input_mode == "URL" else "",
        "file": file_value if input_mode == "파일" else None,
        "keep_existing_file": input_mode == "파일" and not file_value and has_file
    }

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
        
        # URL별 첨부파일 정보 처리
        def get_file_info(url_type):
            file_info = value.get(f"{url_type}_file")
            if file_info:
                return f"파일: {file_info.get('original_name', 'Unknown')}"
            return value.get(url_type, "")
        
        export_data.append({
            "시도명": region,
            "시군구명": district,
            "배출정보": get_file_info("info_url"),
            "시스템": get_file_info("system_url"),
            "수수료": get_file_info("fee_url"),
            "폐가전제품": get_file_info("appliance_url"),
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

def show_error_status_panel(district_key: str, config):
    """오류 상태 패널을 표시합니다."""
    error_status = get_district_error_status(district_key, config)
    
    if error_status.has_errors:
        st.error(f"🚨 **{error_status.error_count}개 오류 발견** (마지막 검사: {error_status.last_check[:16] if error_status.last_check else '없음'})")
        
        for error in error_status.errors:
            with st.expander(f"❌ {error['url_type_name']} 오류", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**상태**: {error['status'].upper()}")
                    st.write(f"**오류내용**: {error['error_message']}")
                    if error['last_checked']:
                        st.write(f"**확인시간**: {error['last_checked'][:16]}")
                
                with col2:
                    if st.button("✅ 확인됨", key=f"ack_{district_key}_{error['url_type']}", 
                               help="이 오류를 확인했음으로 표시"):
                        if mark_error_as_acknowledged(district_key, error['url_type'], config):
                            st.success("오류가 확인됨으로 표시되었습니다.")
                            st.rerun()
    elif error_status.last_check:
        st.success(f"✅ **모든 URL 정상** (마지막 검사: {error_status.last_check[:16]})")
    else:
        st.info("ℹ️ **아직 모니터링 검사가 실행되지 않았습니다.**")


def show_sigungu_editor(sigungu_info: dict, registered_links: dict, config):
    """선택된 시군구의 상세 정보 관리 패널을 표시합니다."""
    region = sigungu_info.get("시도명")
    name = sigungu_info.get("시군구명")
    district_key = f"{region}_{name}"
    
    current_link_info = registered_links.get(district_key, {})

    with st.container(border=True):
        # 오류 상태 패널 추가
        show_error_status_panel(district_key, config)
        st.divider()
        
        search_url = create_google_search_url(region, name)
        st.markdown(f'''<a href="{search_url}" target="_blank"><button style="width:100%; margin-bottom: 10px;">'{region} {name}' (으)로 새 창에서 검색 🔎</button></a>''', unsafe_allow_html=True)

        # --- 배출정보 (URL 또는 파일) ---
        info_result = show_url_or_file_input("배출정보", "info_url", "info_file", district_key, current_link_info, "안내 페이지 등")

        # --- 시스템 (URL 또는 파일) ---
        system_result = show_url_or_file_input("시스템", "system_url", "system_file", district_key, current_link_info, "실제 신고 사이트")

        # --- 수수료 (URL 또는 파일) ---
        fee_result = show_url_or_file_input("수수료", "fee_url", "fee_file", district_key, current_link_info, "요금 안내 페이지")

        # --- 폐가전제품 (URL 또는 파일) ---
        appliance_result = show_url_or_file_input("폐가전제품", "appliance_url", "appliance_file", district_key, current_link_info, "가전제품 배출 신고")

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
                    "info_url": info_result["url"],
                    "system_url": system_result["url"],
                    "fee_url": fee_result["url"],
                    "appliance_url": appliance_result["url"],
                    "description": description
                }
                
                # 각 URL 타입별로 파일 처리
                file_count = 0
                pdf_validation_error = False
                
                for url_type, result in [("info_url", info_result), ("system_url", system_result), ("fee_url", fee_result), ("appliance_url", appliance_result)]:
                    if result["file"]:
                        # PDF 파일 검증
                        file_name = result["file"].name.lower()
                        if not file_name.endswith('.pdf'):
                            st.error(f"'{result['file'].name}' 파일은 PDF 형식이 아닙니다. RAG 기능을 위해 PDF 파일만 업로드 가능합니다.")
                            pdf_validation_error = True
                            continue
                        
                        # 새 파일 업로드
                        attachment_info = save_url_attachment(district_key, url_type, result["file"])
                        if attachment_info:
                            link_data[f"{url_type}_file"] = attachment_info
                            file_count += 1
                        else:
                            st.error(f"'{result['file'].name}' 파일 저장에 실패했습니다.")
                    elif result["keep_existing_file"]:
                        # 기존 파일 유지
                        existing_file = current_link_info.get(f"{url_type}_file")
                        if existing_file:
                            link_data[f"{url_type}_file"] = existing_file
                    else:
                        # 기존 파일이 있었다면 삭제
                        existing_file = current_link_info.get(f"{url_type}_file")
                        if existing_file:
                            delete_attachment(district_key, existing_file)
                
                if save_link(district_key, link_data):
                    success_msg = f"{name} 정보가 저장되었습니다."
                    if file_count > 0:
                        success_msg += f" (새 PDF 파일 {file_count}개 포함)"
                    if pdf_validation_error:
                        success_msg += " ⚠️ 일부 비PDF 파일은 제외됨"
                    st.toast(success_msg, icon="✅")
                    st.rerun()
                else:
                    st.error("저장에 실패했습니다.")
        
        with btn_col2:
            if st.button("🗑️ 삭제", key=f"delete_{district_key}", use_container_width=True):
                # URL별 첨부파일들도 함께 삭제
                for url_type in ["info_url", "system_url", "fee_url", "appliance_url"]:
                    file_key = f"{url_type}_file"
                    attachment = current_link_info.get(file_key)
                    if attachment:
                        delete_attachment(district_key, attachment)
                
                if delete_link(district_key):
                    st.toast(f"{name} 정보가 삭제되었습니다.", icon="🗑️")
                    st.session_state.selected_sigungu_key = None # 선택 해제
                    st.rerun()
                else:
                    st.error("삭제에 실패했습니다.")

def show_detail_content_management(all_districts: list, registered_links: dict, config):
    """세부내역 관리 UI"""
    from src.domains.infrastructure.ui.detail_content_ui import show_detail_content_editor

    st.subheader("📖 배출정보/수수료 세부내역 관리")
    st.caption("지역별 배출정보 및 수수료에 대한 상세 내용을 관리합니다.")

    st.divider()

    # 시도 선택
    sido_list = list(set(d.get("시도명") for d in all_districts))
    sido_list.sort()

    selected_sido = st.selectbox(
        "시/도 선택",
        sido_list,
        key="detail_sido_select"
    )

    # 시군구 선택
    if selected_sido:
        sigungu_list = [d.get("시군구명") for d in all_districts if d.get("시도명") == selected_sido]
        sigungu_list.sort()

        selected_sigungu = st.selectbox(
            "시/군/구 선택",
            sigungu_list,
            key="detail_sigungu_select"
        )

        if selected_sigungu:
            district_key = f"{selected_sido}_{selected_sigungu}"

            # 세부내역 관리
            st.subheader(f"🗂️ {selected_sido} {selected_sigungu}")

            # 배출정보 / 수수료 선택
            content_type = st.radio(
                "관리 항목",
                ["배출정보 (info)", "수수료 (fee)"],
                horizontal=True,
                key="detail_content_type"
            )

            content_type_key = 'info' if '배출정보' in content_type else 'fee'

            st.divider()

            show_detail_content_editor(district_key, content_type_key, registered_links, config)


def show_error_summary_dashboard(config):
    """오류 요약 대시보드를 표시합니다."""
    summary = get_all_districts_error_summary(config)
    
    st.subheader("📊 오류 현황 요약")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 지역", summary["total_districts"])
    with col2:
        st.metric("정상 지역", len(summary["healthy_districts"]), 
                 delta=None if len(summary["healthy_districts"]) == 0 else f"+{len(summary['healthy_districts'])}")
    with col3:
        error_count = summary["districts_with_errors"]
        st.metric("오류 지역", error_count,
                 delta=None if error_count == 0 else f"+{error_count}",
                 delta_color="inverse")
    with col4:
        st.metric("미검사 지역", len(summary["never_checked"]),
                 help="아직 모니터링 검사가 실행되지 않은 지역")
    
    if summary["error_districts"]:
        st.warning(f"⚠️ **{len(summary['error_districts'])}개 지역에서 총 {summary['total_errors']}개 오류 발견**")
        
        with st.expander("🚨 오류 발생 지역 목록", expanded=False):
            for district in summary["error_districts"][:10]:  # 상위 10개만 표시
                col1, col2, col3 = st.columns([2, 1, 2])
                
                with col1:
                    st.write(f"**{district.district_name}**")
                with col2:
                    st.error(f"{district.error_count}개 오류")
                with col3:
                    error_types = [e['url_type_name'] for e in district.errors[:3]]  # 최대 3개
                    if len(district.errors) > 3:
                        error_types.append(f"외 {len(district.errors) - 3}개")
                    st.write(", ".join(error_types))
    else:
        st.success("✅ **모든 지역이 정상 상태입니다!**")


def link_collector_ui():

    initialize_session_state()

    # 설정 로드
    from src.app.core.config import load_config
    config = load_config()
    
    # 데이터 로드
    all_districts = get_districts_data()
    registered_links_data = load_registered_links(config)
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

    tab1, tab2, tab3, tab4 = st.tabs(["📝 링크 관리", "🚨 오류 현황", "📤 데이터 내보내기", "📖 세부내역 관리"])

    with tab1:
        # 1단계: 시/도 선택
        sido_list = ["전체"] + list(sido_map.keys())

        def on_sido_change():
            """시/도 선택 변경 시 호출되는 콜백 함수"""
            st.session_state.selected_sigungu_key = None

        st.subheader("1️⃣ 필터 선택")
        filter_cols = st.columns([1, 1, 2])
        with filter_cols[0]:
            selected_sido = st.selectbox(
                "시/도", 
                sido_list,
                index=0 if not st.session_state.selected_sido else sido_list.index(st.session_state.selected_sido),
                on_change=on_sido_change
            )
        with filter_cols[1]:
            error_filter = st.selectbox("오류 상태", ["전체", "오류 있음", "오류 없음", "미검사", "배출정보 미등록"])
        with filter_cols[2]:
            district_search = st.text_input("시/군/구 검색", placeholder="시/군/구 명을 입력하세요...", key="district_search")
        
        st.session_state.selected_sido = selected_sido

        st.divider()

        # 2단계: 통계 정보 및 시/군/구 목록 표시
        sigungus_in_sido = []
        if selected_sido == "전체":
            for sido_name in sido_map:
                sigungus_in_sido.extend(sido_map[sido_name])
        else:
            sigungus_in_sido = sido_map.get(selected_sido, [])

        # 오류 상태 및 검색 필터링 적용
        sigungus_to_display = []
        for d in sigungus_in_sido:
            district_key = f"{d.get('시도명')}_{d.get('시군구명')}"
            district_name = d.get('시군구명', '')
            error_status = get_district_error_status(district_key, config)
            
            # 배출정보 등록 상태 확인
            current_link_info = registered_links.get(district_key, {})
            has_info_url = bool(current_link_info.get("info_url") or current_link_info.get("info_url_file"))
            
            # 시/군/구 검색 필터 적용
            if district_search and district_search.strip():
                if district_search.strip().lower() not in district_name.lower():
                    continue
            
            # 오류 상태 필터 적용
            if error_filter == "오류 있음" and not error_status.has_errors:
                continue
            elif error_filter == "오류 없음" and (error_status.has_errors or not error_status.last_check):
                continue
            elif error_filter == "미검사" and error_status.last_check:
                continue
            elif error_filter == "배출정보 미등록" and has_info_url:
                continue
            
            # 데이터에 오류 상태 및 등록 정보 추가
            d_with_error = d.copy()
            d_with_error['_error_status'] = error_status
            d_with_error['_has_info_url'] = has_info_url
            sigungus_to_display.append(d_with_error)

        if not sigungus_to_display:
            st.warning("표시할 시/군/구가 없습니다.")
            return

        # 통계 계산
        total_count = len(sigungus_to_display)
        error_count = sum(1 for d in sigungus_to_display if d.get('_error_status') and d['_error_status'].has_errors)
        healthy_count = sum(1 for d in sigungus_to_display if d.get('_error_status') and not d['_error_status'].has_errors and d['_error_status'].last_check)
        never_checked = sum(1 for d in sigungus_to_display if d.get('_error_status') and not d['_error_status'].last_check)
        unregistered_count = sum(1 for d in sigungus_to_display if not d.get('_has_info_url', False))

        # 통계 정보 표시
        st.info(f"총 {total_count}개 시/군/구 중 🚨 오류: {error_count}개 / ✅ 정상: {healthy_count}개 / ❓ 미검사: {never_checked}개 / 📝 미등록: {unregistered_count}개")

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
                    error_status = sigungu.get('_error_status')
                    has_info_url = sigungu.get('_has_info_url', False)
                    
                    # 상태 아이콘 결정 (우선순위: 미등록 > 오류 > 정상 > 미검사)
                    if not has_info_url:
                        status_icon = "📝"  # 배출정보 미등록
                        button_type = "secondary"
                        status_badge = " (미등록)"
                    elif error_status and error_status.has_errors:
                        status_icon = "🚨"  # 오류 있음
                        button_type = "secondary"
                        status_badge = f" ({error_status.error_count}개 오류)"
                    elif error_status and error_status.last_check:
                        status_icon = "✅"  # 정상
                        button_type = "primary" if district_key == st.session_state.selected_sigungu_key else "secondary"
                        status_badge = ""
                    else:
                        status_icon = "❓"  # 미검사
                        button_type = "secondary"
                        status_badge = ""
                    
                    button_label = f"{status_icon} {region} {name}{status_badge}"
                    
                    if st.button(button_label, key=district_key, use_container_width=True, type=button_type):
                        st.session_state.selected_sigungu_key = district_key
                        st.rerun()
        
        # 오른쪽 열: 상세 정보 편집기
        with col2:
            if st.session_state.selected_sigungu_key:
                selected_info = next((d for d in all_districts if f"{d.get('시도명')}_{d.get('시군구명')}" == st.session_state.selected_sigungu_key), None)
                if selected_info:
                    st.subheader("3️⃣ 링크 정보 관리")
                    show_sigungu_editor(selected_info, registered_links, config)
            else:
                st.info("왼쪽 목록에서 관리할 시/군/구를 선택하세요.")

    with tab2:
        show_error_summary_dashboard(config)

    with tab3:
        show_data_export(registered_links_data)

    with tab4:
        show_detail_content_management(all_districts, registered_links, config)