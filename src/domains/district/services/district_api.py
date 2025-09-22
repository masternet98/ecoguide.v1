"""통합 district 서비스 API 모듈.

행정구역 데이터 작업을 고수준 API로 제공합니다.
"""

from typing import Any, Dict, List, Optional

from src.app.core.config import DistrictConfig, load_config
from .district_loader import (
    check_data_go_kr_update,
    download_district_data_from_web,
    process_district_csv,
)
from .district_cache import (
    delete_all_district_files,
    delete_district_file,
    get_district_files,
    get_latest_district_file,
    preview_district_file,
)
from .district_service import (
    get_last_update_info,
    save_update_info,
    auto_update_district_data,
    clear_update_info,
    force_update_district_data,
)


class DistrictService:
    """행정구역 데이터 처리를 위한 고수준 API."""

    def __init__(self, config: Optional[DistrictConfig] = None) -> None:
        self.config = config or load_config().district

    def process_csv(
        self,
        csv_content: bytes,
        output_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """CSV 데이터를 처리하여 저장합니다."""
        return process_district_csv(csv_content, output_filename, self.config)

    def download_latest_data(self) -> Dict[str, Any]:
        """data.go.kr에서 최신 데이터를 다운로드합니다."""
        return download_district_data_from_web(self.config)

    def check_remote_update(self) -> Dict[str, Any]:
        """원격 데이터 수정일을 확인합니다."""
        return check_data_go_kr_update(self.config)

    def auto_update(self) -> Dict[str, Any]:
        """자동 업데이트 파이프라인을 실행합니다."""
        return auto_update_district_data(self.config)

    def force_update(self) -> Dict[str, Any]:
        """날짜 비교 없이 강제 업데이트를 수행합니다."""
        return force_update_district_data(self.config)

    def get_last_update_info(self) -> Dict[str, Any]:
        """로컬에 저장된 마지막 업데이트 정보를 반환합니다."""
        return get_last_update_info(self.config)

    def save_update_info(self, modification_date: str) -> None:
        """마지막 업데이트 정보를 갱신합니다."""
        save_update_info(modification_date, self.config)

    def clear_update_info(self) -> Dict[str, Any]:
        """업데이트 정보를 초기화합니다."""
        return clear_update_info(self.config)

    def list_cached_files(self) -> List[Dict[str, Any]]:
        """저장된 행정구역 파일 목록을 반환합니다."""
        return get_district_files(self.config)

    def latest_cached_file(self) -> Optional[str]:
        """가장 최근 캐시 파일 경로를 반환합니다."""
        return get_latest_district_file(self.config)

    def preview_cached_file(self, filename: str) -> Dict[str, Any]:
        """지정한 캐시 파일을 미리봅니다."""
        return preview_district_file(filename, self.config)

    def delete_cached_file(self, filename: str) -> Dict[str, Any]:
        """캐시 파일을 삭제하고 필요 시 업데이트 정보를 초기화합니다."""
        result = delete_district_file(filename, self.config)
        if result.get("success") and not self.list_cached_files():
            self.clear_update_info()
        return result

    def delete_all_cached_files(self) -> Dict[str, Any]:
        """모든 캐시 파일을 삭제하고 업데이트 정보를 초기화합니다."""
        result = delete_all_district_files(self.config)
        if result.get("success"):
            self.clear_update_info()
        return result


__all__ = ["DistrictService"]
