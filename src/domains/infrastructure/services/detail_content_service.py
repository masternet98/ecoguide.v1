"""
District Link 세부내역 콘텐츠 관리 서비스입니다.
URL/PDF에서 배출정보 및 수수료 정보를 자동 추출하거나 수동으로 등록·관리합니다.

기능:
- URL 콘텐츠 수집 및 파싱
- PDF 파일에서 텍스트 추출
- OpenAI를 활용한 자동 정리/요약
- 세부내역 CRUD (저장, 조회, 수정, 삭제)
"""

import json
import os
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from io import BytesIO

from src.app.core.config import Config
from src.app.core.logger import log_info, log_error, LogCategory
from src.app.core.base_service import BaseService


class DetailContentService(BaseService):
    """세부내역 콘텐츠 관리 서비스"""

    def get_service_name(self) -> str:
        """서비스 이름"""
        return "DetailContentService"

    def get_service_version(self) -> str:
        """서비스 버전"""
        return "1.0.0"

    def get_service_description(self) -> str:
        """서비스 설명"""
        return "URL/PDF에서 배출정보 및 수수료 정보를 추출하고 관리합니다"

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
        self._try_import_dependencies()

    def _try_import_dependencies(self):
        """필요한 외부 라이브러리 임포트 시도"""
        self.has_beautifulsoup = False
        self.has_pypdf = False
        self.has_pdfplumber = False

        try:
            import bs4
            self.has_beautifulsoup = True
        except ImportError:
            log_info(
                LogCategory.INITIALIZATION, "detail_content_service", "__init__",
                "BeautifulSoup4 미설치", "URL 파싱 기능 사용 불가"
            )

        try:
            import pypdf
            self.has_pypdf = True
        except ImportError:
            pass

        try:
            import pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            pass

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

    def extract_info_from_url(self, url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        URL에서 콘텐츠 추출

        Args:
            url: 추출할 URL

        Returns:
            (콘텐츠, 메타데이터) 튜플
        """
        if not url or not url.startswith(('http://', 'https://')):
            return None, {"error": "유효한 URL이 아닙니다"}

        try:
            # 타임아웃 설정하여 요청
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            response.raise_for_status()

            # HTML 파싱
            if self.has_beautifulsoup:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # 스크립트 및 스타일 제거
                for script in soup(["script", "style"]):
                    script.decompose()

                # 텍스트 추출
                text = soup.get_text(separator='\n', strip=True)

                # 중복 줄바꿈 제거
                text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())

                metadata = {
                    "url": url,
                    "title": soup.title.string if soup.title else "Unknown",
                    "content_length": len(text),
                    "extracted_at": datetime.now().isoformat()
                }

                log_info(
                    LogCategory.EXTERNAL_API, "detail_content_service", "extract_info_from_url",
                    "URL 콘텐츠 추출 성공", f"URL: {url[:50]}..., Length: {len(text)}"
                )

                return text, metadata
            else:
                # BeautifulSoup 없으면 raw text 반환
                text = response.text[:5000]  # 처음 5000자만
                return text, {"url": url, "note": "BeautifulSoup 미설치 - HTML 파싱 제한"}

        except requests.RequestException as e:
            log_error(
                LogCategory.EXTERNAL_API, "detail_content_service", "extract_info_from_url",
                "URL 콘텐츠 추출 실패", f"URL: {url}, Error: {str(e)}", error=e
            )
            return None, {"error": f"URL 접근 실패: {str(e)}"}
        except Exception as e:
            log_error(
                LogCategory.EXTERNAL_API, "detail_content_service", "extract_info_from_url",
                "예상 외 오류", f"URL: {url}, Error: {str(e)}", error=e
            )
            return None, {"error": f"예상 외 오류: {str(e)}"}

    def extract_info_from_pdf(self, file_path: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        PDF 파일에서 텍스트 추출

        Args:
            file_path: PDF 파일 경로

        Returns:
            (텍스트 콘텐츠, 메타데이터) 튜플
        """
        if not os.path.exists(file_path):
            return None, {"error": "파일이 존재하지 않습니다"}

        try:
            # pdfplumber 우선 시도 (더 나은 텍스트 추출)
            if self.has_pdfplumber:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text_parts = []
                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text()
                        if text:
                            text_parts.append(f"--- 페이지 {page_num} ---\n{text}")

                    text = '\n'.join(text_parts)
                    metadata = {
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "file_size": os.path.getsize(file_path),
                        "page_count": len(pdf.pages),
                        "content_length": len(text),
                        "extracted_at": datetime.now().isoformat(),
                        "method": "pdfplumber"
                    }

                    log_info(
                        LogCategory.FILE_OPERATION, "detail_content_service", "extract_info_from_pdf",
                        "PDF 추출 성공 (pdfplumber)", f"Pages: {len(pdf.pages)}, Length: {len(text)}"
                    )

                    return text, metadata

            # pypdf 사용
            elif self.has_pypdf:
                from pypdf import PdfReader
                with open(file_path, 'rb') as f:
                    pdf_reader = PdfReader(f)
                    text_parts = []
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        text = page.extract_text()
                        if text:
                            text_parts.append(f"--- 페이지 {page_num} ---\n{text}")

                    text = '\n'.join(text_parts)
                    metadata = {
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "file_size": os.path.getsize(file_path),
                        "page_count": len(pdf_reader.pages),
                        "content_length": len(text),
                        "extracted_at": datetime.now().isoformat(),
                        "method": "pypdf"
                    }

                    log_info(
                        LogCategory.FILE_OPERATION, "detail_content_service", "extract_info_from_pdf",
                        "PDF 추출 성공 (pypdf)", f"Pages: {len(pdf_reader.pages)}, Length: {len(text)}"
                    )

                    return text, metadata
            else:
                return None, {"error": "PDF 라이브러리 미설치 (pypdf 또는 pdfplumber 필요)"}

        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "detail_content_service", "extract_info_from_pdf",
                "PDF 추출 실패", f"File: {file_path}, Error: {str(e)}", error=e
            )
            return None, {"error": f"PDF 추출 실패: {str(e)}"}

    def generate_detail_content(
        self,
        content: str,
        content_type: str,  # 'info' or 'fee'
        district_info: Dict[str, str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        OpenAI를 사용하여 콘텐츠를 분석하고 구조화된 정보 생성

        Args:
            content: 분석할 콘텐츠 (URL/PDF에서 추출한 텍스트)
            content_type: 'info' (배출정보) 또는 'fee' (수수료)
            district_info: 지역 정보 (선택사항)

        Returns:
            구조화된 세부내역 딕셔너리
        """
        try:
            from src.domains.analysis.services.openai_service import OpenAIService

            openai_service = OpenAIService(self.config)
            if not openai_service.is_ready():
                log_error(
                    LogCategory.EXTERNAL_API, "detail_content_service", "generate_detail_content",
                    "OpenAI 서비스 준비 안됨", "API 키 설정 필요"
                )
                return None

            # 프롬프트 생성
            if content_type == 'info':
                prompt = self._get_info_extraction_prompt(content, district_info)
            elif content_type == 'fee':
                prompt = self._get_fee_extraction_prompt(content, district_info)
            else:
                return None

            # OpenAI 호출
            response = openai_service.call_with_prompt(prompt, model="gpt-4o")

            if not response:
                log_error(
                    LogCategory.EXTERNAL_API, "detail_content_service", "generate_detail_content",
                    "OpenAI 응답 없음", f"ContentType: {content_type}"
                )
                return None

            # JSON 파싱
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                response = json_match.group(1).strip()

            detail_data = json.loads(response)

            # 메타데이터 추가
            detail_data['source'] = 'ai_generated'
            detail_data['extracted_at'] = datetime.now().isoformat()
            detail_data['model'] = 'gpt-4o'

            log_info(
                LogCategory.EXTERNAL_API, "detail_content_service", "generate_detail_content",
                "세부내역 생성 성공", f"ContentType: {content_type}"
            )

            return detail_data

        except json.JSONDecodeError as e:
            log_error(
                LogCategory.EXTERNAL_API, "detail_content_service", "generate_detail_content",
                "JSON 파싱 실패", f"Error: {str(e)}", error=e
            )
            return None
        except Exception as e:
            log_error(
                LogCategory.EXTERNAL_API, "detail_content_service", "generate_detail_content",
                "세부내역 생성 실패", f"Error: {str(e)}", error=e
            )
            return None

    def _get_info_extraction_prompt(self, content: str, district_info: Optional[Dict[str, str]] = None) -> str:
        """배출정보 추출 프롬프트 생성"""
        district_context = ""
        if district_info:
            district_context = f"\n(지역: {district_info.get('sido', '')} {district_info.get('sigungu', '')})"

        return f"""당신은 대형폐기물 배출 정보 분석 전문가입니다.{district_context}

다음 콘텐츠에서 배출정보를 추출하고 구조화하세요:

---
{content[:3000]}  # 처음 3000자만 사용
---

다음 JSON 형식으로 응답하세요:

```json
{{
  "배출_가능_물품": ["물품1", "물품2"],
  "배출_불가능_물품": ["물품1", "물품2"],
  "배출_방법": "설명",
  "수거_일정": "설명",
  "신청_방법": {{
    "온라인": "설명 또는 빈 문자열",
    "전화": "전화번호 또는 빈 문자열",
    "방문": "주소 또는 빈 문자열"
  }},
  "기본_수수료": "설명",
  "연락처": "전화번호 또는 이메일",
  "운영_시간": "시간 또는 빈 문자열",
  "추가_정보": "기타 중요 정보 또는 빈 문자열",
  "신뢰도": 0.0
}}
```

주의사항:
1. 명확하지 않은 정보는 빈 문자열("")로 처리하세요
2. 신뢰도는 0.0~1.0 범위로 평가하세요
3. 필드값이 모두 비어있으면 안 됩니다 - 최소한 "배출_방법"과 "신뢰도"는 포함하세요
4. JSON만 응답하세요"""

    def _get_fee_extraction_prompt(self, content: str, district_info: Optional[Dict[str, str]] = None) -> str:
        """수수료 정보 추출 프롬프트 생성"""
        district_context = ""
        if district_info:
            district_context = f"\n(지역: {district_info.get('sido', '')} {district_info.get('sigungu', '')})"

        return f"""당신은 대형폐기물 수수료 정보 분석 전문가입니다.{district_context}

다음 콘텐츠에서 수수료 정보를 추출하고 구조화하세요:

---
{content[:3000]}  # 처음 3000자만 사용
---

다음 JSON 형식으로 응답하세요:

```json
{{
  "배출_기준": "물품 크기 기준 설명",
  "요금_표": [
    {{
      "카테고리": "소파",
      "기준": "크기 또는 조건",
      "요금": "10,000원~20,000원",
      "설명": "추가 설명 또는 빈 문자열"
    }}
  ],
  "예약_방법": "설명",
  "결제_방법": "결제 수단",
  "할인": "할인 정보 또는 빈 문자열",
  "추가_정보": "기타 정보 또는 빈 문자열",
  "신뢰도": 0.0
}}
```

주의사항:
1. 요금은 한글 표기 유지 (예: "10,000원~20,000원")
2. 요금_표는 반드시 배열 형식으로, 최소 1개 이상의 항목이 있어야 합니다
3. 신뢰도는 0.0~1.0 범위로 평가하세요
4. 명확하지 않은 정보는 빈 문자열("")로 처리하세요
5. JSON만 응답하세요"""

    def save_detail_content(
        self,
        district_key: str,
        content_type: str,  # 'info' or 'fee'
        detail_data: Dict[str, Any]
    ) -> bool:
        """
        세부내역 저장

        Args:
            district_key: 지역 키 (예: "서울특별시_강남구")
            content_type: 'info' 또는 'fee'
            detail_data: 저장할 세부내역 데이터

        Returns:
            저장 성공 여부
        """
        try:
            data = self._load_detail_contents()

            if district_key not in data["contents"]:
                data["contents"][district_key] = {}

            # 타입에 따라 저장
            if content_type == 'info':
                data["contents"][district_key]["info_detail"] = detail_data
            elif content_type == 'fee':
                data["contents"][district_key]["fee_detail"] = detail_data
            else:
                return False

            data["contents"][district_key]["managed_at"] = datetime.now().isoformat()

            if not self._save_detail_contents(data):
                return False

            log_info(
                LogCategory.FILE_OPERATION, "detail_content_service", "save_detail_content",
                "세부내역 저장 성공", f"District: {district_key}, Type: {content_type}"
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
            세부내역 데이터 (없으면 None)
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

    @property
    def is_ready(self) -> bool:
        """서비스 준비 상태 확인"""
        return self.has_beautifulsoup or self.has_pypdf or self.has_pdfplumber
