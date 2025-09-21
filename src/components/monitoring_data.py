"""Data utilities for monitoring dashboard views."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

_URL_TYPE_LABELS = {
    "info_url": "배출정보",
    "system_url": "시스템",
    "fee_url": "배출수수료",
    "appliance_url": "배출용품",
}

_STATUS_ICONS = {
    "ok": "✅",
    "changed": "⚠️",
    "error": "❌",
    "unreachable": "🚫",
}


def build_recent_changes_table(summary: Dict[str, Any], limit: int = 10) -> Optional[pd.DataFrame]:
    """Return a dataframe describing recent monitoring changes."""
    recent_changes: Iterable[Dict[str, Any]] = summary.get("recent_changes", []) if summary else []
    rows: List[Dict[str, Any]] = []

    for change in list(recent_changes)[:limit]:
        district_name = change.get("district", "").replace("_", " ")
        url_type = _URL_TYPE_LABELS.get(change.get("url_type"), change.get("url_type", ""))
        change_time = change.get("changed_at")
        timestamp = (
            datetime.fromisoformat(change_time).strftime("%m-%d %H:%M")
            if isinstance(change_time, str)
            else ""
        )
        rows.append(
            {
                "지역": district_name,
                "구분": url_type,
                "변경 유형": change.get("change_type", ""),
                "변경 시각": timestamp,
            }
        )

    if not rows:
        return None

    return pd.DataFrame(rows)


def build_error_table(summary: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """Return a dataframe describing districts with errors."""
    error_districts: Iterable[Dict[str, Any]] = summary.get("error_districts", []) if summary else []
    rows: List[Dict[str, Any]] = []

    for error in error_districts:
        district_name = error.get("district", "").replace("_", " ")
        url_type = _URL_TYPE_LABELS.get(error.get("url_type"), error.get("url_type", ""))
        rows.append(
            {
                "지역": district_name,
                "구분": url_type,
                "상태": error.get("status", ""),
                "오류": error.get("error", ""),
            }
        )

    if not rows:
        return None

    return pd.DataFrame(rows)


def status_icon(status: str) -> str:
    """Return an icon for a monitoring status value."""
    return _STATUS_ICONS.get(status, "ℹ️")


def url_type_label(key: str) -> str:
    """Return a human readable label for a monitoring url type."""
    return _URL_TYPE_LABELS.get(key, key)


def resolve_selected_districts(
    district_keys: List[str],
    selected_names: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """Map user selected district labels back to storage keys."""
    if not selected_names:
        return None

    mapped = []
    labelled_keys = [key.replace("_", " ") for key in district_keys]
    for name in selected_names:
        if name in labelled_keys:
            mapped.append(district_keys[labelled_keys.index(name)])
    return mapped or None


def summarize_run_progress(statuses: Dict[str, str]) -> Tuple[int, int, int]:
    """Return summary counts for pending, running and completed districts."""
    pending = sum(1 for value in statuses.values() if value == "pending")
    running = sum(1 for value in statuses.values() if value == "running")
    completed = sum(1 for value in statuses.values() if value == "completed")
    return pending, running, completed


def district_has_issue(result: Dict[str, Any]) -> bool:
    """Determine whether a monitoring result contains issues."""
    if not result:
        return False
    return bool(result.get("changed")) or bool(result.get("error"))


def iter_district_items(result: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield individual monitoring items for a district result."""
    for item in result.get("results", []):
        yield item
