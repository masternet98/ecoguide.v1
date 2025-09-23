"""
모니터링 시스템과 관리자 페이지 연동을 위한 통합 서비스입니다.
시군구별 오류 상태를 관리자 링크 관리 시스템과 연결합니다.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from src.app.core.config import Config
from src.domains.monitoring.services.monitoring_service import load_monitoring_history
from src.domains.infrastructure.services.link_collector_service import load_registered_links
from src.app.core.logger import log_info, log_error, LogCategory


@dataclass
class DistrictErrorStatus:
    """시군구 오류 상태 정보"""
    district_key: str
    district_name: str
    has_errors: bool
    error_count: int
    total_urls: int
    last_check: Optional[str] = None
    errors: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def get_district_error_status(district_key: str, config: Optional[Config] = None) -> DistrictErrorStatus:
    """
    특정 시군구의 오류 상태를 조회합니다.
    
    Args:
        district_key: 시군구 키 (예: "서울특별시_종로구")
        config: 애플리케이션 설정
        
    Returns:
        시군구 오류 상태 정보
    """
    history_data = load_monitoring_history(config)
    district_history = history_data.get("districts", {}).get(district_key, {})
    
    # 시군구명 추출
    district_name = district_key.replace('_', ' ') if district_key else "Unknown"
    
    # URL 타입별 오류 확인
    url_types = ["info_url", "system_url", "fee_url", "appliance_url"]
    errors = []
    total_urls = 0
    
    for url_type in url_types:
        status_key = f"{url_type}_last_status"
        error_key = f"{url_type}_last_error"
        check_key = f"{url_type}_last_checked"
        
        status = district_history.get(status_key)
        if status:  # 검사된 적이 있는 URL
            total_urls += 1
            
            if status in ['error', 'unreachable']:
                url_type_names = {
                    'info_url': '배출정보',
                    'system_url': '시스템',
                    'fee_url': '수수료',
                    'appliance_url': '폐가전제품'
                }
                
                errors.append({
                    'url_type': url_type,
                    'url_type_name': url_type_names.get(url_type, url_type),
                    'status': status,
                    'error_message': district_history.get(error_key, 'Unknown error'),
                    'last_checked': district_history.get(check_key),
                    'severity': 'critical' if status == 'unreachable' else 'high'
                })
    
    return DistrictErrorStatus(
        district_key=district_key,
        district_name=district_name,
        has_errors=len(errors) > 0,
        error_count=len(errors),
        total_urls=total_urls,
        last_check=district_history.get("last_checked"),
        errors=errors
    )


def get_all_districts_error_summary(config: Optional[Config] = None) -> Dict[str, Any]:
    """
    모든 시군구의 오류 상태 요약을 조회합니다.
    
    Args:
        config: 애플리케이션 설정
        
    Returns:
        전체 오류 상태 요약
    """
    registered_data = load_registered_links(config)
    links_data = registered_data.get("links", {})
    
    summary = {
        "total_districts": len(links_data),
        "districts_with_errors": 0,
        "total_errors": 0,
        "error_districts": [],
        "healthy_districts": [],
        "never_checked": []
    }
    
    for district_key in links_data.keys():
        error_status = get_district_error_status(district_key, config)
        
        if error_status.has_errors:
            summary["districts_with_errors"] += 1
            summary["total_errors"] += error_status.error_count
            summary["error_districts"].append(error_status)
        elif error_status.last_check:
            summary["healthy_districts"].append(error_status)
        else:
            summary["never_checked"].append(error_status)
    
    # 오류가 많은 순으로 정렬
    summary["error_districts"].sort(key=lambda x: x.error_count, reverse=True)
    
    return summary


def get_filtered_districts(error_filter: str = "전체", 
                          search_query: str = "",
                          config: Optional[Config] = None) -> List[DistrictErrorStatus]:
    """
    필터링 조건에 따라 시군구 목록을 조회합니다.
    
    Args:
        error_filter: 오류 필터 ("전체", "오류 있음", "오류 없음", "미검사")
        search_query: 검색어 (시군구명 검색)
        config: 애플리케이션 설정
        
    Returns:
        필터링된 시군구 상태 목록
    """
    registered_data = load_registered_links(config)
    links_data = registered_data.get("links", {})
    
    filtered_districts = []
    
    for district_key in links_data.keys():
        error_status = get_district_error_status(district_key, config)
        
        # 검색어 필터링
        if search_query and search_query.lower() not in error_status.district_name.lower():
            continue
        
        # 오류 상태 필터링
        if error_filter == "오류 있음" and not error_status.has_errors:
            continue
        elif error_filter == "오류 없음" and (error_status.has_errors or not error_status.last_check):
            continue
        elif error_filter == "미검사" and error_status.last_check:
            continue
        
        filtered_districts.append(error_status)
    
    # 오류가 있는 지역을 우선 정렬, 그 다음 이름순 정렬
    filtered_districts.sort(
        key=lambda x: (not x.has_errors, x.error_count == 0, x.district_name)
    )
    
    return filtered_districts


def mark_error_as_acknowledged(district_key: str, url_type: str, 
                              config: Optional[Config] = None) -> bool:
    """
    오류를 확인했음으로 표시합니다 (향후 기능 확장용).
    
    Args:
        district_key: 시군구 키
        url_type: URL 타입
        config: 애플리케이션 설정
        
    Returns:
        성공 여부
    """
    # 향후 확장: 오류 확인 상태 추적
    # 현재는 로그만 남김
    log_info(
        LogCategory.USER_ACTION, "monitoring_admin_integration", "mark_error_as_acknowledged",
        f"오류 확인됨: {district_key} - {url_type}", ""
    )
    return True


def get_error_statistics_for_dashboard(config: Optional[Config] = None) -> Dict[str, Any]:
    """
    관리자 대시보드용 오류 통계를 생성합니다.
    
    Args:
        config: 애플리케이션 설정
        
    Returns:
        대시보드용 통계 데이터
    """
    summary = get_all_districts_error_summary(config)
    
    return {
        "metrics": {
            "total_districts": summary["total_districts"],
            "healthy_districts": len(summary["healthy_districts"]),
            "error_districts": summary["districts_with_errors"],
            "never_checked": len(summary["never_checked"]),
            "total_errors": summary["total_errors"]
        },
        "error_breakdown": {
            "critical": sum(1 for d in summary["error_districts"] 
                          for e in d.errors if e.get("severity") == "critical"),
            "high": sum(1 for d in summary["error_districts"] 
                       for e in d.errors if e.get("severity") == "high")
        },
        "top_error_districts": summary["error_districts"][:5]  # 상위 5개 문제 지역
    }