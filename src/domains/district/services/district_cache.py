"""
행정구역 데이터 파일 관리 및 캐시 모듈

이 모듈은 행정구역 JSON 파일의 저장, 조회, 삭제 등 파일 관리 작업을 담당합니다.
uploads 디렉토리의 파일 관리, 파일 메타데이터 조회, 파일 정리 작업 등을 수행합니다.
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.app.core.logger import logger, log_info, log_warning, log_error
from src.app.core.config import DistrictConfig


def get_district_files(config: Optional[DistrictConfig] = None) -> List[Dict[str, Any]]:
    """
    uploads 폴더의 행정구역 JSON 파일 목록을 반환합니다.

    Args:
        config: District 설정 (None이면 기본 config 사용)

    Returns:
        파일 정보 리스트 (파일명, 경로, 크기, 생성일시)
    """
    # Config 로드
    if config is None:
        from src.app.core.config import load_config
        config = load_config().district

    uploads_dir = config.uploads_dir
    if not os.path.exists(uploads_dir):
        return []

    files = []
    for filename in os.listdir(uploads_dir):
        if filename.startswith(f"{config.file_prefix}_") and filename.endswith(f".{config.file_extension}"):
            file_path = os.path.join(uploads_dir, filename)
            try:
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "file_path": file_path,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "created_time": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except OSError:
                continue

    # 생성일시 기준 내림차순 정렬
    files.sort(key=lambda x: x["created_time"], reverse=True)
    return files


def get_latest_district_file(config: Optional[DistrictConfig] = None) -> Optional[str]:
    """
    가장 최근에 생성된 행정구역 JSON 파일의 경로를 반환합니다.

    Args:
        config: District 설정 (None이면 기본 config 사용)

    Returns:
        최신 파일의 경로 (없으면 None)
    """
    files = get_district_files(config)
    if not files:
        log_warning("저장된 행정구역 파일이 없습니다.")
        return None

    latest_file = files[0]["file_path"]
    log_info(f"최신 행정구역 파일을 찾았습니다: {latest_file}")
    return latest_file



def preview_district_file(file_path: str, limit: int = 10, config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    '''
    Return summary preview data for a cached district JSON file.
    '''
    if isinstance(limit, DistrictConfig) and config is None:
        config = limit
        limit = 10

    if config is not None and not os.path.isabs(file_path):
        candidate_path = os.path.join(config.uploads_dir, file_path)
        if os.path.exists(candidate_path):
            file_path = candidate_path

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        file_stats = os.stat(file_path)
        file_info = {
            "file_path": file_path,
            "file_size_mb": round(file_stats.st_size / 1024 / 1024, 2),
            "created_time": datetime.fromtimestamp(file_stats.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "modified_time": datetime.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }

        safe_limit = 10
        if isinstance(limit, int):
            safe_limit = max(limit, 0)
        elif isinstance(limit, str) and limit.isdigit():
            safe_limit = max(int(limit), 0)

        metadata: Dict[str, Any] = {}
        preview_data: List[Dict[str, Any]] = []
        total_count = 0
        structure_type = "unknown"

        def append_row(row: Dict[str, Any]) -> None:
            if safe_limit == 0:
                return
            if len(preview_data) < safe_limit:
                preview_data.append(row)

        if isinstance(data, dict):
            raw_metadata = data.get("metadata")
            if isinstance(raw_metadata, dict):
                metadata = raw_metadata

            districts_data = data.get("districts")
            if districts_data is not None:
                if isinstance(districts_data, list):
                    structure_type = "list"
                    total_count = len(districts_data)
                    for row in districts_data:
                        if isinstance(row, dict):
                            append_row(row)
                        else:
                            append_row({"value": row})
                elif isinstance(districts_data, dict):
                    structure_type = "dict"

                    def handle_nested(parent_key: Any, value: Any, code: Optional[Any] = None) -> None:
                        nonlocal total_count
                        if isinstance(value, list):
                            for item in value:
                                handle_nested(parent_key, item, code)
                            return
                        if isinstance(value, dict):
                            if all(not isinstance(v, (dict, list)) for v in value.values()):
                                total_count += 1
                                row = {"parent": parent_key}
                                if code is not None:
                                    row["code"] = code
                                row.update(value)
                                append_row(row)
                            else:
                                for inner_key, inner_value in value.items():
                                    handle_nested(parent_key, inner_value, inner_key)
                        else:
                            total_count += 1
                            row = {"parent": parent_key, "value": value}
                            if code is not None:
                                row["code"] = code
                            append_row(row)

                    for parent_key, entries in districts_data.items():
                        handle_nested(parent_key, entries)
                else:
                    structure_type = type(districts_data).__name__
                    total_count = 1
                    append_row({"value": districts_data})
            else:
                if not metadata:
                    metadata = {
                        k: v for k, v in data.items() if not isinstance(v, (dict, list))
                    }

                structure_type = "nested_dict"

                def handle_legacy(parent_key: Any, value: Any, code: Optional[Any] = None) -> None:
                    nonlocal total_count
                    if isinstance(value, list):
                        for item in value:
                            handle_legacy(parent_key, item)
                        return
                    if isinstance(value, dict):
                        if all(not isinstance(v, (dict, list)) for v in value.values()):
                            total_count += 1
                            row = {"sido": parent_key}
                            if code is not None:
                                row["code"] = code
                            row.update(value)
                            append_row(row)
                        else:
                            for inner_key, inner_value in value.items():
                                handle_legacy(parent_key, inner_value, inner_key)
                    else:
                        total_count += 1
                        row = {"sido": parent_key, "value": value}
                        if code is not None:
                            row["code"] = code
                        append_row(row)

                for top_key, regions in data.items():
                    if isinstance(regions, (dict, list)):
                        handle_legacy(top_key, regions)
                    else:
                        total_count += 1
                        append_row({"sido": top_key, "value": regions})

                if total_count == 0:
                    total_count = sum(
                        len(v) if isinstance(v, (list, dict)) else 1 for v in data.values()
                    )
        elif isinstance(data, list):
            structure_type = "list"
            total_count = len(data)
            for row in data:
                if isinstance(row, dict):
                    append_row(row)
                else:
                    append_row({"value": row})
        else:
            return {
                "success": False,
                "error": "???? ?? ??? ?????.",
                "file_info": file_info,
            }

        data_stats = {
            "structure_type": structure_type,
            "total_count": total_count,
            "preview_count": len(preview_data),
        }
        if isinstance(data, dict):
            data_stats["top_level_keys"] = len(data)

        return {
            "success": True,
            "metadata": metadata,
            "preview_data": preview_data,
            "total_count": total_count,
            "file_info": file_info,
            "data_stats": data_stats,
        }

    except json.JSONDecodeError as e:
        logger.exception("?? ?? ??", exc_info=e)
        return {
            "success": False,
            "error": f"JSON ?? ?? ??: {str(e)}",
            "file_path": file_path,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "??? ???? ????.",
            "file_path": file_path,
        }
    except Exception as e:
        logger.exception("???? ?? ??", exc_info=e)
        return {
            "success": False,
            "error": f"???? ?? ?? ??: {str(e)}",
            "file_path": file_path,
        }

def delete_district_file(file_path: str, config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    지정된 행정구역 파일을 삭제합니다.

    Args:
        file_path: 삭제할 파일 경로
        config: District 설정 (None이면 기본 config 사용)

    Returns:
        삭제 결과 딕셔너리
    """
    # Config 로드
    if config is None:
        from src.app.core.config import load_config
        config = load_config().district

    try:
        # 파일 존재 확인
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": "파일이 존재하지 않습니다.",
                "file_path": file_path
            }

        # 안전성 검사: uploads 디렉토리 내의 district 파일인지 확인
        uploads_dir = os.path.abspath(config.uploads_dir)
        file_abs_path = os.path.abspath(file_path)

        if not file_abs_path.startswith(uploads_dir):
            log_error(f"허용되지 않은 경로에서 파일 삭제 시도: {file_path}")
            return {
                "success": False,
                "error": "허용되지 않은 경로입니다.",
                "file_path": file_path
            }

        filename = os.path.basename(file_path)
        if not (filename.startswith(f"{config.file_prefix}_") and filename.endswith(f".{config.file_extension}")):
            log_error(f"허용되지 않은 파일 형식 삭제 시도: {filename}")
            return {
                "success": False,
                "error": "허용되지 않은 파일 형식입니다.",
                "file_path": file_path
            }

        # 파일 정보 백업 (삭제 전)
        file_stats = os.stat(file_path)
        file_info = {
            "filename": filename,
            "size_mb": round(file_stats.st_size / 1024 / 1024, 2),
            "created_time": datetime.fromtimestamp(file_stats.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        }

        # 파일 삭제
        os.remove(file_path)
        log_info(f"행정구역 파일 삭제 완료: {filename}")

        return {
            "success": True,
            "message": "파일이 성공적으로 삭제되었습니다.",
            "deleted_file": file_info
        }

    except PermissionError:
        log_error(f"파일 삭제 권한 없음: {file_path}")
        return {
            "success": False,
            "error": "파일 삭제 권한이 없습니다.",
            "file_path": file_path
        }
    except Exception as e:
        log_error(f"파일 삭제 중 오류 발생: {e}")
        return {
            "success": False,
            "error": f"파일 삭제 중 오류 발생: {str(e)}",
            "file_path": file_path
        }


def delete_all_district_files(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    모든 행정구역 파일을 삭제합니다.

    Args:
        config: District 설정 (None이면 기본 config 사용)

    Returns:
        삭제 결과 딕셔너리
    """
    # Config 로드
    if config is None:
        from src.app.core.config import load_config
        config = load_config().district

    try:
        files = get_district_files(config)
        if not files:
            log_info("삭제할 행정구역 파일이 없습니다.")
            return {
                "success": True,
                "message": "삭제할 파일이 없습니다.",
                "deleted_count": 0,
                "deleted_files": []
            }

        deleted_files = []
        failed_files = []

        for file_info in files:
            file_path = file_info["file_path"]
            result = delete_district_file(file_path, config)

            if result["success"]:
                deleted_files.append(file_info["filename"])
            else:
                failed_files.append({
                    "filename": file_info["filename"],
                    "error": result["error"]
                })

        if failed_files:
            log_warning(f"일부 파일 삭제 실패: {len(failed_files)}개")
            return {
                "success": False,
                "message": f"{len(deleted_files)}개 파일 삭제 완료, {len(failed_files)}개 파일 삭제 실패",
                "deleted_count": len(deleted_files),
                "deleted_files": deleted_files,
                "failed_files": failed_files
            }
        else:
            log_info(f"모든 행정구역 파일 삭제 완료: {len(deleted_files)}개")
            return {
                "success": True,
                "message": f"모든 파일이 성공적으로 삭제되었습니다. ({len(deleted_files)}개)",
                "deleted_count": len(deleted_files),
                "deleted_files": deleted_files
            }

    except Exception as e:
        log_error(f"전체 파일 삭제 중 오류 발생: {e}")
        return {
            "success": False,
            "error": f"전체 파일 삭제 중 오류 발생: {str(e)}"
        }