"""
District Link 세부내역 콘텐츠 관리 서비스입니다.
웹페이지 내용을 복사해서 붙여넣으면 AI가 요약해서 저장합니다.

기능:
- 웹페이지 콘텐츠 AI 분석 및 요약 (Prompt Admin 연동)
- 세부내역 CRUD (저장, 조회, 수정, 삭제)
"""

import json
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime

from src.app.core.config import Config
from src.app.core.logger import log_info, log_error, LogCategory
from src.app.core.base_service import BaseService

# ===== Feature ID 상수 (Prompt Admin과 연동) =====
FEATURE_ID_DISPOSAL_INFO = "detail_content_disposal_info"  # 배출정보 프롬프트
FEATURE_ID_FEE_INFO = "detail_content_fee_info"  # 수수료 프롬프트
# ================================================


class DetailContentService(BaseService):
    """세부내역 콘텐츠 관리 서비스"""

    def get_service_name(self) -> str:
        """서비스 이름"""
        return "DetailContentService"

    def get_service_version(self) -> str:
        """서비스 버전"""
        return "2.0.0"

    def get_service_description(self) -> str:
        """서비스 설명"""
        return "웹페이지 내용을 AI로 분석하여 배출정보 및 수수료 정보를 관리합니다"

    def __init__(self, config: Optional[Config] = None):
        """
        서비스 초기화

        Args:
            config: 앱 설정
        """
        if config is None:
            from src.app.core.config import load_config
            config = load_config()

        self.config = config

    def _get_storage_filepath(self) -> str:
        """세부내역 데이터를 저장할 파일 경로 반환"""
        from src.domains.infrastructure.services.link_collector_service import get_waste_links_storage_path
        storage_dir = get_waste_links_storage_path(self.config)
        return os.path.join(storage_dir, "detail_contents.json")

    def _load_detail_contents(self) -> Dict[str, Any]:
        """저장된 세부내역 데이터 로드"""
        filepath = self._get_storage_filepath()

        if not os.path.exists(filepath):
            return {
                "metadata": {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                },
                "contents": {}
            }

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "_load_detail_contents",
                "세부내역 파일 로드 실패", f"Error: {str(e)}", error=e
            )
            return {"metadata": {}, "contents": {}}

    def _save_detail_contents(self, data: Dict[str, Any]) -> bool:
        """세부내역 데이터 저장"""
        filepath = self._get_storage_filepath()
        data["metadata"]["last_updated"] = datetime.now().isoformat()

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "_save_detail_contents",
                "세부내역 파일 저장 실패", f"Error: {str(e)}", error=e
            )
            return False

    def generate_detail_content(
        self,
        content: str,
        content_type: str,  # 'info' or 'fee'
        district_info: Dict[str, str] = None
    ) -> Optional[str]:
        """
        AI를 사용하여 콘텐츠를 분석하고 마크다운으로 정리

        OpenAI API로부터 마크다운 형식의 응답을 직접 받아 그대로 저장합니다.
        Prompt Admin에 등록된 프롬프트를 동적으로 로드하여 사용합니다.

        Args:
            content: 분석할 콘텐츠 (웹페이지에서 복사한 텍스트)
            content_type: 'info' (배출정보) 또는 'fee' (수수료)
            district_info: 지역 정보 (선택사항)

        Returns:
            마크다운 형식의 응답 텍스트 (변수 주입용)
        """
        try:
            from src.domains.analysis.services.openai_service import OpenAIService

            openai_service = OpenAIService(self.config)
            if not openai_service.is_ready():
                log_error(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "OpenAI 서비스 준비 안됨", "API 키 설정 필요"
                )
                return None

            # Prompt Admin에서 프롬프트 로드
            prompt_template = self._load_prompt_from_admin(content_type)
            if not prompt_template:
                log_error(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "프롬프트 로드 실패", f"Feature ID를 찾을 수 없습니다 (ContentType: {content_type})"
                )
                return None

            # 프롬프트 렌더링
            prompt = self._render_prompt(prompt_template, content, district_info)
            if not prompt:
                return None

            # OpenAI 호출
            try:
                response = openai_service.call_with_prompt(prompt, model="gpt-4o-mini")
            except Exception as api_error:
                log_error(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "OpenAI API 호출 중 오류 발생", f"Error: {str(api_error)}", error=api_error
                )
                return None

            if not response or not response.strip():
                log_error(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "OpenAI 응답 없음", f"ContentType: {content_type}"
                )
                return None

            # 응답 완전성 확인 (디버깅)
            response_text = response.strip()
            response_len = len(response_text)

            # JSON 형식 응답인 경우 완전성 확인
            if response_text.startswith('[') and response_text.endswith(']'):
                # 유효한 JSON 배열로 종료
                log_info(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "세부내역 생성 성공 (완전한 JSON)", f"ContentType: {content_type}, Length: {response_len}"
                )
            elif response_text.startswith('##') or response_text.startswith('**'):
                # 마크다운 형식
                log_info(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "세부내역 생성 성공 (마크다운)", f"ContentType: {content_type}, Length: {response_len}"
                )
            else:
                # 기타 형식
                log_info(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "세부내역 생성 성공", f"ContentType: {content_type}, Length: {response_len}, Format: {response_text[:50]}..."
                )

            # 불완전한 JSON 감지
            if response_text.startswith('[') and not response_text.endswith(']'):
                log_error(
                    LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                    "⚠️  응답이 불완전한 JSON입니다!",
                    f"ContentType: {content_type}, Length: {response_len}, LastChars: ...{response_text[-50:]}"
                )

            return response_text

        except Exception as e:
            log_error(
                LogCategory.API_CALL, "detail_content_service", "generate_detail_content",
                "세부내역 생성 실패", f"Error: {str(e)}", error=e
            )
            return None


    def _load_prompt_from_admin(self, content_type: str) -> Optional[str]:
        """
        Prompt Admin에서 프롬프트 템플릿 로드

        Args:
            content_type: 'info' 또는 'fee'

        Returns:
            프롬프트 템플릿 문자열
        """
        try:
            # Feature ID 결정
            if content_type == 'info':
                feature_id = FEATURE_ID_DISPOSAL_INFO
            elif content_type == 'fee':
                feature_id = FEATURE_ID_FEE_INFO
            else:
                return None

            log_info(
                LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                "프롬프트 로드 시작", f"ContentType: {content_type}, Feature ID: {feature_id}"
            )

            # Feature Registry에서 프롬프트 ID 조회 (PromptService 없이도 직접 가능)
            try:
                from src.app.core.prompt_feature_registry import PromptFeatureRegistry
                registry = PromptFeatureRegistry()
                feature = registry.get_feature(feature_id)

                if not feature:
                    log_info(
                        LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                        "Feature 찾음 실패", f"Feature ID: {feature_id}"
                    )
                    return self._get_fallback_prompt_template(content_type)

                prompt_id = feature.metadata.get('prompt_id')
                if not prompt_id:
                    log_info(
                        LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                        "Prompt ID 찾음 실패", f"Feature: {feature_id}"
                    )
                    return self._get_fallback_prompt_template(content_type)

                log_info(
                    LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                    "Prompt ID 조회 성공", f"Feature: {feature_id}, Prompt ID: {prompt_id}"
                )

                # 🔵 우선순위 1: 로컬 파일에서 직접 로드 (최신 프롬프트)
                prompt_template = self._load_prompt_from_local_file(prompt_id)
                if prompt_template:
                    log_info(
                        LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                        "프롬프트 로드 성공 (로컬 파일 - 우선)", f"Prompt ID: {prompt_id}"
                    )
                    return prompt_template

                # 🟡 우선순위 2: PromptService에서 로드 (캐시된 프롬프트)
                try:
                    from src.app.core.app_factory import ApplicationFactory
                    app_context = ApplicationFactory.create_application()
                    prompt_service = app_context.get_service('prompt_service')

                    if prompt_service:
                        prompt_obj = prompt_service.get_prompt(prompt_id)
                        if prompt_obj:
                            log_info(
                                LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                                "프롬프트 로드 성공 (PromptService - 우선 2)", f"Feature: {feature_id}, Prompt ID: {prompt_id}"
                            )
                            return prompt_obj.template

                except Exception as e:
                    log_info(
                        LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                        "PromptService 로드 시도 실패", f"Error: {str(e)}"
                    )

                # 🔴 우선순위 3: Fallback 프롬프트 사용
                log_info(
                    LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                    "로컬/PromptService 모두 실패", f"Prompt ID: {prompt_id} (폴백 프롬프트 사용)"
                )
                return self._get_fallback_prompt_template(content_type)

            except Exception as e:
                log_error(
                    LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                    "Feature Registry 로드 오류", str(e), error=e
                )
                return self._get_fallback_prompt_template(content_type)

        except Exception as e:
            log_error(
                LogCategory.API_CALL, "detail_content_service", "_load_prompt_from_admin",
                "프롬프트 로드 오류", str(e), error=e
            )
            return None

    def _load_prompt_from_local_file(self, prompt_id: str) -> Optional[str]:
        """
        로컬 파일에서 프롬프트 직접 로드

        Args:
            prompt_id: 프롬프트 ID (파일명)

        Returns:
            프롬프트 템플릿 문자열
        """
        try:
            import os
            from pathlib import Path

            # 프롬프트 파일 경로
            prompt_file_path = os.path.join(
                os.path.dirname(__file__),
                "../../../data/prompts/templates",
                f"{prompt_id}.json"
            )

            # 절대 경로로 변환
            prompt_file_path = os.path.abspath(prompt_file_path)

            if not os.path.exists(prompt_file_path):
                log_info(
                    LogCategory.FILE_OPERATION, "detail_content_service", "_load_prompt_from_local_file",
                    "프롬프트 파일 찾기 실패", f"Path: {prompt_file_path}"
                )
                return None

            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            template = prompt_data.get('template')
            if template:
                log_info(
                    LogCategory.FILE_OPERATION, "detail_content_service", "_load_prompt_from_local_file",
                    "프롬프트 로드 성공", f"Prompt ID: {prompt_id}"
                )
                return template
            else:
                log_info(
                    LogCategory.FILE_OPERATION, "detail_content_service", "_load_prompt_from_local_file",
                    "Template 필드 없음", f"Prompt ID: {prompt_id}"
                )
                return None

        except json.JSONDecodeError as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "_load_prompt_from_local_file",
                "JSON 파싱 실패", str(e), error=e
            )
            return None
        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "_load_prompt_from_local_file",
                "로컬 파일 로드 실패", str(e), error=e
            )
            return None

    def _get_fallback_prompt_template(self, content_type: str) -> Optional[str]:
        """
        로컬 프롬프트 템플릿 폴백 (PromptService 미사용 시)

        Args:
            content_type: 'info' 또는 'fee'

        Returns:
            프롬프트 템플릿 문자열
        """
        try:
            from src.domains.infrastructure.services.detail_content_prompts import (
                get_info_extraction_prompt_template,
                get_fee_extraction_prompt_template
            )

            if content_type == 'info':
                return get_info_extraction_prompt_template()
            elif content_type == 'fee':
                return get_fee_extraction_prompt_template()
            else:
                return None

        except Exception as e:
            log_error(
                LogCategory.API_CALL, "detail_content_service", "_get_fallback_prompt_template",
                "폴백 프롬프트 로드 실패", str(e), error=e
            )
            return None

    def _render_prompt(
        self,
        template: str,
        content: str,
        district_info: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        프롬프트 템플릿 렌더링

        Args:
            template: 프롬프트 템플릿
            content: 분석할 콘텐츠
            district_info: 지역 정보

        Returns:
            렌더링된 프롬프트
        """
        try:
            district_context = ""
            if district_info:
                district_context = f"(지역: {district_info.get('sido', '')} {district_info.get('sigungu', '')})"

            # 로깅: 입력 콘텐츠 크기 기록
            log_info(
                LogCategory.API_CALL, "detail_content_service", "_render_prompt",
                "프롬프트 렌더링 시작", f"Content size: {len(content)} characters"
            )

            rendered = template.format(
                district_context=district_context,
                content=content  # 전체 콘텐츠 사용 (제한 없음)
            )

            return rendered

        except Exception as e:
            log_error(
                LogCategory.API_CALL, "detail_content_service", "_render_prompt",
                "프롬프트 렌더링 실패", str(e), error=e
            )
            return None

    def save_detail_content(
        self,
        district_key: str,
        content_type: str,  # 'info' or 'fee'
        detail_content: str  # 마크다운 형태의 내용
    ) -> bool:
        """
        세부내역 저장 (마크다운 형식)

        Args:
            district_key: 지역 키 (예: "서울특별시_강남구")
            content_type: 'info' 또는 'fee'
            detail_content: 저장할 마크다운 형태의 세부내역 내용

        Returns:
            저장 성공 여부
        """
        try:
            # 로깅: 저장 시작
            content_size = len(detail_content) if detail_content else 0
            log_info(
                LogCategory.FILE_OPERATION, "detail_content_service", "save_detail_content",
                "세부내역 저장 시작", f"District: {district_key}, Type: {content_type}, Size: {content_size} characters"
            )

            data = self._load_detail_contents()

            if district_key not in data["contents"]:
                data["contents"][district_key] = {}

            # 마크다운 저장
            if content_type == 'info':
                data["contents"][district_key]["info_detail"] = {
                    "content": detail_content,
                    "created_at": datetime.now().isoformat(),
                    "source": "ai_analyzed"
                }
            elif content_type == 'fee':
                data["contents"][district_key]["fee_detail"] = {
                    "content": detail_content,
                    "created_at": datetime.now().isoformat(),
                    "source": "ai_analyzed"
                }
            else:
                return False

            data["contents"][district_key]["managed_at"] = datetime.now().isoformat()

            if not self._save_detail_contents(data):
                return False

            log_info(
                LogCategory.FILE_OPERATION, "detail_content_service", "save_detail_content",
                "세부내역 저장 성공", f"District: {district_key}, Type: {content_type}, Saved Size: {content_size} characters"
            )
            return True

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "save_detail_content",
                "세부내역 저장 실패", f"District: {district_key}, Error: {str(e)}", error=e
            )
            return False

    def get_detail_content(
        self,
        district_key: str,
        content_type: str  # 'info' or 'fee'
    ) -> Optional[Dict[str, Any]]:
        """
        세부내역 조회

        Args:
            district_key: 지역 키
            content_type: 'info' 또는 'fee'

        Returns:
            세부내역 데이터 (content, created_at, source를 포함)
        """
        try:
            data = self._load_detail_contents()
            district_contents = data["contents"].get(district_key, {})

            if content_type == 'info':
                return district_contents.get("info_detail")
            elif content_type == 'fee':
                return district_contents.get("fee_detail")
            else:
                return None

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "get_detail_content",
                "세부내역 조회 실패", f"District: {district_key}, Error: {str(e)}", error=e
            )
            return None

    def delete_detail_content(
        self,
        district_key: str,
        content_type: str  # 'info' or 'fee' or 'all'
    ) -> bool:
        """
        세부내역 삭제

        Args:
            district_key: 지역 키
            content_type: 'info', 'fee', 또는 'all' (전체 삭제)

        Returns:
            삭제 성공 여부
        """
        try:
            data = self._load_detail_contents()

            if district_key not in data["contents"]:
                return True  # 이미 없음

            if content_type == 'all':
                del data["contents"][district_key]
            elif content_type == 'info':
                if "info_detail" in data["contents"][district_key]:
                    del data["contents"][district_key]["info_detail"]
            elif content_type == 'fee':
                if "fee_detail" in data["contents"][district_key]:
                    del data["contents"][district_key]["fee_detail"]
            else:
                return False

            if not self._save_detail_contents(data):
                return False

            log_info(
                LogCategory.FILE_OPERATION, "detail_content_service", "delete_detail_content",
                "세부내역 삭제 성공", f"District: {district_key}, Type: {content_type}"
            )
            return True

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "delete_detail_content",
                "세부내역 삭제 실패", f"District: {district_key}, Error: {str(e)}", error=e
            )
            return False

    def get_all_detail_contents(self) -> Dict[str, Any]:
        """모든 세부내역 조회"""
        return self._load_detail_contents()

    def get_all_detail_content_by_type(
        self,
        district_key: str
    ) -> Dict[str, Optional[str]]:
        """
        지역별 모든 세부내역 조회 (info와 fee 모두)

        배출방법 확인 시 마크다운 형태의 상세 내용을 프롬프트에 주입할 때 사용

        Args:
            district_key: 지역 키 (예: "서울특별시_강남구")

        Returns:
            {
                'info_content': '배출정보 마크다운 내용 또는 None',
                'fee_content': '수수료 마크다운 내용 또는 None'
            }
        """
        try:
            info_detail = self.get_detail_content(district_key, 'info')
            fee_detail = self.get_detail_content(district_key, 'fee')

            info_content = None
            fee_content = None

            # info_detail 추출
            if info_detail:
                if isinstance(info_detail, dict):
                    info_content = info_detail.get('content')
                else:
                    # 레거시 형식 (문자열)
                    info_content = str(info_detail)

            # fee_detail 추출
            if fee_detail:
                if isinstance(fee_detail, dict):
                    fee_content = fee_detail.get('content')
                else:
                    # 레거시 형식 (문자열)
                    fee_content = str(fee_detail)

            log_info(
                LogCategory.FILE_OPERATION, "detail_content_service", "get_all_detail_content_by_type",
                "세부내역 통합 조회 성공", f"District: {district_key}, info_exists: {bool(info_content)}, fee_exists: {bool(fee_content)}"
            )

            return {
                'info_content': info_content,
                'fee_content': fee_content
            }

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "get_all_detail_content_by_type",
                "세부내역 통합 조회 실패", f"District: {district_key}, Error: {str(e)}", error=e
            )
            return {
                'info_content': None,
                'fee_content': None
            }
