"""Streamlit UI components for the monitoring dashboard.

These functions were extracted from monitoring_ui.py to keep the main module focused on orchestration.
"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.app.core.config import Config
from src.app.core.logger import log_error, log_info, LogCategory
from src.domains.monitoring.services.monitoring_service import (
    run_monitoring_check, get_monitoring_summary, MonitoringConfig,
    check_district_changes, load_monitoring_history
)
from src.domains.monitoring.services.notification_service import (
    get_notification_history, load_notification_config, send_daily_summary_email,
    load_notification_settings, save_notification_settings, send_test_email
)
from src.domains.infrastructure.services.batch_service import get_batch_scheduler
from src.domains.infrastructure.services.link_collector_service import load_registered_links

from .monitoring_charts import (
    display_error_table,
    display_recent_changes_table,
    render_saved_monitoring_results,
)
from .monitoring_data import (
    build_error_table,
    build_recent_changes_table,
    resolve_selected_districts,
)

def show_monitoring_dashboard(config: Config) -> None:
    """Render the monitoring dashboard summary view."""
    st.header("📊 모니터링 요약 대시보드")

    col1, col2, col3 = st.columns(3)

    try:
        summary = get_monitoring_summary(config, days=7)
        overview = summary.get("overview", {})

        with col1:
            st.metric("모니터링 지점", overview.get("total_districts", 0), help="현재 모니터링 대상 수")

        with col2:
            healthy = summary.get("healthy_districts") or overview.get("healthy_districts", 0)
            st.metric("정상 지점", healthy, help="최근 검사에서 문제가 없었던 지점 수")

        with col3:
            error_count = len(summary.get("error_districts", []))
            delta_value = None if error_count == 0 else f"+{error_count}"
            st.metric("문제 지점", error_count, delta=delta_value, delta_color="inverse", help="최근 불일치나 오류가 발생한 지점 수")

        last_check = overview.get("last_check")
        if isinstance(last_check, str):
            last_dt = datetime.fromisoformat(last_check)
            delta = datetime.now() - last_dt
            if delta.days > 0:
                human_delta = f"{delta.days}일 전"
            elif delta.seconds > 3600:
                human_delta = f"{delta.seconds // 3600}시간 전"
            else:
                human_delta = f"{max(delta.seconds // 60, 1)}분 전"
            st.info(f"마지막 점검: {human_delta} ({last_dt.strftime('%Y-%m-%d %H:%M')})")
        else:
            st.warning("아직 모니터링 기록이 없습니다.")

        changes_df = build_recent_changes_table(summary)
        if changes_df is not None:
            st.subheader("🔄 최근 7일 변경사항")
            display_recent_changes_table(changes_df)
        else:
            st.success("최근 7일간 변경된 내역이 없습니다.")

        error_df = build_error_table(summary)
        if error_df is not None:
            st.subheader("⚠️ 문제가 발생한 지점")
            display_error_table(error_df)
        else:
            st.success("모든 지점이 정상입니다.")

    except Exception as exc:
        log_error(
            LogCategory.UI,
            "monitoring_dashboard",
            "show_monitoring_dashboard",
            "대시보드 렌더링 실패",
            str(exc),
            error=exc,
        )
        st.error(f"대시보드를 불러오는 중 오류가 발생했습니다: {exc}")


def show_manual_monitoring(config: Config) -> None:
    """Render controls for running monitoring manually."""
    st.header("🛠 수동 모니터링 실행")

    with st.expander("⚙️ 모니터링 설정", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            timeout = st.number_input("요청 타임아웃(초)", min_value=10, max_value=120, value=30, help="개별 요청의 최대 대기 시간을 설정합니다")
            max_concurrent = st.number_input("동시 검사 수", min_value=1, max_value=10, value=5, help="동시에 검사할 지점 수")
        with col2:
            retry_attempts = st.number_input("재시도 횟수", min_value=1, max_value=5, value=3, help="오류 발생 시 재시도 횟수")
            ignore_minor = st.checkbox("사소한 변경 무시", value=True, help="날짜/시간 등 경미한 변경은 무시합니다")

    registered_data = load_registered_links(config)
    district_keys = list(registered_data.get("links", {}).keys())
    if not district_keys:
        st.warning("등록된 지점이 없습니다. 먼저 링크를 등록해주세요.")
        return

    st.subheader("🎯 검사 대상 선택")
    check_option = st.radio("검사 범위", ["전체 지점", "지정 지점 선택"], horizontal=True)

    selected_districts: Optional[List[str]] = None
    if check_option == "지정 지점 선택":
        district_names = [key.replace('_', ' ') for key in district_keys]
        selected_names = st.multiselect("검사할 지점을 선택하세요", district_names, help="여러 지점을 동시에 선택할 수 있습니다")
        selected_districts = resolve_selected_districts(district_keys, selected_names)

    if st.button("🚀 모니터링 검사 실행", type="primary"):
        if check_option == "지정 지점 선택" and not selected_districts:
            st.error("검사할 지점을 한 개 이상 선택해주세요.")
            return

        monitoring_config = MonitoringConfig(
            request_timeout=timeout,
            max_concurrent_checks=max_concurrent,
            retry_attempts=retry_attempts,
            ignore_minor_changes=ignore_minor,
        )

        run_streaming_monitoring(config, monitoring_config, selected_districts, district_keys)


def run_streaming_monitoring(config: Config, monitoring_config: MonitoringConfig, 
                           selected_districts: Optional[List[str]], district_keys: List[str]):
    """
    실시간 스트리밍 모니터링 실행 및 진행 상황 표시
    """
    # 검사할 지역 결정
    districts_to_check = selected_districts if selected_districts else district_keys
    
    # UI 컴포넌트 초기화
    st.divider()
    st.subheader("🔄 실시간 모니터링 진행 상황")
    
    # 전체 진행률
    overall_progress = st.progress(0)
    overall_status = st.empty()
    
    # 상태 추적용 변수
    district_statuses = {}
    completed_count = 0
    total_districts = len(districts_to_check)
    all_results = []
    
    # 지역별 상태 표시 - 확장 가능한 UI로 개선
    district_status_container = st.container()
    
    with district_status_container:
        st.write("**지역별 검사 현황:**")
        
        # 통합 테이블 형태로 표시
        # 통계 요약 표시
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
        with summary_col1:
            st.metric("총 지역", total_districts, help=f"검사 대상 지역 수")
        with summary_col2:
            pending_metric = st.empty()
            pending_metric.metric("대기중", total_districts, help="아직 검사하지 않은 지역")
        with summary_col3:
            running_metric = st.empty() 
            running_metric.metric("진행중", 0, help="현재 검사 중인 지역")
        with summary_col4:
            completed_metric = st.empty()
            completed_metric.metric("완료", 0, help="검사 완료된 지역")
        
        # 메트릭 업데이트 함수 저장
        district_statuses["metrics"] = {
            "pending": pending_metric,
            "running": running_metric, 
            "completed": completed_metric
        }
        
        # 검색/필터링 기능
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_filter = st.text_input(
                "지역 검색", 
                placeholder="지역명으로 검색 (예: 인천, 서구)",
                key="district_search",
                help="지역명의 일부만 입력해도 검색됩니다"
            )
        with col2:
            show_status = st.selectbox(
                "상태 필터",
                ["전체", "진행중", "완료", "오류", "대기중"],
                key="status_filter"
            )
        with col3:
            show_only_issues = st.checkbox(
                "문제만 표시",
                help="오류나 변경사항이 있는 지역만 표시"
            )
        
        # 상태 표시 테이블 생성
        status_table_placeholder = st.empty()
        
        # 초기 테이블 데이터
        table_data = []
        for district_key in districts_to_check:
            district_name = district_key.replace('_', ' ')
            table_data.append({
                "지역": district_name,
                "상태": "⏳ 대기중",
                "진행률": "0%",
                "결과": "",
                "_key": district_key  # 내부 키 (표시 안됨)
            })
        
        # 테이블 저장소
        district_statuses["table_data"] = table_data
        district_statuses["table_placeholder"] = status_table_placeholder
    
    # 결과 요약 컨테이너
    results_container = st.container()
    
    # 세부 로그 표시
    log_container = st.expander("🔍 상세 진행 로그", expanded=True)
    with log_container:
        log_placeholder = st.empty()
        logs = []
    
    def add_log(message: str):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        logs.append(f"[{timestamp}] {message}")
        # 최근 20개 로그만 유지
        if len(logs) > 20:
            logs.pop(0)
        log_placeholder.text('\n'.join(logs))
    
    def update_district_status_table(district_statuses: dict, search_filter: str = "", status_filter: str = "전체", show_only_issues: bool = False):
        """테이블 형태 상태 업데이트"""
        if "table_data" not in district_statuses:
            return
        
        import pandas as pd
        
        table_data = district_statuses["table_data"]
        
        # 상태별 카운트 계산
        status_counts = {"대기중": 0, "진행중": 0, "완료": 0, "오류": 0}
        for row in table_data:
            status_text = row["상태"]
            for status_key in status_counts.keys():
                if status_key in status_text:
                    status_counts[status_key] += 1
                    break
        
        # 메트릭 업데이트
        if "metrics" in district_statuses:
            metrics = district_statuses["metrics"]
            metrics["pending"].metric("대기중", status_counts["대기중"], help="아직 검사하지 않은 지역")
            metrics["running"].metric("진행중", status_counts["진행중"], help="현재 검사 중인 지역")
            metrics["completed"].metric("완료", status_counts["완료"], help="검사 완료된 지역")
        
        # 검색 필터 적용
        filtered_data = table_data
        if search_filter:
            filtered_data = [
                row for row in table_data 
                if search_filter.lower() in row["지역"].lower()
            ]
        
        # 상태 필터 적용
        if status_filter != "전체":
            status_mapping = {
                "대기중": "⏳",
                "진행중": "🔄", 
                "완료": "✅",
                "오류": "❌"
            }
            target_icon = status_mapping.get(status_filter, "")
            if target_icon:
                filtered_data = [
                    row for row in filtered_data 
                    if row["상태"].startswith(target_icon)
                ]
        
        # 문제만 표시 필터
        if show_only_issues:
            filtered_data = [
                row for row in filtered_data
                if "❌" in row["상태"] or ("변경" in row["결과"] and row["결과"] != "변경:0")
            ]
        
        # 데이터프레임 생성 및 표시
        if filtered_data:
            # 성능 최적화: 표시할 행 수 제한 (최대 100행)
            display_data = filtered_data[:100]
            if len(filtered_data) > 100:
                st.info(f"📊 총 {len(filtered_data)}개 지역 중 상위 100개만 표시됩니다. 검색어를 입력하여 범위를 좁혀보세요.")
            
            df = pd.DataFrame([
                {k: v for k, v in row.items() if not k.startswith('_')} 
                for row in display_data
            ])
            
            # 상태별 색상 구분을 위한 스타일 적용
            def color_status(val):
                if "❌" in str(val):
                    return "background-color: #ffebee"  # 연한 빨강
                elif "✅" in str(val):
                    return "background-color: #e8f5e8"  # 연한 초록
                elif "🔄" in str(val):
                    return "background-color: #fff3e0"  # 연한 오렌지
                return ""
            
            styled_df = df.style.applymap(color_status, subset=['상태'])
            district_statuses["table_placeholder"].dataframe(
                styled_df, use_container_width=True, hide_index=True
            )
        else:
            district_statuses["table_placeholder"].info("검색 조건에 맞는 지역이 없습니다.")
    
    def update_district_status(district_key: str, status: str, details: str = "", results_count: int = 0):
        """지역별 상태 업데이트 (통합 테이블형)"""
        nonlocal completed_count
        
        district_name = district_key.replace('_', ' ')
        status_icons = {
            'pending': '⏳ 대기중',
            'running': '🔄 진행중', 
            'completed': '✅ 완료',
            'error': '❌ 오류'
        }
        
        status_display = status_icons.get(status, '❓ 알 수 없음')
        
        # 테이블 데이터 업데이트
        for row in district_statuses["table_data"]:
            if row["_key"] == district_key:
                row["상태"] = status_display
                row["진행률"] = f"{((completed_count + (1 if status == 'completed' else 0)) / total_districts * 100):.0f}%"
                row["결과"] = details if details else ""
                break
        
        # 테이블 다시 렌더링 (현재 필터 조건 유지)
        current_search = st.session_state.get("district_search", "")
        current_status = st.session_state.get("status_filter", "전체") 
        show_only_issues = False  # 기본값
        update_district_status_table(district_statuses, current_search, current_status, show_only_issues)
        
        # 완료된 경우 카운트 업데이트
        if status == 'completed':
            # 중복 완료 방지
            if not hasattr(update_district_status, '_completed_districts'):
                update_district_status._completed_districts = set()
            
            if district_key not in update_district_status._completed_districts:
                update_district_status._completed_districts.add(district_key)
                completed_count += 1
                
                # 전체 진행률 업데이트
                progress = completed_count / total_districts
                overall_progress.progress(progress)
                overall_status.text(f"진행 상황: {completed_count}/{total_districts} 지역 완료 ({progress*100:.1f}%)")
    
    # 함수 정의 완료 후 초기 테이블 표시
    update_district_status_table(district_statuses, search_filter, show_status, show_only_issues)
    
    try:
        add_log("모니터링 검사를 시작합니다...")
        overall_status.text("초기화 중...")
        
        # 등록된 링크 데이터 로드
        from src.domains.infrastructure.services.link_collector_service import load_registered_links
        registered_data = load_registered_links(config)
        links_data = registered_data.get("links", {})
        
        # 모니터링 이력 로드
        history_data = load_monitoring_history(config)
        
        add_log(f"검사 대상: {total_districts}개 지역")
        
        # 각 지역별 검사 실행 (순차적으로)
        for i, district_key in enumerate(districts_to_check):
            district_name = district_key.replace('_', ' ')
            add_log(f"[{i+1}/{total_districts}] {district_name} 검사 시작")
            
            update_district_status(district_key, 'running')
            
            try:
                if district_key not in links_data:
                    add_log(f"❌ {district_name}: 등록된 링크 정보 없음")
                    update_district_status(district_key, 'error', "등록된 링크 정보 없음")
                    continue
                
                district_data = links_data[district_key]
                
                # 지역별 검사 실행
                district_results = check_district_changes(
                    district_key, district_data, history_data, monitoring_config, config
                )
                
                # 결과 분석
                changed = sum(1 for r in district_results if r.status == 'changed')
                errors = sum(1 for r in district_results if r.status in ['error', 'unreachable'])
                ok = sum(1 for r in district_results if r.status == 'ok')
                
                status_summary = f"변경:{changed} 오류:{errors} 정상:{ok}"
                add_log(f"✅ {district_name}: {status_summary}")
                
                update_district_status(district_key, 'completed', status_summary)
                all_results.extend(district_results)
                
            except Exception as e:
                add_log(f"❌ {district_name}: 검사 실패 - {str(e)}")
                update_district_status(district_key, 'error', f"검사 실패: {str(e)}")
        
        # 최종 결과 처리
        overall_progress.progress(1.0)
        overall_status.text("알림 처리 중...")
        add_log("모든 지역 검사 완료. 알림 처리 중...")
        
        # 결과 요약 생성
        total_checked = len(all_results)
        changed_count = sum(1 for r in all_results if r.status == 'changed')
        error_count = sum(1 for r in all_results if r.status in ['error', 'unreachable'])
        ok_count = sum(1 for r in all_results if r.status == 'ok')
        
        # 알림 처리
        from src.domains.monitoring.services.notification_service import process_monitoring_results
        notification_result = process_monitoring_results(all_results, config)
        
        # 최종 상태 업데이트
        overall_status.success("✅ 모니터링 검사 완료!")
        add_log(f"📊 최종 결과: 총 {total_checked}개 검사, 변경 {changed_count}개, 오류 {error_count}개, 정상 {ok_count}개")
        
        if notification_result["sent_emails"] > 0:
            add_log(f"📧 {notification_result['sent_emails']}개 배치 요약 이메일 발송됨")
        
        # 결과를 세션 상태에 저장
        result_summary = {
            "total_checked": total_checked,
            "changed_count": changed_count,
            "error_count": error_count,
            "ok_count": ok_count,
            "districts": {},
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }
        
        # 지역별 결과 정리
        for district_key in districts_to_check:
            district_results_for_key = [r for r in all_results if r.district_key == district_key]
            result_summary["districts"][district_key] = {
                "total": len(district_results_for_key),
                "changed": sum(1 for r in district_results_for_key if r.status == 'changed'),
                "error": sum(1 for r in district_results_for_key if r.status in ['error', 'unreachable']),
                "ok": sum(1 for r in district_results_for_key if r.status == 'ok'),
                "results": [
                    {
                        "url_type": r.url_type,
                        "status": r.status,
                        "change_type": r.change_type,
                        "error_message": r.error_message,
                        "response_time": r.response_time
                    } for r in district_results_for_key
                ]
            }
        
        st.session_state.monitoring_result = result_summary
        st.session_state.notification_result = notification_result
        
        # 결과 요약 표시
        with results_container:
            st.divider()
            st.subheader("📊 검사 결과 요약")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 검사", total_checked)
            with col2:
                st.metric("변경됨", changed_count, delta=None if changed_count == 0 else f"+{changed_count}")
            with col3:
                st.metric("오류", error_count, delta=None if error_count == 0 else f"+{error_count}")
            with col4:
                st.metric("정상", ok_count)
        
    except Exception as e:
        add_log(f"❌ 치명적 오류: {str(e)}")
        overall_status.error(f"모니터링 검사 중 오류 발생: {str(e)}")
        st.error(f"모니터링 검사 중 오류가 발생했습니다: {str(e)}")
        import traceback
        add_log(f"상세 오류: {traceback.format_exc()}")
    
        saved_result = st.session_state.get("monitoring_result")
    render_saved_monitoring_results(saved_result)

def show_batch_management(config: Config):
    """
    배치 작업 관리 인터페이스를 표시합니다.
    """
    st.header("⚙️ 배치 작업 관리")
    
    # 배치 스케줄러 상태
    try:
        scheduler = get_batch_scheduler(config)
        status = scheduler.get_job_status()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            scheduler_status = "🟢 실행중" if status["scheduler_running"] else "🔴 중지됨"
            st.metric("스케줄러 상태", scheduler_status)
            
        with col2:
            st.metric("전체 작업", status["total_jobs"])
            
        with col3:
            st.metric("실행중인 작업", status["running_jobs"])
        
        # 스케줄러 제어
        col1, col2 = st.columns(2)
        
        with col1:
            if not status["scheduler_running"]:
                if st.button("▶️ 스케줄러 시작", type="primary"):
                    scheduler.start_scheduler()
                    st.success("스케줄러가 시작되었습니다.")
                    st.rerun()
            else:
                if st.button("⏹️ 스케줄러 중지", type="secondary"):
                    scheduler.stop_scheduler()
                    st.success("스케줄러가 중지되었습니다.")
                    st.rerun()
        
        # 작업 목록
        st.subheader("📋 배치 작업 목록")
        
        job_data = []
        for job in status["jobs"]:
            status_icon = {
                "completed": "✅",
                "running": "🔄",
                "failed": "❌",
                "pending": "⏳"
            }.get(job["status"], "❓")
            
            running_status = "🔄 실행중" if job["is_running"] else "⏸️ 대기"
            
            job_data.append({
                "상태": status_icon,
                "작업명": job["name"],
                "실행상태": running_status,
                "활성화": "🟢 ON" if job["enabled"] else "🔴 OFF",
                "마지막 실행": job["last_run"][:16] if job["last_run"] else "없음",
                "작업ID": job["id"]
            })
        
        df = pd.DataFrame(job_data)
        
        # 작업 선택을 위한 데이터프레임 표시
        selected_rows = st.dataframe(
            df.drop('작업ID', axis=1), 
            use_container_width=True, 
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        # 수동 실행
        st.subheader("🎮 수동 실행")
        
        job_options = {job["name"]: job["id"] for job in status["jobs"]}
        selected_job_name = st.selectbox(
            "실행할 작업 선택",
            options=list(job_options.keys()),
            help="선택한 작업을 즉시 실행합니다"
        )
        
        if st.button("🚀 작업 실행", type="primary"):
            selected_job_id = job_options[selected_job_name]
            
            # 이미 실행중인지 확인
            job_status = scheduler.get_job_status(selected_job_id)
            if job_status["is_running"]:
                st.error("선택한 작업이 이미 실행중입니다.")
            else:
                with st.spinner(f"{selected_job_name} 작업을 실행중입니다..."):
                    result = scheduler.run_job_manually(selected_job_id)
                    
                    if result["success"]:
                        st.success(f"✅ {selected_job_name} 작업이 성공적으로 완료되었습니다!")
                        
                        # 결과 상세 표시
                        if "result" in result and result["result"]:
                            with st.expander("실행 결과 상세"):
                                st.json(result["result"])
                    else:
                        st.error(f"❌ {selected_job_name} 작업 실행에 실패했습니다: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        st.error(f"배치 관리 시스템 로드 중 오류가 발생했습니다: {str(e)}")

def show_notification_history(config: Config):
    """
    알림 이력을 표시합니다.
    """
    st.header("📧 알림 이력")
    
    # 조회 기간 선택
    col1, col2 = st.columns(2)
    
    with col1:
        days = st.selectbox(
            "조회 기간",
            [7, 14, 30, 60],
            index=2,
            format_func=lambda x: f"최근 {x}일",
            help="알림 이력을 조회할 기간을 선택하세요"
        )
    
    with col2:
        priority_filter = st.multiselect(
            "우선순위 필터",
            ["critical", "high", "medium", "low"],
            default=["critical", "high", "medium"],
            help="표시할 알림의 우선순위를 선택하세요"
        )
    
    try:
        history = get_notification_history(config, days=days)
        
        if history["summary"]["total"] == 0:
            st.info(f"최근 {days}일간 알림이 없습니다.")
            return
        
        # 요약 통계
        st.subheader("📊 알림 통계")
        
        summary = history["summary"]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 알림", summary["total"])
        with col2:
            st.metric("긴급", summary["by_priority"].get("critical", 0))
        with col3:
            st.metric("높음", summary["by_priority"].get("high", 0))
        with col4:
            st.metric("보통", summary["by_priority"].get("medium", 0))
        
        # 알림 목록
        st.subheader("📋 알림 목록")
        
        # 우선순위 필터 적용
        filtered_events = []
        for event in history["events"]:
            if event.get("priority", "low") in priority_filter:
                filtered_events.append(event)
        
        if not filtered_events:
            st.info("선택한 조건에 해당하는 알림이 없습니다.")
            return
        
        # 알림 데이터 준비
        notification_data = []
        for event in filtered_events[:50]:  # 최근 50개만
            priority_icon = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "📝",
                "low": "ℹ️"
            }.get(event.get("priority", "low"), "📋")
            
            district_name = event.get("district_key", "").replace('_', ' ')
            created_time = datetime.fromisoformat(event["created_at"])
            
            notification_data.append({
                "우선순위": priority_icon,
                "제목": event["title"],
                "지역": district_name,
                "생성시간": created_time.strftime('%m-%d %H:%M'),
                "발송여부": "✅" if event.get("sent_at") else "❌",
                "이벤트ID": event["id"]
            })
        
        df = pd.DataFrame(notification_data)
        
        # 선택된 행의 상세 정보 표시
        selected_indices = st.dataframe(
            df.drop('이벤트ID', axis=1),
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        ).selection.rows
        
        # 선택된 알림의 상세 정보 표시
        if selected_indices:
            selected_idx = selected_indices[0]
            selected_event = filtered_events[selected_idx]
            
            with st.expander("📋 알림 상세 정보", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**제목**: {selected_event['title']}")
                    st.write(f"**지역**: {selected_event.get('district_key', '').replace('_', ' ')}")
                    st.write(f"**우선순위**: {selected_event.get('priority', 'low').upper()}")
                    
                with col2:
                    created_at = datetime.fromisoformat(selected_event["created_at"])
                    st.write(f"**생성시간**: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if selected_event.get("sent_at"):
                        sent_at = datetime.fromisoformat(selected_event["sent_at"])
                        st.write(f"**발송시간**: {sent_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        st.write("**발송시간**: 미발송")
                
                st.write("**메시지**:")
                st.write(selected_event["message"])
                
                # 메타데이터 표시
                if selected_event.get("metadata"):
                    with st.expander("🔍 기술적 상세정보"):
                        st.json(selected_event["metadata"])
    
    except Exception as e:
        st.error(f"알림 이력 로드 중 오류가 발생했습니다: {str(e)}")

def show_monitoring_settings(config: Config):
    """
    모니터링 설정 관리 인터페이스를 표시합니다.
    """
    st.header("⚙️ 모니터링 설정")
    
    # 현재 설정 로드
    notification_config = load_notification_config(config)
    notification_settings = load_notification_settings(config)
    
    # SMTP 상태 표시
    st.subheader("📡 SMTP 연결 상태")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if notification_config.email_user:
            st.success(f"📧 발송자: {notification_config.email_user}")
        else:
            st.error("❌ 발송자 이메일 미설정")
    
    with col2:
        if notification_config.email_password:
            st.success("🔑 SMTP 인증 정보 있음")
        else:
            st.error("❌ SMTP 비밀번호 미설정")
    
    with col3:
        status_color = "🟢" if notification_config.email_enabled else "🔴"
        st.info(f"{status_color} 이메일 알림: {'활성화' if notification_config.email_enabled else '비활성화'}")
    
    if not notification_config.email_enabled:
        st.warning("""
        ⚠️ **이메일 알림 설정이 필요합니다**
        
        환경변수(.env 파일)에 다음 설정을 추가하세요:
        ```
        NOTIFICATION_EMAIL_USER=ecoguide.ai@gmail.com
        NOTIFICATION_EMAIL_PASSWORD=your_gmail_app_password
        ```
        
        Gmail 앱 비밀번호 생성 방법:
        1. Google 계정 → 보안 → 2단계 인증 활성화
        2. 앱 비밀번호 생성 → "EcoGuide" 선택
        3. 생성된 16자리 비밀번호를 위 설정에 입력
        """)
    
    st.divider()
    
    # 수신자 관리
    st.subheader("👥 수신자 관리")
    
    recipients = notification_settings.get("email_recipients", [])
    
    # 현재 수신자 목록 표시
    if recipients:
        st.write("**현재 수신자 목록:**")
        for i, email in enumerate(recipients):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📧 {email}")
            with col2:
                if st.button("🗑️", key=f"delete_{i}", help=f"{email} 삭제"):
                    recipients.remove(email)
                    notification_settings["email_recipients"] = recipients
                    if save_notification_settings(notification_settings, config):
                        st.success(f"{email}을 삭제했습니다.")
                        st.rerun()
                    else:
                        st.error("삭제에 실패했습니다.")
    else:
        st.info("등록된 수신자가 없습니다. 아래에서 수신자를 추가하세요.")
    
    # 새 수신자 추가
    with st.form("add_recipient"):
        new_email = st.text_input(
            "새 수신자 이메일",
            placeholder="example@domain.com",
            help="알림을 받을 이메일 주소를 입력하세요"
        )
        
        if st.form_submit_button("➕ 수신자 추가"):
            if not new_email or '@' not in new_email:
                st.error("올바른 이메일 주소를 입력하세요.")
            elif new_email in recipients:
                st.warning("이미 등록된 이메일입니다.")
            else:
                recipients.append(new_email)
                notification_settings["email_recipients"] = recipients
                if save_notification_settings(notification_settings, config):
                    st.success(f"{new_email}을 추가했습니다.")
                    st.rerun()
                else:
                    st.error("추가에 실패했습니다.")
    
    st.divider()
    
    # 알림 주기 설정
    st.subheader("📬 알림 주기 설정")
    
    prefs = notification_settings.get("notification_preferences", {})
    
    with st.form("notification_preferences"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            critical_immediate = st.checkbox(
                "긴급 알림 (즉시)",
                value=prefs.get("critical_immediate", True),
                help="서비스 중단 등 긴급한 상황 시 즉시 알림"
            )
            
        with col2:
            high_daily = st.checkbox(
                "높은 우선순위 (일일)",
                value=prefs.get("high_daily_summary", True),
                help="페이지 변경 등 중요한 변화에 대한 일일 요약"
            )
            
        with col3:
            medium_weekly = st.checkbox(
                "보통 우선순위 (주간)",
                value=prefs.get("medium_weekly_summary", True),
                help="텍스트 변경 등에 대한 주간 요약"
            )
            
        with col4:
            low_monthly = st.checkbox(
                "낮은 우선순위 (월간)",
                value=prefs.get("low_monthly_summary", True),
                help="경미한 변경사항에 대한 월간 요약"
            )
        
        if st.form_submit_button("💾 알림 설정 저장"):
            notification_settings["notification_preferences"] = {
                "critical_immediate": critical_immediate,
                "high_daily_summary": high_daily,
                "medium_weekly_summary": medium_weekly,
                "low_monthly_summary": low_monthly
            }
            
            if save_notification_settings(notification_settings, config):
                st.success("✅ 알림 설정이 저장되었습니다.")
                st.rerun()
            else:
                st.error("❌ 설정 저장에 실패했습니다.")
    
    st.divider()
    
    # 테스트 이메일 발송
    st.subheader("📮 연결 테스트")
    
    if not notification_config.email_enabled:
        st.warning("⚠️ 이메일 설정이 비활성화되어 있습니다. 위의 SMTP 설정을 먼저 완료하세요.")
    else:
        with st.form("test_email"):
            test_recipient = st.text_input(
                "테스트 수신자",
                value=recipients[0] if recipients else "",
                placeholder="test@example.com",
                help="테스트 이메일을 받을 이메일 주소"
            )
            
            if st.form_submit_button("📧 테스트 이메일 발송"):
                if not test_recipient:
                    st.error("테스트 수신자 이메일을 입력하세요.")
                else:
                    with st.spinner("테스트 이메일 발송 중..."):
                        result = send_test_email(test_recipient, config, notification_config)
                    
                    if result["success"]:
                        st.success(f"✅ {result['message']}")
                        st.info(f"📤 발송 시간: {result['sent_at'][:19].replace('T', ' ')}")
                    else:
                        st.error(f"❌ {result['error']}")
                        
                        if "technical_error" in result:
                            with st.expander("🔍 상세 오류 정보"):
                                st.code(result["technical_error"])
        
        # 일일 요약 이메일 테스트
        st.write("**또는**")
        
        if st.button("📊 일일 요약 이메일 테스트 (실제 데이터)"):
            if not recipients:
                st.warning("먼저 수신자를 등록하세요.")
            else:
                with st.spinner("일일 요약 이메일 발송 중..."):
                    try:
                        success = send_daily_summary_email(config, notification_config)
                        
                        if success:
                            st.success("✅ 일일 요약 이메일이 성공적으로 발송되었습니다!")
                        else:
                            st.warning("⚠️ 전송할 내용이 없어 이메일을 발송하지 않았습니다.")
                            
                    except Exception as e:
                        st.error(f"❌ 일일 요약 이메일 발송에 실패했습니다: {str(e)}")
