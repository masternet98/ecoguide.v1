"""
이 모듈은 OpenAI API와 상호 작용하기 위한 헬퍼 함수를 제공합니다.
OpenAI 클라이언트 생성, 이미지 처리, OpenAI Vision API를 사용한 이미지 분석
기능을 포함합니다.
"""
import io
import base64
from typing import Tuple, Dict, Any

from PIL import Image

# OpenAI 클라이언트에 대한 선택적 가져오기 가드
try:
    from openai import OpenAI, APIError
except ImportError:
    OpenAI = None
    APIError = None


def get_openai_client(api_key: str) -> Any:
    """OpenAI 클라이언트를 가져옵니다. SDK가 설치되지 않은 경우 오류를 발생시킵니다."""
    if OpenAI is None:
        raise ImportError(
            "OpenAI Python SDK가 설치되어 있지 않습니다. `pip install openai`로 설치하세요."
        )
    return OpenAI(api_key=api_key)


def jpeg_bytes_from_image(raw_bytes: bytes, max_size: int, quality: int) -> bytes:
    """이미지를 RGB JPEG로 변환하고 필요한 경우 크기를 조정합니다."""
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img.thumbnail((max_size, max_size))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


def analyze_image_with_openai(
    image_bytes: bytes, prompt: str, model: str, api_key: str
) -> Tuple[str, Dict[str, Any]]:
    """
    이미지와 프롬프트를 OpenAI Vision 모델로 보냅니다.
    (output_text, raw_response_dict)를 반환합니다.
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
