"""
시군구별 등록 정보의 변경 감지를 위한 모니터링 서비스 모듈입니다.
URL과 첨부파일의 변경사항을 자동으로 감지하고 이력을 관리합니다.
"""
import hashlib
import json
import os
import requests
import ssl
import urllib3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
import re
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from src.core.config import Config
from src.core.logger import log_error, log_info, LogCategory
from src.services.link_collector_service import load_registered_links, get_storage_filepath

# SSL 경고 메시지 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacyHTTPSAdapter(HTTPAdapter):
    """
    Legacy SSL 연결을 위한 HTTP 어댑터
    오래된 서버의 SSL 핸드셰이크 실패를 해결합니다.
    """
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')  # 보안 수준 낮춤
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super(LegacyHTTPSAdapter, self).init_poolmanager(*args, **kwargs)

@dataclass
class MonitoringResult:
    """모니터링 결과를 담는 데이터 클래스"""
    district_key: str
    url_type: str
    status: str  # 'ok', 'changed', 'error', 'unreachable'
    change_type: Optional[str] = None  # 'content', 'structure', 'status', 'file'
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    error_message: Optional[str] = None
    response_time: Optional[float] = None
    checked_at: Optional[str] = None

@dataclass
class MonitoringConfig:
    """모니터링 설정"""
    check_interval_hours: int = 24
    request_timeout: int = 30
    max_concurrent_checks: int = 5
    retry_attempts: int = 3
    retry_delay: int = 5
    ignore_minor_changes: bool = True
    keywords_to_track: List[str] = None
    
    def __post_init__(self):
        if self.keywords_to_track is None:
            self.keywords_to_track = [
                "대형폐기물", "신고", "배출", "수수료", "가전", "접수", "예약"
            ]

def get_monitoring_storage_path(config: Optional[Config] = None) -> str:
    """
    모니터링 데이터가 저장될 디렉토리 경로를 반환합니다.
    
    Args:
        config: 앱 설정
        
    Returns:
        모니터링 저장 디렉토리 경로
    """
    if config is None:
        from src.core.config import load_config
        config = load_config()
    
    base_dir = os.path.dirname(config.district.uploads_dir)
    monitoring_dir = os.path.join(base_dir, 'monitoring')
    os.makedirs(monitoring_dir, exist_ok=True)
    return monitoring_dir

def get_monitoring_history_path(config: Optional[Config] = None) -> str:
    """모니터링 이력 파일 경로를 반환합니다."""
    storage_dir = get_monitoring_storage_path(config)
    return os.path.join(storage_dir, "monitoring_history.json")

def get_url_content_hash(url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """
    URL의 콘텐츠 해시값을 계산합니다.
    
    Args:
        url: 확인할 URL
        timeout: 요청 타임아웃 (초)
        
    Returns:
        (해시값, 에러메시지, 응답시간) 튜플
    """
    try:
        start_time = datetime.now()
        
        # User-Agent 헤더 추가로 봇 차단 회피
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        }
        
        # SSL 호환성을 위한 세션 생성
        session = requests.Session()
        session.mount('https://', LegacyHTTPSAdapter())
        
        response = session.get(url, timeout=timeout, verify=False, headers=headers)
        response_time = (datetime.now() - start_time).total_seconds()
        
        if response.status_code == 200:
            # HTML 콘텐츠에서 동적 요소 제거 (날짜, 시간 등)
            content = response.text
            # 타임스탬프, 날짜 등 동적 콘텐츠 제거
            content = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', content)
            content = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', content)
            content = re.sub(r'timestamp=\d+', 'timestamp=TIMESTAMP', content)
            
            # 해시 계산
            hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()
            return hash_value, None, response_time
        else:
            return None, f"HTTP {response.status_code}", response_time
            
    except requests.exceptions.Timeout:
        return None, "Timeout", None
    except requests.exceptions.ConnectionError:
        return None, "Connection Error", None
    except Exception as e:
        return None, str(e), None

def get_file_content_hash(file_path: str) -> Optional[str]:
    """
    파일의 콘텐츠 해시값을 계산합니다.
    
    Args:
        file_path: 파일 경로
        
    Returns:
        파일 해시값 또는 None
    """
    try:
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.md5(content).hexdigest()
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "monitoring_service", "get_file_content_hash",
            "파일 해시 계산 실패", f"File: {file_path}, Error: {str(e)}", error=e
        )
        return None

