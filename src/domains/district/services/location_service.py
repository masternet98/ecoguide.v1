"""
위치 기반 서비스 모듈입니다.
GPS 좌표를 행정구역으로 변환하고, 행정구역 데이터를 관리합니다.
"""
import json
import os
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from src.app.core.config import LocationConfig, get_vworld_api_key
from src.app.core.logger import logger, log_function, log_step, log_info, log_warning, log_error, LogCategory


class LocationService:
    """위치 기반 서비스를 관리하는 클래스입니다."""

    def __init__(self, config: LocationConfig):
        """
        LocationService 초기화

        Args:
            config: 위치 서비스 설정
        """
        self.config = config
        # VWorld API 키를 런타임에 로드 (Streamlit Cloud secrets 지원)
        self.config.vworld_api_key = get_vworld_api_key()
        self.districts_data: Optional[Dict[str, Any]] = None
        self.location_cache: Dict[str, Dict[str, Any]] = {}
        self._load_districts_data()

    def _load_districts_data(self) -> None:
        """행정구역 데이터를 로드합니다."""
        try:
            # district_service의 get_latest_district_file 함수 사용
            from src.domains.district.services.district_service import get_latest_district_file

            latest_file_path = get_latest_district_file()
            if not latest_file_path:
                log_warning(
                    LogCategory.FILE_OPERATION, "location_service", "_load_districts_data",
                    "사용 가능한 districts 파일이 없음",
                    "uploads/districts 폴더를 확인하세요"
                )
                return

            with open(latest_file_path, 'r', encoding='utf-8') as f:
                self.districts_data = json.load(f)

            # 파일명만 추출 (로그용)
            filename = os.path.basename(latest_file_path)

            # dong_hierarchy 존재 여부 확인
            has_dong_hierarchy = 'dong_hierarchy' in self.districts_data and bool(self.districts_data['dong_hierarchy'])
            dong_count = 0
            if has_dong_hierarchy:
                for sido, sigungu_dict in self.districts_data['dong_hierarchy'].items():
                    for sigungu, dong_list in sigungu_dict.items():
                        dong_count += len(dong_list)

            log_info(
                LogCategory.FILE_OPERATION, "location_service", "_load_districts_data",
                "districts 데이터 로드 완료",
                f"파일: {filename}, 지역 수: {len(self.districts_data.get('districts', []))}, dong_hierarchy: {has_dong_hierarchy}, 동 수: {dong_count}"
            )

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "location_service", "_load_districts_data",
                "districts 데이터 로드 실패", f"오류: {str(e)}", error=e
            )

    @log_function(LogCategory.WEB_API, "좌표를_주소로_변환", include_args=True, include_result=True)
    def get_location_from_coords(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        GPS 좌표를 행정구역 정보로 변환합니다.

        Args:
            lat: 위도
            lng: 경도

        Returns:
            변환된 위치 정보 딕셔너리
        """
        # 좌표 정밀도 조정
        lat = round(lat, self.config.coordinate_precision)
        lng = round(lng, self.config.coordinate_precision)

        # 캐시 키 생성
        cache_key = f"{lat},{lng}"

        # 캐시 확인
        if cache_key in self.location_cache:
            cached_data = self.location_cache[cache_key]
            cache_time = datetime.fromisoformat(cached_data.get('cached_at', '2000-01-01'))
            if datetime.now() - cache_time < timedelta(seconds=self.config.location_cache_duration):
                log_info(
                    LogCategory.CACHE, "location_service", "get_location_from_coords",
                    "캐시에서 위치 정보 반환", f"좌표: {lat}, {lng}"
                )
                return cached_data['data']

        # VWorld API 키 가용성 확인
        vworld_available = bool(self.config.vworld_api_key)

        # 디버깅: API 키 상태 로깅
        log_info(
            LogCategory.WEB_API, "location_service", "get_location_from_coords",
            "VWorld API 키 가용성 확인",
            f"VWorld: {vworld_available} (키: {self.config.vworld_api_key[:10] + '...' if self.config.vworld_api_key else 'None'})"
        )

        if not vworld_available:
            error_message = 'VWorld API 키 미설정: VWORLD_API_KEY가 필요합니다.'
            log_error(
                LogCategory.WEB_API, "location_service", "get_location_from_coords",
                "VWorld API 키 없음", error_message
            )
            return {
                'success': False,
                'message': error_message,
                'data': None
            }

        try:
            # VWorld API 호출
            log_info(
                LogCategory.WEB_API, "location_service", "get_location_from_coords",
                "VWorld API 호출 시작", f"좌표: {lat}, {lng}"
            )
            result = self._get_location_from_vworld(lat, lng)

            if result['success']:
                log_info(
                    LogCategory.WEB_API, "location_service", "get_location_from_coords",
                    "VWorld API 성공", f"결과: {result.get('data', {}).get('full_address', 'N/A')}"
                )
                # 캐시에 저장
                self.location_cache[cache_key] = {
                    'data': result,
                    'cached_at': datetime.now().isoformat()
                }
                return result
            else:
                log_error(
                    LogCategory.WEB_API, "location_service", "get_location_from_coords",
                    "VWorld API 실패", f"메시지: {result.get('message', 'N/A')}"
                )
                return result

        except Exception as e:
            log_error(
                LogCategory.WEB_API, "location_service", "get_location_from_coords",
                "VWorld API 호출 중 예상치 못한 오류", f"좌표: {lat}, {lng}, 오류: {str(e)}", error=e
            )
            return {
                'success': False,
                'message': f'위치 변환 중 오류가 발생했습니다: {str(e)}',
                'data': None
            }

    def _get_location_from_vworld(self, lat: float, lng: float) -> Dict[str, Any]:
        """VWorld API를 사용하여 좌표를 주소로 변환합니다."""
        try:
            # VWorld API 파라미터 설정
            params = {
                'service': 'address',
                'request': 'getAddress',
                'version': '2.0',
                'crs': 'epsg:4326',
                'point': f'{lng},{lat}',  # VWorld는 x,y (lng,lat) 순서
                'format': 'json',
                'type': 'both',  # PARCEL, ROAD, BOTH 중 선택
                'zipcode': 'true',
                'key': self.config.vworld_api_key
            }

            url = self.config.vworld_geocode_url
            response = requests.get(
                url,
                params=params,
                timeout=self.config.default_timeout
            )

            # HTTP 상태 코드 확인
            if response.status_code == 502:
                log_warning(
                    LogCategory.WEB_API, "location_service", "_get_location_from_vworld",
                    "VWorld API 서버 오류 (502)",
                    "Streamlit Cloud IP 제한 또는 서버 점검 상태 가능성 - VWorld 관리 페이지에서 아웃바운드 IP 화이트리스트 확인 필요"
                )
                return {
                    'success': False,
                    'message': 'VWorld API 서버 오류(502): 서버가 일시적으로 사용 불가능합니다.',
                    'data': None,
                    'error_code': 502
                }

            response.raise_for_status()

            data = response.json()

            # VWorld API 응답 구조 확인
            if data.get('response', {}).get('status') != 'OK':
                error_msg = data.get('response', {}).get('error', {}).get('message', '알 수 없는 오류')
                return {
                    'success': False,
                    'message': f'VWorld API 오류: {error_msg}',
                    'data': None
                }

            result = data.get('response', {}).get('result', [])
            if not result:
                return {
                    'success': False,
                    'message': '해당 좌표에서 주소를 찾을 수 없습니다.',
                    'data': None
                }

            # 첫 번째 결과 사용
            address_info = result[0]
            structure = address_info.get('structure', {})

            # 시도와 시군구 추출
            sido = structure.get('level1', '')  # 시/도
            sigungu = structure.get('level2', '')  # 시/군/구

            # 동 정보 추출 (법정동/행정동)
            try:
                legal_dong = structure.get('level4L', '') or ''  # 법정동
                admin_dong = structure.get('level4A', '') or ''  # 행정동

                # 동 정보 결정 로직 (법정동 우선, 없으면 행정동)
                dong = legal_dong if legal_dong else admin_dong
                dong_type = "법정동" if legal_dong else ("행정동" if admin_dong else None)
            except Exception as dong_error:
                # 동 정보 추출 실패해도 기존 처리 계속
                legal_dong = admin_dong = dong = ''
                dong_type = None
                log_warning(
                    LogCategory.WEB_API, "location_service", "_get_location_from_vworld",
                    "동 정보 추출 실패, 기본 처리 계속", f"오류: {str(dong_error)}"
                )

            # 전체 주소 구성 (text 필드 사용)
            full_address = address_info.get('text', '')

            # 동 정보 포함 로깅
            dong_info = f", 동: {dong}({dong_type})" if dong else ""
            log_info(
                LogCategory.WEB_API, "location_service", "_get_location_from_vworld",
                "VWorld API 지오코딩 성공", f"시도: {sido}, 시군구: {sigungu}{dong_info}"
            )

            # Phase 2: 동 정보 자동 캐싱
            if sido and sigungu and (legal_dong or admin_dong):
                try:
                    self.cache_dong_info(sido, sigungu, legal_dong, admin_dong)
                except Exception as cache_error:
                    # 캐싱 실패해도 메인 로직에는 영향 주지 않음
                    log_warning(
                        LogCategory.CACHE, "location_service", "_get_location_from_vworld",
                        "동 정보 캐싱 실패, 메인 로직 계속 진행", f"오류: {str(cache_error)}"
                    )

            return {
                'success': True,
                'message': '위치 정보를 성공적으로 가져왔습니다.',
                'data': {
                    'sido': sido,
                    'sigungu': sigungu,
                    'legal_dong': legal_dong,     # 신규: 법정동
                    'admin_dong': admin_dong,     # 신규: 행정동
                    'dong': dong,                 # 신규: 대표 동 (법정동 우선)
                    'dong_type': dong_type,       # 신규: 동 타입
                    'full_address': full_address,
                    'coords': {'lat': lat, 'lng': lng},
                    'method': 'vworld_api'
                }
            }

        except requests.exceptions.RequestException as e:
            import traceback
            status = getattr(getattr(e, "response", None), "status_code", "N/A")
            body = None
            error_detail = None

            try:
                response = getattr(e, "response", None)
                if response:
                    body = response.text[:500] if response.text else None
                    # JSON 응답인 경우 파싱 시도
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('response', {}).get('error', {}).get('message', str(error_json))
                    except:
                        error_detail = body
            except Exception:
                body = None

            # 상세한 에러 정보 로깅 (traceback 포함)
            traceback_str = traceback.format_exc()
            log_error(
                LogCategory.WEB_API, "location_service", "_get_location_from_vworld",
                "VWorld API 요청 실패",
                f"좌표: {lat}, {lng}, status: {status}, url: {url}, 오류: {str(e)}, 응답: {body}, "
                f"상세오류: {error_detail}, traceback: {traceback_str}",
                error=e
            )

            # 사용자용 에러 메시지
            user_message = f'VWorld API 오류(status={status})'
            if error_detail:
                user_message += f': {error_detail}'
            else:
                user_message += f': {str(e)}'

            return {
                'success': False,
                'message': user_message,
                'data': {
                    'api_error': True,
                    'status_code': status,
                    'error_detail': error_detail,
                    'response_body': body
                }
            }
        except Exception as e:
            import traceback
            # 상세한 예외 정보 로깅 (traceback 포함)
            traceback_str = traceback.format_exc()
            log_error(
                LogCategory.WEB_API, "location_service", "_get_location_from_vworld",
                "VWorld API 처리 실패",
                f"좌표: {lat}, {lng}, 오류: {str(e)}, traceback: {traceback_str}",
                error=e
            )
            return {
                'success': False,
                'message': f'VWorld API 처리 오류: {str(e)}',
                'data': {
                    'exception_error': True,
                    'error_type': type(e).__name__,
                    'traceback': traceback_str
                }
            }

    def get_sido_list(self) -> List[str]:
        """시/도 목록을 반환합니다."""
        if not self.districts_data:
            return []

        districts = self.districts_data.get('districts', [])
        sido_set = set()

        for district in districts:
            sido = district.get('시도명')
            if sido:
                sido_set.add(sido)

        return sorted(list(sido_set))

    def get_sigungu_list_by_sido(self, sido_name: str) -> List[str]:
        """특정 시/도의 시/군/구 목록을 반환합니다."""
        if not self.districts_data:
            return []

        districts = self.districts_data.get('districts', [])
        sigungu_set = set()

        for district in districts:
            if district.get('시도명') == sido_name:
                sigungu = district.get('시군구명')
                if sigungu:
                    sigungu_set.add(sigungu)

        return sorted(list(sigungu_set))

    def validate_location(self, sido: str, sigungu: str) -> Dict[str, Any]:
        """선택된 시/도 및 시/군/구가 유효한지 검증합니다."""
        if not self.districts_data:
            return {
                'valid': False,
                'message': '행정구역 데이터가 로드되지 않았습니다.'
            }

        districts = self.districts_data.get('districts', [])

        for district in districts:
            if (district.get('시도명') == sido and
                district.get('시군구명') == sigungu):
                return {
                    'valid': True,
                    'message': '유효한 행정구역입니다.',
                    'district_data': district
                }

        return {
            'valid': False,
            'message': f'"{sido} {sigungu}"는 유효하지 않은 행정구역입니다.'
        }

    def get_location_info(self, sido: str, sigungu: str) -> Dict[str, Any]:
        """시/도와 시/군/구 정보로 위치 정보를 구성합니다."""
        validation = self.validate_location(sido, sigungu)

        if not validation['valid']:
            return {
                'success': False,
                'message': validation['message'],
                'data': None
            }

        return {
            'success': True,
            'message': '수동으로 선택된 위치입니다.',
            'data': {
                'sido': sido,
                'sigungu': sigungu,
                'full_address': f"{sido} {sigungu}",
                'coords': None,  # 수동 선택 시에는 좌표 없음
                'method': 'manual'
            }
        }

    def get_api_status(self) -> Dict[str, Any]:
        """위치 서비스 API 상태를 확인합니다."""
        # 현재 사용 중인 파일 정보 가져오기
        current_file_info = self.get_current_district_file_info()

        status = {
            'vworld_api': {
                'available': bool(self.config.vworld_api_key),
                'api_key_set': bool(self.config.vworld_api_key)
            },
            'districts_data': {
                'loaded': bool(self.districts_data),
                'count': len(self.districts_data.get('districts', [])) if self.districts_data else 0,
                'has_dong_hierarchy': bool(self.districts_data and 'dong_hierarchy' in self.districts_data and self.districts_data['dong_hierarchy']),
                'current_file': current_file_info
            }
        }

        return status

    def get_current_district_file_info(self) -> Optional[Dict[str, Any]]:
        """현재 사용 중인 district 파일 정보를 반환합니다."""
        try:
            from src.domains.district.services.district_service import get_latest_district_file

            latest_file_path = get_latest_district_file()
            if not latest_file_path:
                return None

            stat = os.stat(latest_file_path)
            filename = os.path.basename(latest_file_path)

            # dong_hierarchy 정보 확인
            dong_count = 0
            has_dong_hierarchy = False
            if self.districts_data and 'dong_hierarchy' in self.districts_data:
                has_dong_hierarchy = bool(self.districts_data['dong_hierarchy'])
                if has_dong_hierarchy:
                    for sido, sigungu_dict in self.districts_data['dong_hierarchy'].items():
                        for sigungu, dong_list in sigungu_dict.items():
                            dong_count += len(dong_list)

            return {
                'filename': filename,
                'file_path': latest_file_path,
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                'is_force_update': '_force_' in filename,
                'has_dong_hierarchy': has_dong_hierarchy,
                'dong_count': dong_count
            }

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "location_service", "get_current_district_file_info",
                "현재 파일 정보 조회 실패", f"오류: {str(e)}", error=e
            )
            return None

    def clear_cache(self) -> None:
        """위치 캐시를 모두 삭제합니다."""
        self.location_cache.clear()
        log_info(
            LogCategory.CACHE, "location_service", "clear_cache",
            "위치 캐시 삭제 완료", "모든 캐시 데이터가 삭제되었습니다"
        )

    # =================================================================
    # 동 단위 데이터 관리 시스템 (Phase 2 추가)
    # =================================================================

    def get_dong_list_by_sigungu_from_json(self, sido_name: str, sigungu_name: str) -> List[Dict[str, str]]:
        """
        JSON 데이터의 dong_hierarchy에서 동 목록을 반환합니다.

        Args:
            sido_name: 시/도명
            sigungu_name: 시/군/구명

        Returns:
            동 정보 리스트 (기존 캐시 형식과 호환)
        """
        try:
            if not self.districts_data:
                log_warning(
                    LogCategory.FILE_OPERATION, "location_service", "get_dong_list_by_sigungu_from_json",
                    "districts 데이터 없음", "districts_data가 로드되지 않음"
                )
                return []

            dong_hierarchy = self.districts_data.get('dong_hierarchy', {})

            if sido_name not in dong_hierarchy:
                log_info(
                    LogCategory.FILE_OPERATION, "location_service", "get_dong_list_by_sigungu_from_json",
                    "시도 데이터 없음", f"시도: {sido_name}"
                )
                return []

            if sigungu_name not in dong_hierarchy[sido_name]:
                log_info(
                    LogCategory.FILE_OPERATION, "location_service", "get_dong_list_by_sigungu_from_json",
                    "시군구 데이터 없음", f"시도: {sido_name}, 시군구: {sigungu_name}"
                )
                return []

            dong_list_raw = dong_hierarchy[sido_name][sigungu_name]

            # 기존 캐시 형식과 호환되도록 변환
            dong_list = []
            for dong_info in dong_list_raw:
                dong_entry = {
                    'dong': dong_info.get('dong', ''),
                    'legal_dong': dong_info.get('dong', ''),  # 법정동으로 간주
                    'admin_dong': '',  # 행정동 정보는 별도 관리 필요시 추가
                    'dong_type': dong_info.get('type', '법정동')
                }
                dong_list.append(dong_entry)

            log_info(
                LogCategory.FILE_OPERATION, "location_service", "get_dong_list_by_sigungu_from_json",
                "JSON에서 동 목록 조회 성공",
                f"시도: {sido_name}, 시군구: {sigungu_name}, 동 수: {len(dong_list)}"
            )

            return dong_list

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "location_service", "get_dong_list_by_sigungu_from_json",
                "JSON 동 목록 조회 실패",
                f"시도: {sido_name}, 시군구: {sigungu_name}, 오류: {str(e)}",
                error=e
            )
            return []

    def get_dong_list_by_sigungu(self, sido_name: str, sigungu_name: str) -> List[Dict[str, str]]:
        """특정 시/도, 시/군/구의 동 목록을 반환합니다."""
        try:
            dong_cache_path = self._get_dong_cache_file_path(sido_name, sigungu_name)

            if os.path.exists(dong_cache_path):
                with open(dong_cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return cache_data.get('dong_list', [])
            else:
                log_info(
                    LogCategory.CACHE, "location_service", "get_dong_list_by_sigungu",
                    "동 캐시 파일 없음", f"파일: {dong_cache_path}"
                )
                return []

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "location_service", "get_dong_list_by_sigungu",
                "동 목록 로드 실패", f"시도: {sido_name}, 시군구: {sigungu_name}, 오류: {str(e)}", error=e
            )
            return []

    def cache_dong_info(self, sido: str, sigungu: str, legal_dong: str, admin_dong: str) -> None:
        """VWorld API 응답에서 추출한 동 정보를 캐시에 저장합니다."""
        try:
            # 캐시 파일 경로 결정
            dong_cache_path = self._get_dong_cache_file_path(sido, sigungu)

            # 기존 캐시 데이터 로드 또는 새 데이터 구조 생성
            if os.path.exists(dong_cache_path):
                with open(dong_cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            else:
                cache_data = {
                    'sido': sido,
                    'sigungu': sigungu,
                    'dong_list': [],
                    'last_updated': None,
                    'sample_count': 0
                }

            # 동 정보 정리
            dong_entry = {
                'legal_dong': legal_dong or '',
                'admin_dong': admin_dong or '',
                'dong': legal_dong if legal_dong else admin_dong,  # 대표 동
                'dong_type': "법정동" if legal_dong else ("행정동" if admin_dong else None)
            }

            # 중복 확인 - 이미 같은 동 정보가 있는지 체크
            existing_dong = None
            for existing in cache_data['dong_list']:
                if (existing.get('legal_dong') == dong_entry['legal_dong'] and
                    existing.get('admin_dong') == dong_entry['admin_dong']):
                    existing_dong = existing
                    break

            if not existing_dong and dong_entry['dong']:  # 동 정보가 있고 중복이 아닌 경우만 추가
                cache_data['dong_list'].append(dong_entry)
                cache_data['sample_count'] = len(cache_data['dong_list'])
                cache_data['last_updated'] = datetime.now().isoformat()

                # 디렉토리 생성 (필요시)
                os.makedirs(os.path.dirname(dong_cache_path), exist_ok=True)

                # 캐시 파일 저장
                with open(dong_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)

                log_info(
                    LogCategory.CACHE, "location_service", "cache_dong_info",
                    "동 정보 캐시 저장",
                    f"시도: {sido}, 시군구: {sigungu}, 동: {dong_entry['dong']}({dong_entry['dong_type']})"
                )

        except Exception as e:
            log_error(
                LogCategory.CACHE, "location_service", "cache_dong_info",
                "동 정보 캐싱 실패",
                f"시도: {sido}, 시군구: {sigungu}, 법정동: {legal_dong}, 행정동: {admin_dong}, 오류: {str(e)}",
                error=e
            )

    def validate_location_with_dong(self, sido: str, sigungu: str, dong: str = None) -> Dict[str, Any]:
        """선택된 시/도, 시/군/구, 동이 유효한지 검증합니다."""
        # 기본 시/도, 시/군/구 검증
        base_validation = self.validate_location(sido, sigungu)

        if not base_validation['valid']:
            return base_validation

        # 동이 제공된 경우 JSON 데이터에서 검증
        if dong:
            # JSON 데이터에서 동 목록 가져오기 (캐시 의존성 제거)
            dong_list = self.get_dong_list_by_sigungu_from_json(sido, sigungu)

            # 동 목록에서 일치하는 동 찾기
            matching_dong = None
            for dong_info in dong_list:
                if dong_info.get('dong') == dong:
                    matching_dong = dong_info
                    break

            if not matching_dong:
                # 캐시 오류 메시지 제거 - 단순히 유효하지 않다고 안내
                return {
                    'valid': False,
                    'message': f'"{sido} {sigungu} {dong}"는 유효하지 않은 동입니다.'
                }

            return {
                'valid': True,
                'message': '유효한 위치입니다.',
                'district_data': base_validation['district_data'],
                'dong_data': matching_dong
            }

        return base_validation

    def get_location_info_with_dong(self, sido: str, sigungu: str, dong: str = None) -> Dict[str, Any]:
        """시/도, 시/군/구, 동 정보로 위치 정보를 구성합니다."""
        validation = self.validate_location_with_dong(sido, sigungu, dong)

        if not validation['valid']:
            return {
                'success': False,
                'message': validation['message'],
                'data': None
            }

        location_data = {
            'sido': sido,
            'sigungu': sigungu,
            'full_address': f"{sido} {sigungu}",
            'coords': None,
            'method': 'manual'
        }

        # 동 정보가 있으면 추가
        if dong and validation.get('dong_data'):
            dong_data = validation['dong_data']
            location_data.update({
                'legal_dong': dong_data.get('legal_dong', ''),
                'admin_dong': dong_data.get('admin_dong', ''),
                'dong': dong_data.get('dong', dong),
                'dong_type': dong_data.get('dong_type', ''),
                'full_address': f"{sido} {sigungu} {dong}"
            })

        return {
            'success': True,
            'message': '수동으로 선택된 위치입니다.',
            'data': location_data
        }

    def _get_dong_cache_file_path(self, sido: str, sigungu: str) -> str:
        """시/도, 시/군/구를 기반으로 동 캐시 파일 경로를 생성합니다."""
        # 파일명 안전화 (특수문자 제거)
        safe_sido = sido.replace('특별시', '').replace('광역시', '').replace('특별자치시', '').replace('도', '').replace(' ', '')
        safe_sigungu = sigungu.replace('시', '').replace('군', '').replace('구', '').replace(' ', '')

        filename = f"{safe_sido}_{safe_sigungu}.json"
        return os.path.join(os.getcwd(), "uploads", "dong_cache", filename)

    def get_dong_list_by_sampling(self, sido: str, sigungu: str, sample_count: int = 10) -> List[Dict[str, str]]:
        """
        ⚠️  DEPRECATED: 실시간 API 호출 방식에서 JSON 기반 방식으로 변경됨

        이 메서드는 더 이상 실시간 API 호출을 하지 않습니다.
        대신 get_dong_list_by_sigungu_from_json() 메서드를 호출합니다.

        Args:
            sido: 시/도명
            sigungu: 시/군/구명
            sample_count: 무시됨 (하위 호환성을 위해 유지)

        Returns:
            동 정보 리스트
        """
        log_info(
            LogCategory.WEB_API, "location_service", "get_dong_list_by_sampling",
            "DEPRECATED 메서드 호출됨 - JSON 기반 메서드로 리다이렉트",
            f"시도: {sido}, 시군구: {sigungu}"
        )

        # 새로운 JSON 기반 메서드로 리다이렉트
        return self.get_dong_list_by_sigungu_from_json(sido, sigungu)
        log_info(
            LogCategory.WEB_API, "location_service", "get_dong_list_by_sampling",
            "실시간 동 목록 수집 시작", f"시도: {sido}, 시군구: {sigungu}, 샘플: {sample_count}개"
        )

        # VWorld API 키 확인
        if not self.config.vworld_api_key:
            return []

        # 기존 캐시 확인
        existing_dong_list = self.get_dong_list_by_sigungu(sido, sigungu)
        if len(existing_dong_list) >= sample_count:
            log_info(
                LogCategory.CACHE, "location_service", "get_dong_list_by_sampling",
                "충분한 캐시 데이터 존재", f"캐시된 동: {len(existing_dong_list)}개"
            )
            return existing_dong_list

        # 해당 시/군/구의 대표 좌표들을 샘플링 (실제로는 지역별 좌표 DB가 필요하지만 임시로 고정값 사용)
        sample_coordinates = self._get_sample_coordinates_for_region(sido, sigungu)

        collected_dongs = []
        success_count = 0

        for idx, (lat, lng) in enumerate(sample_coordinates[:sample_count]):
            try:
                log_info(
                    LogCategory.WEB_API, "location_service", "get_dong_list_by_sampling",
                    f"샘플 좌표 조회 {idx+1}/{len(sample_coordinates)}", f"좌표: {lat}, {lng}"
                )

                result = self._get_location_from_vworld(lat, lng)

                if result['success']:
                    data = result['data']
                    if (data.get('sido') == sido and data.get('sigungu') == sigungu and
                        (data.get('legal_dong') or data.get('admin_dong'))):

                        dong_info = {
                            'legal_dong': data.get('legal_dong', ''),
                            'admin_dong': data.get('admin_dong', ''),
                            'dong': data.get('dong', ''),
                            'dong_type': data.get('dong_type', '')
                        }

                        # 중복 확인
                        if not any(d.get('dong') == dong_info['dong'] for d in collected_dongs):
                            collected_dongs.append(dong_info)
                            success_count += 1

                # 너무 빠른 API 호출 방지
                import time
                time.sleep(0.1)

            except Exception as e:
                log_warning(
                    LogCategory.WEB_API, "location_service", "get_dong_list_by_sampling",
                    f"샘플 좌표 {idx+1} 조회 실패", f"오류: {str(e)}"
                )
                continue

        log_info(
            LogCategory.WEB_API, "location_service", "get_dong_list_by_sampling",
            "실시간 동 목록 수집 완료", f"수집된 동: {len(collected_dongs)}개, 성공률: {success_count}/{len(sample_coordinates)}"
        )

        # 기존 캐시와 병합
        if existing_dong_list:
            merged_list = existing_dong_list.copy()
            for new_dong in collected_dongs:
                if not any(d.get('dong') == new_dong['dong'] for d in merged_list):
                    merged_list.append(new_dong)
            return merged_list

        return collected_dongs

    def _get_sample_coordinates_for_region(self, sido: str, sigungu: str) -> List[Tuple[float, float]]:
        """시/군/구별 샘플 좌표를 반환합니다. (실제로는 지역별 좌표 DB가 필요)"""
        # 주요 지역별 샘플 좌표 (임시 데이터)
        region_samples = {
            ("서울특별시", "강남구"): [
                (37.5007, 127.0366),  # 역삼동
                (37.5125, 127.0296),  # 논현동
                (37.5274, 127.0280),  # 압구정동
                (37.5145, 127.0473),  # 청담동
                (37.4951, 127.0306),  # 대치동
                (37.5185, 127.0516),  # 삼성동
            ],
            ("서울특별시", "종로구"): [
                (37.5869, 126.9732),  # 청운동
                (37.5851, 126.9800),  # 효자동
                (37.5796, 126.9770),  # 사직동
                (37.5735, 126.9788),  # 종로1가
            ],
            ("서울특별시", "마포구"): [
                (37.5459, 126.9223),  # 합정동
                (37.5565, 126.9239),  # 상수동
                (37.5663, 126.9779),  # 연남동
                (37.5512, 126.9542),  # 서교동
            ]
        }

        # 해당 지역의 샘플 좌표가 있으면 반환, 없으면 빈 리스트
        return region_samples.get((sido, sigungu), [])