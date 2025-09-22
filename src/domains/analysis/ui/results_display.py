"""
분석 결과 표시 컴포넌트 - JSON 파싱 및 결과 렌더링을 담당합니다.
"""
import streamlit as st
import json
from typing import Optional
from src.components.base import BaseComponent


class ResultsDisplayComponent(BaseComponent):
    """분석 결과를 표시하는 컴포넌트입니다."""
    
    def render(self, result_container, output_text: Optional[str], raw_response) -> None:
        """
        분석 결과를 표시합니다.
        
        Args:
            result_container: Streamlit 컨테이너 객체
            output_text: 분석 결과 텍스트
            raw_response: 원시 응답 데이터
        """
        # 확장 가능한 결과 섹션 생성
        with result_container.expander("📝 분석 결과", expanded=True):
            if output_text:
                self._display_parsed_output(output_text)
            else:
                st.info("모델에서 직접적인 텍스트 응답을 찾지 못했습니다.")
            
            # 원시 응답 표시
            self._display_raw_response(raw_response)
    
    def _display_parsed_output(self, output_text: str) -> None:
        """분석된 출력 텍스트를 표시합니다."""
        try:
            # JSON 파싱 시도
            parsed_output = json.loads(output_text)
            object_name = parsed_output.get("object", "알 수 없음")
            category = parsed_output.get("category", "알 수 없음")
            st.write(f"**물체:** {object_name}")
            st.write(f"**카테고리:** {category}")
            
        except json.JSONDecodeError:
            st.warning("⚠️ JSON 형식이 아닌 응답입니다.")
            st.write(output_text)
            
        except Exception as e:
            st.error(f"응답 처리 중 오류 발생: {e}")
            st.write(output_text)
    
    def _display_raw_response(self, raw_response) -> None:
        """원시 응답을 표시합니다."""
        with st.expander("🔍 원시 응답(JSON) 보기"):
            try:
                st.json(raw_response)
            except Exception:
                st.code(str(raw_response))