def extract_keywords_from_url(url: str, keywords: List[str]) -> List[str]:
    """
    URL에서 특정 키워드들을 추출합니다.
    
    Args:
        url: 확인할 URL
        keywords: 찾을 키워드 목록
        
    Returns:
        발견된 키워드 목록
    """
    try:
        # User-Agent 헤더 추가로 봇 차단 회피
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        }
        
        # SSL 호환성을 위한 세션 생성
        session = requests.Session()
        session.mount('https://', LegacyHTTPSAdapter())
        
        response = session.get(url, timeout=30, verify=False, headers=headers)
        if response.status_code == 200:
            content = response.text.lower()
            found_keywords = []
            for keyword in keywords:
                if keyword.lower() in content:
                    found_keywords.append(keyword)
            return found_keywords
    except Exception:
        pass
    return []

def load_monitoring_history(config: Optional[Config] = None) -> Dict[str, Any]:
    """
    모니터링 이력을 로드합니다.
    
    Args:
        config: 앱 설정
        
    Returns:
        모니터링 이력 데이터
    """
    filepath = get_monitoring_history_path(config)
    if not os.path.exists(filepath):
        return {
            "metadata": {
                "last_full_check": None,
                "total_checks": 0,
                "created_at": datetime.now().isoformat()
            },
            "districts": {}
        }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "monitoring_service", "load_monitoring_history",
            "모니터링 이력 로드 실패", f"Error: {str(e)}", error=e
        )
        return {"metadata": {}, "districts": {}}

def save_monitoring_history(history_data: Dict[str, Any], config: Optional[Config] = None) -> bool:
    """
    모니터링 이력을 저장합니다.
    
    Args:
        history_data: 저장할 이력 데이터
        config: 앱 설정
        
    Returns:
        성공 여부
    """
    filepath = get_monitoring_history_path(config)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "monitoring_service", "save_monitoring_history",
            "모니터링 이력 저장 실패", f"Error: {str(e)}", error=e
        )
        return False

def check_single_url(district_key: str, url_type: str, url: str, 
                    previous_data: Dict[str, Any], 
                    monitoring_config: MonitoringConfig) -> MonitoringResult:
    """
    단일 URL의 변경사항을 확인합니다.
    
    Args:
        district_key: 시군구 키
        url_type: URL 타입
        url: 확인할 URL
        previous_data: 이전 모니터링 데이터
        monitoring_config: 모니터링 설정
        
    Returns:
        모니터링 결과
    """
    if not url or url.strip() == "":
        return MonitoringResult(
            district_key=district_key,
            url_type=url_type,
            status='ok',
            checked_at=datetime.now().isoformat()
        )
    
    # 이전 해시값 가져오기
    url_key = f"{url_type}_hash"
    previous_hash = previous_data.get(url_key)
    
    # 현재 해시값 계산
    current_hash, error_message, response_time = get_url_content_hash(
        url, monitoring_config.request_timeout
    )
    
    result = MonitoringResult(
        district_key=district_key,
        url_type=url_type,
        status='ok',  # 기본값 설정
        current_hash=current_hash,
        previous_hash=previous_hash,
        response_time=response_time,
        checked_at=datetime.now().isoformat()
    )
    
    if error_message:
        result.status = 'error' if current_hash is None else 'unreachable'
        result.error_message = error_message
    elif current_hash != previous_hash:
        result.status = 'changed'
        result.change_type = 'content'
    else:
        result.status = 'ok'
    
    return result

def check_single_file(district_key: str, url_type: str, file_info: Dict[str, Any],
                     previous_data: Dict[str, Any],
                     config: Optional[Config] = None) -> MonitoringResult:
    """
    단일 파일의 변경사항을 확인합니다.
    
    Args:
        district_key: 시군구 키
        url_type: URL 타입
        file_info: 파일 정보
        previous_data: 이전 모니터링 데이터
        config: 앱 설정
        
    Returns:
        모니터링 결과
    """
    if not file_info:
        return MonitoringResult(
            district_key=district_key,
            url_type=url_type,
            status='ok',
            checked_at=datetime.now().isoformat()
        )
    
    file_path = file_info.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return MonitoringResult(
            district_key=district_key,
            url_type=url_type,
            status='error',
            error_message='File not found',
            checked_at=datetime.now().isoformat()
        )
    
    # 이전 해시값 가져오기
    file_key = f"{url_type}_file_hash"
    previous_hash = previous_data.get(file_key)
    
    # 현재 해시값 계산
    current_hash = get_file_content_hash(file_path)
    
    result = MonitoringResult(
        district_key=district_key,
        url_type=url_type,
        status='ok',  # 기본값 설정
        current_hash=current_hash,
        previous_hash=previous_hash,
        checked_at=datetime.now().isoformat()
    )
    
    if current_hash is None:
        result.status = 'error'
        result.error_message = 'Failed to calculate file hash'
    elif current_hash != previous_hash:
        result.status = 'changed'
        result.change_type = 'file'
    else:
        result.status = 'ok'
    
    return result

