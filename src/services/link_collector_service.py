"""
시군구별 대형폐기물 배출 신고 링크를 수동으로 관리하기 위한 서비스 모듈입니다.
관리자가 직접 등록한 링크를 저장, 조회, 수정, 삭제하는 CRUD 기능을 제공합니다.
데이터 모델은 확장성을 고려하여 여러 종류의 URL과 메타데이터를 포함할 수 있습니다.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.core.config import Config
from src.core.logger import log_error, log_info, LogCategory

def get_districts_data(config: Optional[Config] = None) -> List[Dict[str, Any]]:
    """
    districts.json 파일에서 시군구 데이터를 로드합니다.
    가장 최신 districts 파일을 찾아 사용합니다.

    Args:
        config: 앱 설정 (None이면 기본 config 사용)

    Returns:
        시군구 데이터 리스트
    """
    if config is None:
        from src.core.config import load_config
        config = load_config()

    uploads_dir = config.district.uploads_dir
    if not os.path.exists(uploads_dir):
        return []

    district_files = []
    for filename in os.listdir(uploads_dir):
        if filename.startswith('districts_') and filename.endswith('.json'):
            file_path = os.path.join(uploads_dir, filename)
            try:
                stat = os.stat(file_path)
                district_files.append({'path': file_path, 'mtime': stat.st_mtime})
            except OSError:
                continue

    if not district_files:
        return []

    latest_file = max(district_files, key=lambda x: x['mtime'])
    try:
        with open(latest_file['path'], 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('districts', [])
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "link_collector_service", "get_districts_data",
            "Districts 파일 로드 실패", f"Error: {str(e)}", error=e
        )
        return []

def get_waste_links_storage_path(config: Optional[Config] = None) -> str:
    """
    폐기물 링크 데이터가 저장될 디렉토리 경로를 반환합니다.
    없으면 생성합니다.

    Args:
        config: 앱 설정

    Returns:
        저장 디렉토리 경로
    """
    if config is None:
        from src.core.config import load_config
        config = load_config()

    base_dir = os.path.dirname(config.district.uploads_dir)
    waste_links_dir = os.path.join(base_dir, 'waste_links')
    os.makedirs(waste_links_dir, exist_ok=True)
    return waste_links_dir

def get_storage_filepath(config: Optional[Config] = None) -> str:
    """
    데이터를 저장할 파일의 전체 경로를 반환합니다.

    Args:
        config: 앱 설정

    Returns:
        데이터 파일 경로
    """
    storage_dir = get_waste_links_storage_path(config)
    return os.path.join(storage_dir, "waste_links_manual.json")

def load_registered_links(config: Optional[Config] = None) -> Dict[str, Any]:
    """
    저장된 링크 데이터를 로드합니다. 파일이 없으면 기본 구조를 반환합니다.

    Args:
        config: 앱 설정

    Returns:
        기존 링크 데이터 또는 기본 딕셔너리
    """
    filepath = get_storage_filepath(config)
    if not os.path.exists(filepath):
        return {"metadata": {}, "links": {}}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log_error(
            LogCategory.FILE_OPERATION, "link_collector_service", "load_registered_links",
            "링크 파일 로드 실패", f"File: {filepath}, Error: {str(e)}", error=e
        )
        return {"metadata": {}, "links": {}}

def save_link(district_key: str, link_data: Dict[str, str], config: Optional[Config] = None) -> bool:
    """
    특정 시군구의 링크 정보를 저장하거나 업데이트합니다.

    Args:
        district_key: 시군구를 식별하는 고유 키 (예: "서울특별시_강남구")
        link_data: 저장할 링크 정보 딕셔너리 (info_url, system_url, description 포함)
        config: 앱 설정

    Returns:
        성공 여부 (True/False)
    """
    data = load_registered_links(config)
    
    # 기존 데이터가 있으면 업데이트, 없으면 새로 생성
    if district_key not in data["links"]:
        data["links"][district_key] = {}
        
    data["links"][district_key]["info_url"] = link_data.get("info_url", "")
    data["links"][district_key]["system_url"] = link_data.get("system_url", "")
    data["links"][district_key]["fee_url"] = link_data.get("fee_url", "")
    data["links"][district_key]["description"] = link_data.get("description", "")
    data["links"][district_key]["updated_at"] = datetime.now().isoformat()
    
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    
    filepath = get_storage_filepath(config)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_info(
            LogCategory.FILE_OPERATION, "link_collector_service", "save_link",
            "링크 저장 성공", f"District: {district_key}"
        )
        return True
    except IOError as e:
        log_error(
            LogCategory.FILE_OPERATION, "link_collector_service", "save_link",
            "링크 저장 실패", f"File: {filepath}, Error: {str(e)}", error=e
        )
        return False

def delete_link(district_key: str, config: Optional[Config] = None) -> bool:
    """
    특정 시군구의 링크 정보를 삭제합니다.

    Args:
        district_key: 삭제할 시군구의 고유 키
        config: 앱 설정

    Returns:
        성공 여부 (True/False)
    """
    data = load_registered_links(config)
    
    if district_key in data["links"]:
        del data["links"][district_key]
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        
        filepath = get_storage_filepath(config)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log_info(
                LogCategory.FILE_OPERATION, "link_collector_service", "delete_link",
                "링크 삭제 성공", f"District: {district_key}"
            )
            return True
        except IOError as e:
            log_error(
                LogCategory.FILE_OPERATION, "link_collector_service", "delete_link",
                "링크 삭제 실패", f"File: {filepath}, Error: {str(e)}", error=e
            )
            return False
    else:
        # 삭제할 키가 없는 경우도 성공으로 처리
        return True