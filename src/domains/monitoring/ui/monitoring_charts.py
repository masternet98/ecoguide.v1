"""Presentation helpers for monitoring dashboard tables and charts."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from .monitoring_data import district_has_issue, iter_district_items, status_icon, url_type_label


def display_recent_changes_table(dataframe: pd.DataFrame) -> None:
    """Render the recent changes table."""
    st.dataframe(dataframe, use_container_width=True, hide_index=True)


def display_error_table(dataframe: pd.DataFrame) -> None:
    """Render the error districts table."""
    st.dataframe(dataframe, use_container_width=True, hide_index=True)


def render_saved_monitoring_results(saved_result: Dict[str, Any]) -> None:
    """Render the detailed monitoring results stored in session state."""
    if not saved_result:
        return

    st.divider()
    st.subheader("📋 상세 모니터링 결과")

    for district_key, district_result in saved_result.get("districts", {}).items():
        has_issues = district_has_issue(district_result)
        status_summary = "⚠️ 문제 발생" if has_issues else "✅ 정상"
        title = f"{district_key.replace('_', ' ')} ({status_summary}, 총 {district_result.get('total', 0)}개)"

        with st.expander(title, expanded=has_issues):
            for item_result in iter_district_items(district_result):
                status = item_result.get("status", "")
                icon = status_icon(status)
                url_label = url_type_label(item_result.get("url_type", ""))

                col1, col2, col3 = st.columns([2, 1, 3])

                with col1:
                    st.write(f"{icon} **{url_label}**")

                with col2:
                    status_upper = status.upper()
                    if status == "ok":
                        st.success(status_upper)
                    elif status == "changed":
                        st.warning(status_upper)
                    else:
                        st.error(status_upper)

                with col3:
                    if item_result.get("error_message"):
                        st.write(f"⚠️ {item_result['error_message']}")
                    elif item_result.get("response_time"):
                        st.write(f"⏱️ {item_result['response_time']:.2f}초")
                    else:
                        st.write("ℹ️ 처리 정보 없음")
