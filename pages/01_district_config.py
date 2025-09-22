"""
행정구역 데이터 설정 페이지입니다.
CSV 파일 업로드, 중복 제거, JSON 변환 기능을 제공합니다.
"""
import streamlit as st
import os
import json
from src.app.core.config import load_config
from src.domains.district.services.district_service import (
    process_district_csv, get_district_files, preview_district_file,
    auto_update_district_data, force_update_district_data, delete_district_file, delete_all_district_files,
    clear_update_info
)

# 페이지 설정
st.set_page_config(
    page_title="행정구역 설정 - EcoGuide", 
    page_icon="🗺️", 
    layout="wide"
)

# Config 로드
config = load_config()
district_config = config.district

st.title("🗺️ 행정구역 데이터 설정")
st.caption("법정동코드 CSV 파일을 업로드하여 시군구명 기준으로 중복 제거된 JSON 파일을 생성합니다.")

# 탭 생성
tab1, tab2, tab3 = st.tabs(["📤 파일 업로드", "🔄 자동 업데이트", "📁 파일 관리"])

with tab1:
    st.header("CSV 파일 업로드")
    
    # 업로드 설명
    with st.expander("📋 CSV 파일 형식 안내"):
        st.markdown("""
        **필요한 CSV 컬럼 순서:**
        1. 법정동코드 (예: 1111010100)
        2. 시도명 (예: 서울특별시) 
        3. 시군구명 (예: 종로구)
        4. 읍면동명 (예: 청운동)
        5. 리명
        6. 순위
        7. 생성일자 (예: 1988-04-23)
        8. 삭제일자
        
        **처리 과정:**
        - 시군구명이 비어있는 행 제거
        - 시군구명 기준으로 중복 제거 (첫 번째 행 유지)
        - JSON 형태로 {district_config.uploads_dir} 폴더에 저장
        """)
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "CSV 파일을 선택하세요",
        type=['csv'],
        help="법정동코드가 포함된 CSV 파일을 업로드하세요"
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 사용자 정의 파일명 입력
        custom_filename = st.text_input(
            "출력 파일명 (선택사항)",
            placeholder="예: seoul_districts.json",
            help="비워두면 타임스탬프 기반 자동 생성"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # 버튼 위치 조정용
        process_button = st.button(
            "🔄 파일 처리",
            disabled=uploaded_file is None,
            use_container_width=True
        )
    
    # 파일 처리
    if process_button and uploaded_file is not None:
        with st.spinner("CSV 파일을 처리하는 중..."):
            # 파일명 처리
            filename = None
            if custom_filename.strip():
                if not custom_filename.endswith('.json'):
                    filename = custom_filename.strip() + '.json'
                else:
                    filename = custom_filename.strip()
            
            # CSV 처리 (config 전달)
            result = process_district_csv(uploaded_file.getvalue(), filename, district_config)
            
            if result["success"]:
                st.success("✅ " + result["message"])
                
                # 통계 정보 표시
                stats = result["statistics"]
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("원본 데이터", f"{stats['원본_데이터_수']:,}개")
                with col2:
                    st.metric("정리 후", f"{stats['정리_후_데이터_수']:,}개")
                with col3:
                    st.metric("중복 제거 후", f"{stats['중복제거_후_수']:,}개")
                with col4:
                    st.metric("제거된 중복", f"{stats['제거된_중복_수']:,}개")
                
                st.info(f"📁 파일 저장 경로: `{result['file_path']}`")
                
                # 처리된 파일 미리보기
                if st.button("📖 처리된 파일 미리보기"):
                    preview = preview_district_file(result['file_path'], limit=5)
                    if preview["success"]:
                        st.subheader("📋 파일 내용 미리보기 (처음 5개 레코드)")
                        
                        # 메타데이터 표시
                        metadata = preview["metadata"]
                        st.json({
                            "처리일시": metadata.get("processed_date", ""),
                            "총 레코드 수": metadata.get("unique_districts_count", 0)
                        })
                        
                        # 데이터 미리보기
                        if preview["preview_data"]:
                            import pandas as pd
                            df_preview = pd.DataFrame(preview["preview_data"])
                            st.dataframe(df_preview, use_container_width=True)
                    else:
                        st.error(preview["message"])
                        
            else:
                st.error("❌ " + result["message"])

with tab2:
    st.header("data.go.kr 자동 업데이트")
    st.caption("공공데이터포털에서 최신 행정구역 데이터를 자동으로 확인하고 업데이트합니다.")
    
    # 현재 상태 표시
    col1, col2 = st.columns([1,2])
    
    with col1:
        st.subheader("📊 현재 상태")
        
        # 로컬 업데이트 정보 확인
        from src.domains.district.services.district_service import get_last_update_info
        local_info = get_last_update_info(district_config)
        local_date = local_info.get("last_modification_date")
        
        if local_date:
            st.info(f"📅 **로컬 데이터 수정일**: {local_date}")
            st.success("✅ 로컬 데이터가 존재합니다")
        else:
            st.warning("🟡 로컬 업데이트 정보가 없습니다")
            st.info("처음 업데이트를 실행해 주세요")
    
    with col2:
        st.subheader("🌐 웹사이트 확인")
        
        # 웹사이트 상태 확인 버튼
        if st.button("🔍 웹사이트 수정일 확인", use_container_width=True):
            with st.spinner("웹사이트에서 수정일 확인 중..."):
                from src.domains.district.services.district_service import check_data_go_kr_update
                web_result = check_data_go_kr_update(config=district_config)
                
                if web_result["success"]:
                    web_date = web_result["modification_date"]
                    st.success(f"✅ **웹사이트 수정일**: {web_date}")
                    
                    # 로컬과 웹 날짜 비교
                    if local_date and web_date:
                        if local_date == web_date:
                            st.info("🎉 데이터가 최신 상태입니다")
                        else:
                            st.warning("🔄 업데이트가 필요합니다")
                    elif not local_date:
                        st.info("💡 첫 다운로드가 필요합니다")
                else:
                    st.error(f"❌ 확인 실패: {web_result['message']}")

    st.divider()
    
    # 자동 업데이트 실행
    st.subheader("🚀 자동 업데이트 실행")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        **자동 업데이트 기능:**
        1. 웹사이트에서 최신 수정일 확인
        2. 로컬 저장된 수정일과 비교
        3. 업데이트 필요 시 자동 다운로드
        4. CSV 처리 및 JSON 형태로 저장
        5. 업데이트 정보 로컬 저장
        """)
    
    with col2:
        if st.button("🔄 업데이트 확인", use_container_width=True):
            with st.spinner("업데이트 확인 및 처리 중..."):
                # config 전달
                result = auto_update_district_data(config=district_config)
                
                if result["success"]:
                    action = result["action"]
                    
                    if action == "updated":
                        st.success(f"🎉 {result['message']}")
                        
                        # 날짜 정보 표시 (있는 경우)
                        if result.get("web_date") or result.get("local_date"):
                            date_col1, date_col2 = st.columns(2)
                            with date_col1:
                                if result.get("web_date"):
                                    st.info(f"🌐 **웹 수정일**: {result['web_date']}")
                            with date_col2:
                                if result.get("local_date"):
                                    st.info(f"📅 **이전 로컬 수정일**: {result['local_date']}")
                        
                        # 통계 표시
                        stats = result["statistics"]
                        st.subheader("📈 업데이트 통계")
                        
                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            st.metric("원본 데이터", f"{stats['원본_데이터_수']:,}개")
                        with col_b:
                            st.metric("정리 후", f"{stats['정리_후_데이터_수']:,}개")
                        with col_c:
                            st.metric("중복 제거 후", f"{stats['중복제거_후_수']:,}개")
                        with col_d:
                            st.metric("제거된 중복", f"{stats['제거된_중복_수']:,}개")
                        
                        st.info(f"📁 저장 경로: `{result['file_path']}`")
                        
                    elif action == "no_update_needed":
                        st.info(f"ℹ️ {result['message']}")
                        
                        # 날짜 정보 표시
                        if result.get("web_date") and result.get("local_date"):
                            date_col1, date_col2 = st.columns(2)
                            with date_col1:
                                st.success(f"🌐 **웹 수정일**: {result['web_date']}")
                            with date_col2:
                                st.success(f"📅 **로컬 수정일**: {result['local_date']}")
                            st.success("✅ 두 날짜가 일치합니다 - 업데이트 불필요")
                        
                else:
                    action = result.get("action", "unknown")
                    if action == "download_failed":
                        st.error(f"❌ 다운로드 실패: {result['message']}")
                    elif action == "process_failed":
                        st.error(f"❌ 처리 실패: {result['message']}")
                    else:
                        st.error(f"❌ {result['message']}")

    st.divider()

    st.subheader("⚠️ 강제 업데이트 실행")
    st.caption("날짜 비교를 건너뛰고 최신 데이터를 강제로 받아옵니다. 장애 대응 시에만 사용하세요.")
    if st.button("강제 업데이트 실행", use_container_width=True):
        with st.spinner("강제 업데이트 실행 중..."):
            force_result = force_update_district_data(config=district_config)
            if force_result.get("success"):
                st.success(force_result.get("message", "강제 업데이트가 완료되었습니다."))

                stats = force_result.get("statistics")
                if stats:
                    st.json({"처리 통계": stats})

                file_path = force_result.get("file_path")
                if file_path:
                    st.info(f"생성된 파일 경로: `{file_path}`")
            else:
                st.error(force_result.get("message", "강제 업데이트에 실패했습니다."))
    
    # 데이터 소스 정보
    st.divider()
    st.subheader("📍 데이터 소스 정보")
    
    data_info_col1, data_info_col2 = st.columns(2)
    
    with data_info_col1:
        st.markdown("""
        **📊 데이터 출처**
        - **사이트**: 공공데이터포털 (data.go.kr)
        - **데이터명**: 행정안전부 법정동코드
        - **업데이트 주기**: 연간 (매년 8월)
        - **파일 형식**: CSV
        """)
    
    with data_info_col2:
        st.markdown(f"""
        **🔗 관련 링크**
        - [데이터 페이지]({district_config.page_url})
        - [행정안전부](https://www.mois.go.kr)
        
        **⚙️ 처리 방식**
        - 시군구명 기준 중복 제거
        - 중복 개수 정보 추가
        - JSON 형태로 구조화
        """)

with tab3:
    st.header("저장된 파일 관리")
    
    # 상단 버튼들
    col_refresh, col_delete_all = st.columns([1, 1])
    
    with col_refresh:
        if st.button("🔄 목록 새로고침"):
            st.rerun()
    
    with col_delete_all:
        # 일괄 삭제 기능
        files_exist = len(get_district_files(district_config)) > 0
        
        # 세션 상태 초기화
        if 'delete_all_confirm' not in st.session_state:
            st.session_state.delete_all_confirm = False
        
        if not st.session_state.delete_all_confirm:
            # 첫 번째 단계: 삭제 버튼
            if st.button("🗑️ 모든 파일 삭제", disabled=not files_exist, type="secondary"):
                st.session_state.delete_all_confirm = True
                st.rerun()
        else:
            # 두 번째 단계: 확인 단계
            st.warning("⚠️ **주의**: 모든 파일과 업데이트 정보를 삭제하시겠습니까?")
            st.markdown("- 모든 district JSON 파일 삭제")
            st.markdown("- 업데이트 정보 초기화 (last_update_info.json)")
            st.markdown("- **삭제된 파일은 복구할 수 없습니다**")
            
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("❌ 취소", key="cancel_delete_all", use_container_width=True):
                    st.session_state.delete_all_confirm = False
                    st.rerun()
            
            with confirm_col2:
                if st.button("✅ 확인 - 모두 삭제", key="confirm_delete_all", type="primary", use_container_width=True):
                    with st.spinner("모든 파일 삭제 중..."):
                        # 새로 만든 통합 삭제 함수 사용
                        delete_result = delete_all_district_files(district_config)
                        
                        if delete_result["success"]:
                            st.success(f"✅ {delete_result['message']}")
                            if delete_result.get('update_info_cleared'):
                                st.info("📝 업데이트 정보도 초기화되었습니다.")
                        else:
                            st.error(f"❌ {delete_result['message']}")
                        
                        # 세션 상태 초기화
                        st.session_state.delete_all_confirm = False
                        st.rerun()
    
    # 저장된 파일 목록 (config 전달)
    files = get_district_files(district_config)
    
    if not files:
        st.info("저장된 파일이 없습니다. 먼저 CSV 파일을 업로드해 주세요.")
    else:
        st.subheader(f"📂 총 {len(files)}개 파일")
        
        for i, file_info in enumerate(files):
            with st.expander(f"📄 {file_info['filename']} ({file_info['size_mb']}MB) - {file_info['created_time']}"):
                col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                
                with col1:
                    st.write(f"**경로:** `{file_info['file_path']}`")
                    st.write(f"**크기:** {file_info['size_mb']}MB")
                    st.write(f"**생성일시:** {file_info['created_time']}")
                
                with col2:
                    if st.button(f"📖 미리보기", key=f"preview_{i}"):
                        preview = preview_district_file(file_info['file_path'], limit=10)
                        if preview["success"]:
                            
                            # 메타데이터
                            metadata = preview["metadata"]
                            st.json({
                                "처리일시": metadata.get("processed_date", ""),
                                "원본 데이터 수": metadata.get("original_count", 0),
                                "중복 제거 후": metadata.get("unique_districts_count", 0),
                                "제거된 중복": metadata.get("removed_duplicates", 0)
                            })
                            
                            # 데이터 미리보기 (처음 10개)
                            if preview["preview_data"]:
                                import pandas as pd
                                df_preview = pd.DataFrame(preview["preview_data"])
                                st.dataframe(df_preview, use_container_width=True)
                                
                                if preview["total_count"] > 10:
                                    st.info(f"총 {preview['total_count']}개 중 10개만 표시됨")
                        else:
                            st.error(preview["message"])
                
                with col3:
                    # 파일 다운로드
                    try:
                        with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        
                        st.download_button(
                            "⬇️ 다운로드",
                            data=file_content,
                            file_name=file_info['filename'],
                            mime="application/json",
                            key=f"download_{i}"
                        )
                    except Exception as e:
                        st.error(f"파일 읽기 실패: {e}")
                
                with col4:
                    # 파일 삭제
                    delete_key = f"delete_{i}"
                    
                    # 삭제 확인을 위한 체크박스
                    confirm_delete = st.checkbox(
                        "삭제 확인", 
                        key=f"confirm_{i}",
                        help="삭제하려면 체크하세요"
                    )
                    
                    delete_button = st.button(
                        "🗑️ 삭제",
                        key=delete_key,
                        disabled=not confirm_delete,
                        use_container_width=True,
                        type="secondary"
                    )
                    
                    if delete_button and confirm_delete:
                        with st.spinner(f"파일 삭제 중..."):
                            delete_result = delete_district_file(file_info['file_path'], district_config)
                            
                            if delete_result["success"]:
                                st.success(f"✅ {delete_result['message']}")
                                
                                # 삭제 후 남은 파일 확인
                                remaining_files = get_district_files(district_config)
                                if len(remaining_files) == 0:
                                    # 마지막 파일이 삭제된 경우 업데이트 정보도 초기화
                                    clear_result = clear_update_info(district_config)
                                    if clear_result["success"]:
                                        st.info("📝 마지막 파일이 삭제되어 업데이트 정보도 초기화되었습니다.")
                                    else:
                                        st.warning(f"⚠️ 업데이트 정보 초기화 중 문제 발생: {clear_result['message']}")
                                
                                st.rerun()  # 페이지 새로고침하여 파일 목록 업데이트
                            else:
                                st.error(f"❌ {delete_result['message']}")

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 도움말")
    
    st.markdown("""
    ### 📖 사용 방법
    1. **CSV 업로드**: 법정동코드 CSV 파일 선택
    2. **파일명 설정**: 출력 파일명 지정 (선택사항)
    3. **처리 실행**: 중복 제거 및 JSON 변환
    4. **결과 확인**: 통계 및 미리보기
    
    ### 📁 저장 위치
    `{district_config.uploads_dir}` 폴더에 JSON 파일 저장
    
    ### ⚙️ 처리 규칙
    - 시군구명 기준 중복 제거
    - 첫 번째 발견된 레코드 유지
    - 빈 시군구명 행 자동 제거
    
    ### 🗑️ 파일 삭제
    - **개별 삭제**: 확인 체크 후 삭제 버튼 클릭
    - **일괄 삭제**: 모든 파일 삭제 (확인 필요)
    - 삭제된 파일은 복구할 수 없습니다
    """)
    
    # 업로드 폴더 정보 (config 사용)
    uploads_dir = district_config.uploads_dir
    if os.path.exists(uploads_dir):
        try:
            file_count = len([
                f for f in os.listdir(uploads_dir)
                if f.startswith(f"{district_config.file_prefix}")
                    and f.endswith(f".{district_config.file_extension}")
            ])
            st.success(f"📂 {file_count}개 파일 저장됨")
        except:
            st.warning("폴더 접근 오류")
    else:
        st.info("업로드 폴더가 생성됩니다")
