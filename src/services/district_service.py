"""
행정구역 데이터 처리를 위한 서비스 모듈입니다.
CSV 파일을 업로드하여 시군구명 기준으로 중복 제거 후 JSON으로 변환합니다.
data.go.kr에서 자동 업데이트 기능도 제공합니다.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.logger import (
    log_function, log_step, log_info, log_warning, log_error, LogCategory
)
from src.core.config import DistrictConfig
from .district_validator import (
    normalize_admin_field, validate_district_row, get_validation_stats,
    validate_admin_hierarchy, clean_admin_code, validate_csv_data
)
from .district_cache import (
    get_district_files, get_latest_district_file, preview_district_file,
    delete_district_file, delete_all_district_files
)
from .district_loader import (
    check_data_go_kr_update, download_district_data_from_web, process_district_csv
)
# 기존 코드와의 호환성을 위한 별칭
_normalize_admin_field = normalize_admin_field




# get_district_files 함수는 district_cache.py로 이동됨


# get_latest_district_file 함수는 district_cache.py로 이동됨


# preview_district_file 함수는 district_cache.py로 이동됨


















def get_last_update_info(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    로컬에 저장된 마지막 업데이트 정보를 가져옵니다.
    
    Args:
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        마지막 업데이트 정보
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    uploads_dir = config.uploads_dir
    info_file = os.path.join(uploads_dir, "last_update_info.json")
    
    if os.path.exists(info_file):
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"last_modification_date": None, "last_update_time": None}
    
    return {"last_modification_date": None, "last_update_time": None}


def save_update_info(modification_date: str, config: Optional[DistrictConfig] = None):
    """
    업데이트 정보를 로컬에 저장합니다.
    
    Args:
        modification_date: 데이터 수정일
        config: District 설정 (None이면 기본 config 사용)
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    uploads_dir = config.uploads_dir
    os.makedirs(uploads_dir, exist_ok=True)
    
    info_file = os.path.join(uploads_dir, "last_update_info.json")
    
    update_info = {
        "last_modification_date": modification_date,
        "last_update_time": datetime.now().isoformat()
    }
    
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(update_info, f, ensure_ascii=False, indent=2)


