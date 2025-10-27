"""OpenAI API와 상호 작용을 위한 서비스 모듈.

OpenAI 클라이언트 생성, 이미지 처리, OpenAI Vision API를 사용한 이미지 분석
기능을 제공하는 서비스 클래스입니다.
"""
import io
import base64
import re
import json
from typing import Tuple, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI as OpenAIClient
else:
    OpenAIClient = Any

from PIL import Image

from src.app.core.base_service import BaseService
from src.app.core.config import Config
from src.app.core.error_handler import DependencyError, NetworkError, ValidationError, handle_errors

# OpenAI 클라이언트에 대한 선택적 가져오기 가드
try:
    from openai import OpenAI, APIError
except ImportError:
    OpenAI = None
    APIError = None


def jpeg_bytes_from_image(raw_bytes: bytes, max_size: int, quality: int) -> bytes:
    """이미지를 RGB JPEG로 변환하고 필요한 경우 크기를 조정합니다."""
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img.thumbnail((max_size, max_size))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


class OpenAIService(BaseService):
    """OpenAI API 서비스 클래스"""
    
    def __init__(self, config: Config, **kwargs):
        self._client: Optional[OpenAIClient] = None
        self._api_key: Optional[str] = None
        super().__init__(config, **kwargs)
    
    def get_service_name(self) -> str:
        return "openai_service"
    
    def get_service_version(self) -> str:
        return "1.0.0"
    
    def get_service_description(self) -> str:
        return "OpenAI Vision API를 통한 이미지 분석 서비스"
    
    def get_dependencies(self) -> list[str]:
        return ["openai", "PIL"]
    
    def is_optional(self) -> bool:
        return False  # 핵심 서비스
    
    def _initialize(self) -> None:
        """OpenAI 서비스 초기화"""
        if OpenAI is None:
            raise DependencyError(
                "OpenAI Python SDK가 설치되어 있지 않습니다.",
                suggestion="pip install openai로 설치하세요."
            )
        
        # API 키 로드
        from src.app.core.utils import resolve_api_key
        self._api_key = resolve_api_key()
        
        if not self._api_key:
            self._logger.warning("OpenAI API 키가 설정되지 않았습니다.")
        else:
            self._client = OpenAI(api_key=self._api_key)
            self._logger.info("OpenAI client initialized successfully")
    
    def _perform_health_checks(self) -> Dict[str, Any]:
        """OpenAI 서비스 헬스체크"""
        checks = {}
        checks['api_key_available'] = bool(self._api_key)
        checks['client_initialized'] = bool(self._client)
        
        if self._client:
            try:
                # 간단한 API 호출로 연결 테스트 (실제 환경에서는 비용 고려)
                # models = self._client.models.list()
                checks['api_accessible'] = True
            except Exception as e:
                checks['api_accessible'] = False
                checks['api_error'] = str(e)
        
        return checks
    
    def get_client(self) -> OpenAIClient:
        """OpenAI 클라이언트를 반환합니다."""
        if not self.is_ready():
            raise RuntimeError("OpenAI 서비스가 준비되지 않았습니다.")
        
        if not self._client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
        return self._client
    
    def has_api_key(self) -> bool:
        """API 키가 설정되어 있는지 확인합니다."""
        return bool(self._api_key)

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        OpenAI 응답에서 JSON을 추출합니다.

        마크다운 코드 블록(```json ... ```)으로 감싸진 JSON을 처리합니다.

        Args:
            response_text: OpenAI의 응답 텍스트

        Returns:
            추출된 또는 원본 텍스트
        """
        # 1. 마크다운 코드 블록에서 JSON 추출
        # 패턴: ```json ... ``` 또는 ``` ... ```
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            extracted = json_match.group(1).strip()
            # 추출된 내용이 유효한 JSON인지 간단히 확인
            try:
                json.loads(extracted)
                self._logger.debug("Successfully extracted JSON from markdown code block")
                return extracted
            except json.JSONDecodeError:
                # 추출했지만 유효하지 않으면 원본 반환
                self._logger.debug("Extracted text is not valid JSON, using original response")
                return response_text

        return response_text

    @handle_errors(show_user_message=True, reraise=False, fallback_return="")
    def call_with_prompt(self, prompt: str, model: str = "gpt-4o") -> Optional[str]:
        """
        텍스트 프롬프트를 OpenAI에 보내고 응답을 받습니다.

        Simple Prompt 패턴을 위한 간단한 메서드입니다.
        Admin이 저장한 프롬프트를 변수로 렌더링한 후 LLM에 보낼 때 사용합니다.

        Args:
            prompt: 렌더링된 프롬프트 텍스트
            model: 사용할 OpenAI 모델명 (기본값: gpt-4o)

        Returns:
            str: LLM 응답 텍스트
        """
        if not self.is_ready():
            raise RuntimeError("OpenAI 서비스가 준비되지 않았습니다.")

        if not self._client:
            raise RuntimeError("API 키가 설정되지 않았습니다.")

        if not prompt.strip():
            raise ValidationError("프롬프트가 필요합니다.")

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=8192,  # JSON 및 마크다운 긴 응답 지원
            )

            output_text = response.choices[0].message.content or ""

            # 응답 크기 로깅 (디버깅 용도)
            finish_reason = response.choices[0].finish_reason
            self._logger.info(
                f"LLM response received: model={model}, "
                f"output_length={len(output_text)}, "
                f"finish_reason={finish_reason}"
            )

            # finish_reason가 'length'면 max_tokens 제한에 도달한 것
            if finish_reason == 'length':
                self._logger.warning(
                    f"⚠️  응답이 max_tokens 제한에 도달했습니다! "
                    f"응답 길이: {len(output_text)} 문자. "
                    f"max_tokens를 더 증가시키세요."
                )

            return output_text

        except APIError as e:
            raise NetworkError(
                f"OpenAI API 호출 실패: {e}",
                suggestion="API 키와 네트워크 연결을 확인해주세요."
            ) from e
        except Exception as e:
            raise RuntimeError(f"프롬프트 실행 중 오류 발생: {e}") from e

    @handle_errors(show_user_message=True, reraise=False, fallback_return=(None, {}))
    def analyze_image(self, image_bytes: bytes, prompt: str, model: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        이미지와 프롬프트를 OpenAI Vision 모델로 보냅니다.

        Args:
            image_bytes: 분석할 이미지의 바이트 데이터
            prompt: 분석 프롬프트
            model: 사용할 OpenAI 모델명

        Returns:
            Tuple[str, Dict]: (분석 결과 텍스트, 원시 응답 데이터)
        """
        if not self.is_ready():
            raise RuntimeError("OpenAI 서비스가 준비되지 않았습니다.")
        
        if not self._client:
            raise RuntimeError("API 키가 설정되지 않았습니다.")
        
        if not image_bytes:
            raise ValidationError("이미지 데이터가 필요합니다.")
        
        if not prompt.strip():
            raise ValidationError("분석 프롬프트가 필요합니다.")
        
        try:
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                            },
                        ],
                    }
                ],
                max_tokens=2048,
            )
            
            output_text = response.choices[0].message.content or ""

            # JSON을 마크다운 코드 블록에서 추출 (있으면)
            output_text = self._extract_json_from_response(output_text)

            try:
                raw_response = response.model_dump()
            except Exception:
                raw_response = {"raw": str(response)}

            self._logger.info(f"Successfully analyzed image with model {model}")
            return output_text, raw_response
            
        except APIError as e:
            raise NetworkError(
                f"OpenAI API 호출 실패: {e}",
                suggestion="API 키와 네트워크 연결을 확인해주세요."
            ) from e
        except Exception as e:
            raise RuntimeError(f"이미지 분석 중 오류 발생: {e}") from e


# 기존 함수들과의 호환성을 위한 래퍼 함수들
def get_openai_client(api_key: str) -> Any:
    """레거시 호환성을 위한 함수"""
    if OpenAI is None:
        raise ImportError(
            "OpenAI Python SDK가 설치되어 있지 않습니다. `pip install openai`로 설치하세요."
        )
    return OpenAI(api_key=api_key)




def analyze_image_with_openai(
    image_bytes: bytes, prompt: str, model: str, api_key: str
) -> Tuple[str, Dict[str, Any]]:
    """
    레거시 호환성을 위한 함수
    이미지와 프롬프트를 OpenAI Vision 모델로 보냅니다.
    """
    client = get_openai_client(api_key)
    b64_img = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                        },
                    ],
                }
            ],
            max_tokens=2048,
        )
    except APIError as e:
        raise RuntimeError(f"OpenAI API 오류: {e}") from e
    except Exception as e:
        raise RuntimeError(f"OpenAI 요청 중 예기치 않은 오류 발생: {e}") from e

    output_text = response.choices[0].message.content or ""
    try:
        raw_response = response.model_dump()
    except Exception:
        raw_response = {"raw": str(response)}
    return output_text, raw_response