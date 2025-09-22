"""
Streamlit 애플리케이션의 관리자 페이지를 정의하는 모듈입니다.
Cloudflared 터널 관리, 로그 보기, 환경 변수 다시 로드 기능과
시군구별 대형폐기물 배출 신고 링크 자동 수집 기능을 제공합니다.
"""
import os
import streamlit as st
from src.domains.infrastructure.ui.link_collector_ui import link_collector_ui
from src.app.core.utils import get_app_state
from src.app.core.config import load_config
from src.domains.monitoring.services.monitoring_admin_integration import get_error_statistics_for_dashboard

# 페이지 타이틀 설정
config = load_config()
# st.title("🔧 Admin - 관리 페이지")
# st.caption("링크 관리, 터널 및 디버깅 도구를 관리합니다.")
st.title("🔗 대형폐기물 배출신고 링크 관리")
st.caption("시/도, 시/군/구 단계별로 링크를 선택하고 관리합니다.")

# 오류 상태 요약 표시
try:
    error_stats = get_error_statistics_for_dashboard(config)
    
    if error_stats['metrics']['error_districts'] > 0:
        st.warning(
            f"⚠️ **주의 필요**: {error_stats['metrics']['error_districts']}개 지역에서 "
            f"{error_stats['metrics']['total_errors']}개 오류가 발견되었습니다. "
            f"링크 관리에서 확인해 주세요."
        )
        
        with st.expander("🚨 오류 지역 요약", expanded=False):
            for district in error_stats['top_error_districts']:
                col1, col2, col3 = st.columns([2, 1, 2])
                with col1:
                    st.write(f"**{district.district_name}**")
                with col2:
                    st.error(f"{district.error_count}개 오류")
                with col3:
                    error_urls = [e['url_type_name'] for e in district.errors[:2]]
                    if len(district.errors) > 2:
                        error_urls.append(f"외 {len(district.errors) - 2}개")
                    st.write(", ".join(error_urls))
except Exception as e:
    st.warning("오류 상태 정보를 불러오지 못했습니다.")

# 링크 수집기 UI 표시
try:
    link_collector_ui()
except Exception as e:
    st.error(f"링크 수집기 UI 로드 중 오류가 발생했습니다: {str(e)}")
    st.write("자세한 오류 정보:")
    st.code(str(e))

st.divider()

# 파일 다운로드 섹션 추가
st.header("📁 등록된 파일 관리")
try:
    from src.domains.infrastructure.services.link_collector_service import load_registered_links, get_attachment_file_path
    import os
    
    registered_links_data = load_registered_links(config)
    registered_links = registered_links_data.get("links", {})
    
    if registered_links:
        files_found = False
        
        # 등록된 파일들을 검색해서 다운로드 가능한 목록 생성
        for district_key, link_info in registered_links.items():
            district_files = []
            
            # 각 URL 타입별 파일 확인
            for url_type in ["info_url", "system_url", "fee_url", "appliance_url"]:
                file_key = f"{url_type}_file"
                file_info = link_info.get(file_key)
                if file_info:
                    file_path = get_attachment_file_path(district_key, file_info.get('stored_name', ''))
                    if os.path.exists(file_path):
                        district_files.append({
                            'url_type': url_type,
                            'file_info': file_info,
                            'file_path': file_path,
                            'display_name': {
                                'info_url': '배출정보',
                                'system_url': '시스템',
                                'fee_url': '수수료',
                                'appliance_url': '폐가전제품'
                            }.get(url_type, url_type)
                        })
            
            if district_files:
                files_found = True
                region, district = district_key.split('_', 1) if '_' in district_key else (district_key, '')
                
                with st.expander(f"📂 {region} {district} ({len(district_files)}개 파일)", expanded=False):
                    for file_data in district_files:
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                        
                        with col1:
                            st.write(f"**{file_data['display_name']}**")
                        
                        with col2:
                            original_name = file_data['file_info'].get('original_name', 'Unknown')
                            file_size = file_data['file_info'].get('size', 0)
                            size_mb = file_size / (1024*1024) if file_size > 0 else 0
                            
                            # PDF 여부 확인
                            is_pdf = original_name.lower().endswith('.pdf')
                            pdf_indicator = "✅ RAG" if is_pdf else "⚠️ 비PDF"
                            
                            st.write(f"{original_name} ({size_mb:.2f} MB)")
                            st.caption(f"{pdf_indicator}")
                        
                        with col3:
                            upload_date = file_data['file_info'].get('upload_date', '')
                            if upload_date:
                                st.caption(upload_date[:10])  # YYYY-MM-DD만 표시
                        
                        with col4:
                            try:
                                with open(file_data['file_path'], 'rb') as f:
                                    file_content = f.read()
                                st.download_button(
                                    "💾 다운로드",
                                    data=file_content,
                                    file_name=original_name,
                                    key=f"admin_download_{district_key}_{file_data['url_type']}",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.button("❌ 오류", key=f"error_{district_key}_{file_data['url_type']}", 
                                         help=f"파일 로드 오류: {str(e)}", disabled=True)
        
        if not files_found:
            st.info("등록된 파일이 없습니다.")
    else:
        st.info("등록된 링크 데이터가 없습니다.")
        
except Exception as e:
    st.error(f"파일 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")
    st.code(str(e))

st.divider()
st.header("환경 및 키 설정")
st.write("현재 .env 로드 우선순위: Streamlit secrets → 환경변수 → .env 파일")
if st.button("환경변수(.env) 다시 로드"):
    try:
        # 최신 Streamlit에서는 st.rerun() 사용
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.session_state["_admin_rerun_toggle"] = not st.session_state.get("_admin_rerun_toggle", False)
    except Exception:
        pass