def check_district_changes(district_key: str, district_data: Dict[str, Any],
                          history_data: Dict[str, Any],
                          monitoring_config: MonitoringConfig,
                          config: Optional[Config] = None) -> List[MonitoringResult]:
    """
    특정 시군구의 모든 URL과 파일 변경사항을 확인합니다.
    
    Args:
        district_key: 시군구 키
        district_data: 시군구 데이터
        history_data: 모니터링 이력 데이터
        monitoring_config: 모니터링 설정
        config: 앱 설정
        
    Returns:
        모니터링 결과 목록
    """
    results = []
    previous_data = history_data.get("districts", {}).get(district_key, {})
    
    # URL 타입별로 확인
    url_types = ["info_url", "system_url", "fee_url", "appliance_url"]
    
    for url_type in url_types:
        # URL 확인
        url = district_data.get(url_type, "")
        if url and url.strip():
            result = check_single_url(
                district_key, url_type, url, previous_data, monitoring_config
            )
            results.append(result)
        
        # 파일 확인
        file_key = f"{url_type}_file"
        file_info = district_data.get(file_key)
        if file_info:
            result = check_single_file(
                district_key, url_type, file_info, previous_data, config
            )
            results.append(result)
    
    return results

def run_monitoring_check(config: Optional[Config] = None,
                        monitoring_config: Optional[MonitoringConfig] = None,
                        district_filter: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    전체 모니터링 검사를 실행합니다.
    
    Args:
        config: 앱 설정
        monitoring_config: 모니터링 설정
        district_filter: 특정 지역만 확인할 경우 지역 키 목록
        
    Returns:
        모니터링 결과 요약
    """
    if monitoring_config is None:
        monitoring_config = MonitoringConfig()
    
    log_info(
        LogCategory.SYSTEM, "monitoring_service", "run_monitoring_check",
        "모니터링 검사 시작", f"Districts filter: {district_filter}"
    )
    
    # 등록된 링크 데이터 로드
    registered_data = load_registered_links(config)
    links_data = registered_data.get("links", {})
    
    # 모니터링 이력 로드
    history_data = load_monitoring_history(config)
    
    # 검사할 지역 결정
    districts_to_check = district_filter if district_filter else list(links_data.keys())
    
    all_results = []
    summary = {
        "total_checked": 0,
        "changed_count": 0,
        "error_count": 0,
        "ok_count": 0,
        "started_at": datetime.now().isoformat(),
        "districts": {}
    }
    
    # 각 지역별로 검사 실행
    for district_key in districts_to_check:
        if district_key not in links_data:
            continue
            
        district_data = links_data[district_key]
        results = check_district_changes(
            district_key, district_data, history_data, monitoring_config, config
        )
        
        all_results.extend(results)
        
        # 지역별 요약 생성
        district_summary = {
            "total": len(results),
            "changed": sum(1 for r in results if r.status == 'changed'),
            "error": sum(1 for r in results if r.status in ['error', 'unreachable']),
            "ok": sum(1 for r in results if r.status == 'ok'),
            "results": [
                {
                    "url_type": r.url_type,
                    "status": r.status,
                    "change_type": r.change_type,
                    "error_message": r.error_message,
                    "response_time": r.response_time
                } for r in results
            ]
        }
        
        summary["districts"][district_key] = district_summary
        summary["total_checked"] += district_summary["total"]
        summary["changed_count"] += district_summary["changed"]
        summary["error_count"] += district_summary["error"]
        summary["ok_count"] += district_summary["ok"]
    
    # 이력 데이터 업데이트
    update_monitoring_history(all_results, history_data, config)
    
    summary["completed_at"] = datetime.now().isoformat()
    
    log_info(
        LogCategory.SYSTEM, "monitoring_service", "run_monitoring_check",
        "모니터링 검사 완료", 
        f"Total: {summary['total_checked']}, Changed: {summary['changed_count']}, Error: {summary['error_count']}"
    )
    
    return summary

def update_monitoring_history(results: List[MonitoringResult], 
                             history_data: Dict[str, Any],
                             config: Optional[Config] = None) -> bool:
    """
    모니터링 결과를 이력에 반영합니다.
    
    Args:
        results: 모니터링 결과 목록
        history_data: 기존 이력 데이터
        config: 앱 설정
        
    Returns:
        성공 여부
    """
    now = datetime.now().isoformat()
    
    # 메타데이터 업데이트
    if "metadata" not in history_data:
        history_data["metadata"] = {}
    
    history_data["metadata"]["last_full_check"] = now
    history_data["metadata"]["total_checks"] = history_data["metadata"].get("total_checks", 0) + 1
    
    if "districts" not in history_data:
        history_data["districts"] = {}
    
    # 결과별로 이력 업데이트
    for result in results:
        district_key = result.district_key
        
        if district_key not in history_data["districts"]:
            history_data["districts"][district_key] = {}
        
        district_history = history_data["districts"][district_key]
        
        # 해시값 저장
        if result.current_hash:
            if result.url_type.endswith('_file'):
                hash_key = f"{result.url_type}_hash"
            else:
                hash_key = f"{result.url_type}_hash"
            district_history[hash_key] = result.current_hash
        
        # 최근 검사 정보 저장
        district_history["last_checked"] = now
        district_history[f"{result.url_type}_last_status"] = result.status
        district_history[f"{result.url_type}_last_checked"] = result.checked_at
        
        if result.error_message:
            district_history[f"{result.url_type}_last_error"] = result.error_message
        
        # 변경 이력 저장
        if result.status == 'changed':
            if "change_history" not in district_history:
                district_history["change_history"] = []
            
            district_history["change_history"].append({
                "url_type": result.url_type,
                "change_type": result.change_type,
                "previous_hash": result.previous_hash,
                "current_hash": result.current_hash,
                "changed_at": result.checked_at
            })
            
            # 최근 10개만 유지
            district_history["change_history"] = district_history["change_history"][-10:]
    
    return save_monitoring_history(history_data, config)

def get_monitoring_summary(config: Optional[Config] = None, 
                          days: int = 7) -> Dict[str, Any]:
    """
    최근 모니터링 결과 요약을 반환합니다.
    
    Args:
        config: 앱 설정
        days: 조회할 최근 일수
        
    Returns:
        모니터링 요약 정보
    """
    history_data = load_monitoring_history(config)
    
    summary = {
        "overview": {
            "total_districts": len(history_data.get("districts", {})),
            "last_check": history_data.get("metadata", {}).get("last_full_check"),
            "total_checks": history_data.get("metadata", {}).get("total_checks", 0)
        },
        "recent_changes": [],
        "error_districts": [],
        "healthy_districts": 0
    }
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for district_key, district_data in history_data.get("districts", {}).items():
        has_errors = False
        recent_changes = []
        
        # 변경 이력 확인
        for change in district_data.get("change_history", []):
            change_time = datetime.fromisoformat(change["changed_at"])
            if change_time >= cutoff_date:
                recent_changes.append({
                    "district": district_key,
                    "url_type": change["url_type"],
                    "change_type": change["change_type"],
                    "changed_at": change["changed_at"]
                })
        
        # 에러 상태 확인 ('changed' 상태는 정상으로 판정)
        for url_type in ["info_url", "system_url", "fee_url", "appliance_url"]:
            status_key = f"{url_type}_last_status"
            error_key = f"{url_type}_last_error"
            
            # 상태값 가져오기 (None이면 정상으로 처리)
            status = district_data.get(status_key)
            
            # 'error'와 'unreachable' 상태만 오류로 판정
            # 'changed', 'ok', None 상태는 모두 정상으로 처리
            if status in ['error', 'unreachable']:
                has_errors = True
                summary["error_districts"].append({
                    "district": district_key,
                    "url_type": url_type,
                    "status": status,
                    "error": district_data.get(error_key, "Unknown error")
                })
        
        if not has_errors:
            summary["healthy_districts"] += 1
        
        summary["recent_changes"].extend(recent_changes)
    
    # 최근 변경사항 정렬 (최신 순)
    summary["recent_changes"].sort(key=lambda x: x["changed_at"], reverse=True)
    summary["recent_changes"] = summary["recent_changes"][:20]  # 최근 20개만
    
    return summary