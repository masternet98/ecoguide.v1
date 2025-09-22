"""
로그 뷰어 UI 컴포넌트
Streamlit에서 로그를 시각적으로 확인할 수 있는 인터페이스를 제공합니다.
"""
import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
import plotly.express as px
import plotly.graph_objects as go

from src.core.logger import logger, LogLevel, LogCategory, LogEntry


def render_log_viewer():
    """메인 로그 뷰어 렌더링"""
    st.header("🔍 시스템 로그 뷰어")
    
    # 탭으로 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📋 실시간 로그", "📊 에러 대시보드", "🔍 로그 검색", "⚙️ 로그 관리"])
    
    with tab1:
        render_realtime_logs()
    
    with tab2:
        render_error_dashboard()
    
    with tab3:
        render_log_search()
    
    with tab4:
        render_log_management()


def render_realtime_logs():
    """실시간 로그 표시"""
    st.subheader("실시간 로그 스트림")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        auto_refresh = st.checkbox("자동 새로고침 (5초)", value=False)
        if auto_refresh:
            st.rerun()
    
    with col2:
        max_logs = st.selectbox("표시할 로그 수", [50, 100, 200, 500], index=1)
    
    with col3:
        if st.button("🔄 새로고침"):
            st.rerun()
    
    # 최근 로그 가져오기
    recent_logs = logger.get_logs(limit=max_logs)
    
    if not recent_logs:
        st.info("표시할 로그가 없습니다.")
        return
    
    # 로그 통계 표시
    total_logs = len(recent_logs)
    error_logs = len([log for log in recent_logs if log.level == LogLevel.ERROR])
    warning_logs = len([log for log in recent_logs if log.level == LogLevel.WARNING])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 로그", total_logs)
    with col2:
        st.metric("에러", error_logs, delta=f"{error_logs/total_logs*100:.1f}%" if total_logs > 0 else "0%")
    with col3:
        st.metric("경고", warning_logs, delta=f"{warning_logs/total_logs*100:.1f}%" if total_logs > 0 else "0%")
    with col4:
        success_logs = len([log for log in recent_logs if log.success == True])
        st.metric("성공", success_logs, delta=f"{success_logs/total_logs*100:.1f}%" if total_logs > 0 else "0%")
    
    st.divider()
    
    # 로그 목록 표시
    for log in recent_logs:
        render_log_entry(log)
    
    # 자동 새로고침 처리
    if auto_refresh:
        import time
        time.sleep(5)
        st.rerun()


def render_log_entry(log: LogEntry):
    """개별 로그 엔트리 렌더링"""
    # 로그 레벨에 따른 색상 설정
    level_colors = {
        LogLevel.DEBUG: "🐛",
        LogLevel.INFO: "ℹ️",
        LogLevel.WARNING: "⚠️",
        LogLevel.ERROR: "❌",
        LogLevel.CRITICAL: "🚨"
    }
    
    level_emoji = level_colors.get(log.level, "📝")
    
    # 성공/실패 표시
    success_indicator = ""
    if log.success is True:
        success_indicator = " ✅"
    elif log.success is False:
        success_indicator = " ❌"
    
    # 시간 포맷팅
    try:
        log_time = datetime.fromisoformat(log.timestamp).strftime("%H:%M:%S")
    except:
        log_time = log.timestamp[:8] if len(log.timestamp) >= 8 else log.timestamp
    
    # 기본 정보 표시
    with st.container():
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.write(f"**{log_time}**")
            st.caption(f"{log.category.value}")
        
        with col2:
            duration_text = f" ({log.duration_ms:.1f}ms)" if log.duration_ms else ""
            st.write(f"{level_emoji} **{log.module}::{log.function}::{log.step}**{success_indicator}{duration_text}")
            st.write(log.message)
            
            # 에러 정보 표시
            if log.error_type:
                st.error(f"**{log.error_type}**: {log.error_details.get('message', 'Unknown error') if log.error_details else 'Unknown error'}")
            
            # 컨텍스트 데이터 표시
            if log.context_data:
                with st.expander("📋 상세 정보"):
                    st.json(log.context_data)
            
            # 스택 트레이스 표시
            if log.stack_trace:
                with st.expander("🔍 스택 트레이스"):
                    st.code(log.stack_trace, language="python")
        
        st.divider()


def render_error_dashboard():
    """에러 대시보드"""
    st.subheader("📊 에러 분석 대시보드")
    
    # 시간 범위 선택
    col1, col2 = st.columns(2)
    with col1:
        hours = st.selectbox("분석 기간", [1, 6, 12, 24, 48, 168], index=3, format_func=lambda x: f"최근 {x}시간")
    with col2:
        if st.button("🔄 대시보드 새로고침"):
            st.rerun()
    
    # 에러 요약 가져오기
    error_summary = logger.get_error_summary(hours=hours)
    
    if error_summary["total_errors"] == 0:
        st.success(f"최근 {hours}시간 동안 에러가 발생하지 않았습니다! 🎉")
        return
    
    # 에러 통계 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 에러 수", error_summary["total_errors"])
    with col2:
        error_types = len(error_summary["error_by_type"])
        st.metric("에러 유형", error_types)
    with col3:
        affected_modules = len(error_summary["error_by_module"])
        st.metric("영향받은 모듈", affected_modules)
    
    st.divider()
    
    # 에러 유형별 차트
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("에러 유형별 분포")
        if error_summary["error_by_type"]:
            error_df = pd.DataFrame(list(error_summary["error_by_type"].items()), columns=["에러타입", "발생횟수"])
            fig = px.pie(error_df, values="발생횟수", names="에러타입", title="에러 유형별 분포")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("표시할 데이터가 없습니다.")
    
    with col2:
        st.subheader("모듈별 에러 발생")
        if error_summary["error_by_module"]:
            module_df = pd.DataFrame(list(error_summary["error_by_module"].items()), columns=["모듈", "에러수"])
            module_df = module_df.sort_values("에러수", ascending=True)
            fig = px.bar(module_df, x="에러수", y="모듈", orientation='h', title="모듈별 에러 발생 횟수")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("표시할 데이터가 없습니다.")
    
    # 최근 에러 목록
    st.subheader("최근 발생한 에러들")
    for error_log in error_summary["recent_errors"]:
        render_log_entry(error_log)