@log_function(LogCategory.WEB_SCRAPING, "자동_업데이트", include_args=False, include_result=False)
def auto_update_district_data(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    data.go.kr에서 데이터 업데이트를 자동으로 확인하고 필요시 다운로드/처리합니다.
    
    Args:
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        자동 업데이트 결과
    """
    module_name = "district_service"
    function_name = "auto_update_district_data"
    
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    log_info(
        LogCategory.WEB_SCRAPING, module_name, function_name, "자동_업데이트_시작",
        "data.go.kr 자동 업데이트 프로세스 시작"
    )
    
    # 1. 웹사이트에서 수정일 확인
    with log_step(LogCategory.WEB_SCRAPING, module_name, function_name, "웹사이트_확인"):
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_시작",
            "웹사이트에서 데이터 수정일 확인 시작"
        )
        
        check_result = check_data_go_kr_update(config=config)
        if not check_result["success"]:
            log_error(
                LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_실패",
                f"웹사이트 수정일 확인 실패: {check_result['message']}"
            )
            return {
                "success": False,
                "action": "check_failed",
                "message": check_result["message"]
            }
        
        web_modification_date = check_result["modification_date"]
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_완료",
            f"웹사이트 수정일 확인 완료: {web_modification_date}"
        )
    
    # 2. 로컬 업데이트 정보 확인
    with log_step(LogCategory.FILE_OPERATION, module_name, function_name, "로컬_정보_확인"):
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "로컬_정보_조회_시작",
            "로컬 업데이트 정보 조회 시작"
        )
        
        local_info = get_last_update_info(config)
        local_modification_date = local_info.get("last_modification_date")
        
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "로컬_정보_조회_완료",
            f"로컬 수정일: {local_modification_date or '없음'}"
        )
    
    # 3. 날짜 비교
    with log_step(LogCategory.VALIDATION, module_name, function_name, "날짜_비교"):
        log_info(
            LogCategory.VALIDATION, module_name, function_name, "날짜_비교_시작",
            f"날짜 비교 - 웹사이트: {web_modification_date}, 로컬: {local_modification_date}"
        )
        
        if local_modification_date == web_modification_date:
            log_info(
                LogCategory.VALIDATION, module_name, function_name, "업데이트_불필요",
                "데이터가 최신 상태 - 업데이트 불필요"
            )
            return {
                "success": True,
                "action": "no_update_needed",
                "message": f"데이터가 최신 상태입니다. (수정일: {web_modification_date})",
                "web_date": web_modification_date,
                "local_date": local_modification_date
            }
        
        log_info(
            LogCategory.VALIDATION, module_name, function_name, "업데이트_필요",
            "데이터 업데이트 필요 - 다운로드 진행"
        )
    
    # 4. 업데이트 필요 - 데이터 다운로드
    with log_step(LogCategory.WEB_SCRAPING, module_name, function_name, "데이터_다운로드"):
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "다운로드_시작",
            "웹사이트에서 데이터 다운로드 시작"
        )
        
        download_result = download_district_data_from_web(config)
        if not download_result["success"]:
            # HTML 응답인지 확인하여 더 구체적인 에러 메시지 제공
            error_message = download_result["message"]
            
            # 디버그 정보가 있는 경우 추가 분석
            if "debug_info" in download_result:
                debug_info = download_result["debug_info"]
                if "page_size" in debug_info and debug_info.get("found_params") == False:
                    error_message += "\n\n🔍 가능한 해결방법:\n"
                    error_message += "1. 웹사이트 구조가 변경되어 다운로드 파라미터를 찾을 수 없습니다\n"
                    error_message += "2. 수동으로 CSV 파일을 다운로드하여 업로드해 주세요\n"
                    error_message += f"3. 페이지 주소: {config.page_url}"
            
            # HTML 응답 관련 정보가 있는 경우
            validation_info = download_result.get("validation_info", {})
            if validation_info.get("is_html"):
                error_message += "\n\n⚠️ 웹사이트가 HTML 페이지를 반환했습니다. 다운로드 링크가 변경되었을 가능성이 높습니다."
            
            log_error(
                LogCategory.WEB_SCRAPING, module_name, function_name, "다운로드_실패",
                f"데이터 다운로드 실패: {error_message}"
            )
            return {
                "success": False,
                "action": "download_failed",
                "message": error_message,
                "web_date": web_modification_date,
                "local_date": local_modification_date,
                "debug_info": download_result.get("debug_info"),
                "validation_info": validation_info
            }
        
        data_size = len(download_result.get("csv_data", b""))
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "다운로드_완료",
            f"데이터 다운로드 완료 - 크기: {data_size:,} bytes"
        )
    
    # 5. 다운로드된 데이터 검증 및 처리
    with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "자동_데이터_처리"):
        # config를 사용하여 파일명 생성
        if web_modification_date:
            date_str = web_modification_date.replace("-", "")
            filename = f"{config.file_prefix}_auto_{date_str}.{config.file_extension}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{config.file_prefix}_auto_{timestamp}.{config.file_extension}"
        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_처리_시작",
            f"다운로드된 데이터 처리 시작 - 출력 파일: {filename}"
        )
        
        # 다운로드 검증 정보 로깅
        if "source_validation" in download_result:
            validation_info = download_result["source_validation"]
            log_info(
                LogCategory.VALIDATION, module_name, function_name, "소스_검증_결과",
                f"파일 소스 검증 - 유효: {validation_info['is_valid']}, 신뢰도: {validation_info['confidence_score']}, 이슈: {len(validation_info['issues'])}"
            )
            
            if not validation_info['is_valid']:
                log_warning(
                    LogCategory.VALIDATION, module_name, function_name, "소스_검증_경고",
                    f"파일 소스 검증 실패 - 이슈: {validation_info['issues']}"
                )
        
        # 웹사이트 변경 정보 로깅
        if "website_change_info" in download_result:
            change_info = download_result["website_change_info"]
            if change_info.get('changes_detected'):
                log_warning(
                    LogCategory.WEB_SCRAPING, module_name, function_name, "웹사이트_변경_감지",
                    f"웹사이트 변경사항 감지 - 심각도: {change_info['severity']}, 변경유형: {change_info['change_types']}"
                )
        
        process_result = process_district_csv(download_result["csv_data"], filename, config)
        
        if not process_result["success"]:
            log_error(
                LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_처리_실패",
                f"데이터 처리 실패: {process_result['message']}"
            )
            return {
                "success": False,
                "action": "process_failed",
                "message": process_result["message"],
                "web_date": web_modification_date,
                "local_date": local_modification_date
            }
        
        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_처리_완료",
            f"데이터 처리 완료 - 저장 경로: {process_result['file_path']}"
        )
    
    # 6. 업데이트 정보 저장
    with log_step(LogCategory.FILE_OPERATION, module_name, function_name, "업데이트_정보_저장"):
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "정보_저장_시작",
            f"업데이트 정보 저장 - 수정일: {web_modification_date}"
        )
        
        save_update_info(web_modification_date, config)
        
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "정보_저장_완료",
            "업데이트 정보 저장 완료"
        )
    
    log_info(
        LogCategory.WEB_SCRAPING, module_name, function_name, "자동_업데이트_완료",
        f"자동 업데이트 프로세스 성공적으로 완료 - 웹: {web_modification_date}, 로컬: {local_modification_date}"
    )
    
    return {
        "success": True,
        "action": "updated",
        "message": f"데이터가 성공적으로 업데이트되었습니다. (수정일: {web_modification_date})",
        "web_date": web_modification_date,
        "local_date": local_modification_date,
        "file_path": process_result["file_path"],
        "statistics": process_result["statistics"]
    }


# delete_district_file 함수는 district_cache.py로 이동됨


def clear_update_info(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    업데이트 정보를 초기화(삭제)합니다.
    모든 district 파일이 삭제될 때 호출됩니다.
    
    Args:
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        초기화 결과 딕셔너리
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    uploads_dir = config.uploads_dir
    info_file = os.path.join(uploads_dir, "last_update_info.json")
    
    try:
        if os.path.exists(info_file):
            os.remove(info_file)
            log_info(
                LogCategory.FILE_OPERATION, "district_service", "clear_update_info", "업데이트_정보_초기화",
                f"업데이트 정보 파일 삭제 완료 - 경로: {info_file}"
            )
            return {
                "success": True,
                "message": "업데이트 정보가 초기화되었습니다."
            }
        else:
            return {
                "success": True,
                "message": "업데이트 정보 파일이 이미 존재하지 않습니다."
            }
    except Exception as e:
        log_error(
            LogCategory.FILE_OPERATION, "district_service", "clear_update_info", "업데이트_정보_초기화_오류",
            f"업데이트 정보 초기화 실패: {str(e)}", error=e
        )
        return {
            "success": False,
            "message": f"업데이트 정보 초기화 중 오류가 발생했습니다: {str(e)}"
        }


# delete_all_district_files 함수는 district_cache.py로 이동됨


@log_function(LogCategory.WEB_SCRAPING, "강제_업데이트", include_args=False, include_result=False)
def force_update_district_data(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    data.go.kr에서 날짜 체크 없이 강제로 데이터를 다운로드하고 처리합니다.
    dong_hierarchy를 포함한 완전한 구조의 데이터를 생성합니다.

    Args:
        config: District 설정 (None이면 기본 config 사용)

    Returns:
        강제 업데이트 결과
    """
    module_name = "district_service"
    function_name = "force_update_district_data"

    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district

    log_info(
        LogCategory.WEB_SCRAPING, module_name, function_name, "강제_업데이트_시작",
        "data.go.kr 강제 업데이트 프로세스 시작 (날짜 체크 우회)"
    )

    # 1. 웹사이트에서 수정일 확인 (정보 수집 목적)
    with log_step(LogCategory.WEB_SCRAPING, module_name, function_name, "웹사이트_확인"):
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_시작",
            "웹사이트에서 데이터 수정일 확인 시작"
        )

        check_result = check_data_go_kr_update(config=config)
        web_modification_date = None
        if check_result["success"]:
            web_modification_date = check_result["modification_date"]
            log_info(
                LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_완료",
                f"웹사이트 수정일 확인 완료: {web_modification_date}"
            )
        else:
            log_warning(
                LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_실패",
                f"웹사이트 수정일 확인 실패 (계속 진행): {check_result['message']}"
            )

    # 2. 로컬 업데이트 정보 확인 (정보 수집 목적)
    with log_step(LogCategory.FILE_OPERATION, module_name, function_name, "로컬_정보_확인"):
        local_info = get_last_update_info(config)
        local_modification_date = local_info.get("last_modification_date")

        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "강제_업데이트_모드",
            f"강제 업데이트 모드 - 날짜 비교 우회. 웹: {web_modification_date}, 로컬: {local_modification_date}"
        )

    # 3. 강제 다운로드 진행
    with log_step(LogCategory.WEB_SCRAPING, module_name, function_name, "강제_다운로드"):
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "강제_다운로드_시작",
            "강제 다운로드 시작 (날짜 체크 없이 무조건 다운로드)"
        )

        download_result = download_district_data_from_web(config)
        if not download_result["success"]:
            error_message = download_result["message"]

            # 디버그 정보 추가
            if "debug_info" in download_result:
                debug_info = download_result["debug_info"]
                if "page_size" in debug_info and debug_info.get("found_params") == False:
                    error_message += "\n\n🔍 가능한 해결방법:\n"
                    error_message += "1. 웹사이트 구조가 변경되어 다운로드 파라미터를 찾을 수 없습니다\n"
                    error_message += "2. 수동으로 CSV 파일을 다운로드하여 업로드해 주세요\n"
                    error_message += f"3. 페이지 주소: {config.page_url}"

            log_error(
                LogCategory.WEB_SCRAPING, module_name, function_name, "강제_다운로드_실패",
                f"강제 다운로드 실패: {error_message}"
            )
            return {
                "success": False,
                "action": "download_failed",
                "message": f"강제 다운로드 실패: {error_message}",
                "web_date": web_modification_date,
                "local_date": local_modification_date
            }

        data_size = len(download_result.get("csv_data", b""))
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "강제_다운로드_완료",
            f"강제 다운로드 완료 - 크기: {data_size:,} bytes"
        )

    # 4. 다운로드된 데이터 처리 (dong_hierarchy 포함)
    with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "강제_데이터_처리"):
        # config를 사용하여 파일명 생성 (강제 업데이트 표시)
        if web_modification_date:
            date_str = web_modification_date.replace("-", "")
            filename = f"{config.file_prefix}_force_{date_str}.{config.file_extension}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{config.file_prefix}_force_{timestamp}.{config.file_extension}"

        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "강제_처리_시작",
            f"강제 다운로드 데이터 처리 시작 (dong_hierarchy 포함) - 출력 파일: {filename}"
        )

        # 새로운 process_district_csv 함수 사용 (dong_hierarchy 포함)
        process_result = process_district_csv(download_result["csv_data"], filename, config)

        if not process_result["success"]:
            log_error(
                LogCategory.CSV_PROCESSING, module_name, function_name, "강제_처리_실패",
                f"강제 데이터 처리 실패: {process_result['message']}"
            )
            return {
                "success": False,
                "action": "process_failed",
                "message": f"강제 데이터 처리 실패: {process_result['message']}",
                "web_date": web_modification_date,
                "local_date": local_modification_date
            }

        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "강제_처리_완료",
            f"강제 데이터 처리 완료 (dong_hierarchy 포함) - 저장 경로: {process_result['file_path']}"
        )

    # 5. 업데이트 정보 저장
    with log_step(LogCategory.FILE_OPERATION, module_name, function_name, "업데이트_정보_저장"):
        if web_modification_date:
            save_update_info(web_modification_date, config)
            log_info(
                LogCategory.FILE_OPERATION, module_name, function_name, "정보_저장_완료",
                f"업데이트 정보 저장 완료 - 수정일: {web_modification_date}"
            )
        else:
            log_warning(
                LogCategory.FILE_OPERATION, module_name, function_name, "정보_저장_스킵",
                "웹사이트 수정일을 확인할 수 없어 업데이트 정보 저장을 건너뜁니다"
            )

    # 6. 성공 결과 반환
    log_info(
        LogCategory.WEB_SCRAPING, module_name, function_name, "강제_업데이트_완료",
        "data.go.kr 강제 업데이트 프로세스 완료"
    )

    return {
        "success": True,
        "action": "force_updated",
        "message": f"강제 업데이트가 성공적으로 완료되었습니다. dong_hierarchy를 포함한 완전한 데이터 구조가 생성되었습니다.",
        "file_path": process_result["file_path"],
        "statistics": process_result["statistics"],
        "web_date": web_modification_date,
        "local_date": local_modification_date
    }