def render_log_search():
    """로그 검색 인터페이스"""
    st.subheader("🔍 로그 검색")
    
    # 검색 필터
    col1, col2, col3 = st.columns(3)
    
    with col1:
        level_filter = st.selectbox("로그 레벨", ["전체"] + [level.value for level in LogLevel])
        level_filter = None if level_filter == "전체" else LogLevel(level_filter)
    
    with col2:
        category_filter = st.selectbox("카테고리", ["전체"] + [cat.value for cat in LogCategory])
        category_filter = None if category_filter == "전체" else LogCategory(category_filter)
    
    with col3:
        success_filter = st.selectbox("성공/실패", ["전체", "성공", "실패"])
        success_filter = None if success_filter == "전체" else (success_filter == "성공")
    
    col1, col2 = st.columns(2)
    with col1:
        module_filter = st.text_input("모듈 필터 (부분 매치)")
        module_filter = module_filter if module_filter.strip() else None
    
    with col2:
        function_filter = st.text_input("함수 필터 (부분 매치)")
        function_filter = function_filter if function_filter.strip() else None
    
    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("최대 결과 수", min_value=10, max_value=1000, value=100)
    with col2:
        if st.button("🔍 검색", use_container_width=True):
            st.rerun()
    
    # 검색 실행
    filtered_logs = logger.get_logs(
        level_filter=level_filter,
        category_filter=category_filter,
        module_filter=module_filter,
        function_filter=function_filter,
        success_filter=success_filter,
        limit=limit
    )
    
    st.divider()
    
    # 검색 결과 표시
    if filtered_logs:
        st.subheader(f"검색 결과: {len(filtered_logs)}개")
        
        # 검색 결과를 DataFrame으로 변환하여 표시
        if st.checkbox("테이블 형태로 보기"):
            df_logs = []
            for log in filtered_logs:
                df_logs.append({
                    "시간": log.timestamp[:19] if len(log.timestamp) >= 19 else log.timestamp,
                    "레벨": log.level.value,
                    "카테고리": log.category.value,
                    "모듈": log.module,
                    "함수": log.function,
                    "단계": log.step,
                    "메시지": log.message[:100] + "..." if len(log.message) > 100 else log.message,
                    "성공": "✅" if log.success is True else "❌" if log.success is False else "-",
                    "처리시간": f"{log.duration_ms:.1f}ms" if log.duration_ms else "-"
                })
            
            st.dataframe(pd.DataFrame(df_logs), use_container_width=True)
        else:
            # 상세 뷰로 표시
            for log in filtered_logs:
                render_log_entry(log)
    else:
        st.info("검색 조건에 맞는 로그가 없습니다.")


def render_log_management():
    """로그 관리 인터페이스"""
    st.subheader("⚙️ 로그 관리")
    
    # 현재 상태
    current_logs = len(logger.log_entries)
    st.info(f"현재 메모리에 {current_logs:,}개의 로그가 저장되어 있습니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 로그 파일 정보")
        
        log_file_path = getattr(logger, 'log_file_path', None)
        if log_file_path and os.path.exists(log_file_path):
            file_size = os.path.getsize(log_file_path) / 1024 / 1024  # MB
            st.write(f"**파일 경로**: `{log_file_path}`")
            st.write(f"**파일 크기**: {file_size:.2f} MB")
            
            # 로그 파일 다운로드
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                
                st.download_button(
                    "📥 로그 파일 다운로드",
                    data=log_content,
                    file_name=f"ecoguide_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"파일 읽기 실패: {e}")
        else:
            st.warning("로그 파일을 찾을 수 없습니다.")
    
    with col2:
        st.subheader("🧹 로그 관리 작업")
        
        if st.button("🗑️ 메모리 로그 클리어", help="메모리의 로그만 삭제됩니다. 파일은 유지됩니다."):
            logger.clear_logs()
            st.success("메모리 로그가 클리어되었습니다.")
            st.rerun()
        
        st.divider()
        
        st.subheader("📊 로그 통계")
        if current_logs > 0:
            # 레벨별 통계
            level_counts = {}
            category_counts = {}
            
            for log in logger.log_entries:
                level_counts[log.level.value] = level_counts.get(log.level.value, 0) + 1
                category_counts[log.category.value] = category_counts.get(log.category.value, 0) + 1
            
            st.write("**레벨별 분포**")
            for level, count in level_counts.items():
                percentage = count / current_logs * 100
                st.write(f"- {level}: {count}개 ({percentage:.1f}%)")
            
            st.write("**카테고리별 분포**")
            for category, count in list(category_counts.items())[:5]:  # 상위 5개만 표시
                percentage = count / current_logs * 100
                st.write(f"- {category}: {count}개 ({percentage:.1f}%)")
        
        # 로그 설정
        st.subheader("⚙️ 설정")
        new_max_entries = st.number_input(
            "메모리 최대 로그 수", 
            min_value=1000, 
            max_value=50000, 
            value=logger._max_entries,
            help="메모리에 보관할 최대 로그 엔트리 수"
        )
        
        if st.button("설정 저장"):
            logger._max_entries = new_max_entries
            st.success("설정이 저장되었습니다.")