"""
프롬프트 템플릿 렌더링 및 변수 처리를 담당하는 모듈입니다.

프롬프트 템플릿의 변수 치환, 렌더링, 변수 추출 및 검증을 담당합니다.
"""
import re
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.app.core.prompt_types import PromptTemplate, PromptConfig


class PromptRenderer:
    """
    프롬프트 템플릿 렌더링을 담당하는 클래스입니다.
    """

    def __init__(self, config: PromptConfig, logger=None):
        """
        프롬프트 렌더러를 초기화합니다.

        Args:
            config: 프롬프트 설정
            logger: 로거 인스턴스
        """
        self.config = config
        self.logger = logger

    def render_prompt(self, template: PromptTemplate, variables: Dict[str, Any] = None) -> Optional[str]:
        """
        프롬프트를 변수로 렌더링합니다.

        Args:
            template: 프롬프트 템플릿
            variables: 템플릿 변수들

        Returns:
            렌더링된 프롬프트 문자열 또는 None
        """
        if not template:
            return None

        rendered = template.template

        if variables:
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                rendered = rendered.replace(placeholder, str(var_value))

        return rendered

    def render_with_context(self, template: PromptTemplate, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        컨텍스트 정보와 함께 프롬프트를 렌더링합니다.

        Args:
            template: 프롬프트 템플릿
            context: 렌더링 컨텍스트

        Returns:
            렌더링 결과 및 메타데이터
        """
        if not template:
            return {
                'success': False,
                'error': '템플릿이 없습니다.',
                'rendered_text': None,
                'used_variables': [],
                'missing_variables': [],
                'context_info': {}
            }

        context = context or {}
        variables = context.get('variables', {})

        # 렌더링 실행
        rendered_text = self.render_prompt(template, variables)

        # 사용된 변수와 누락된 변수 확인
        template_variables = self.extract_variables(template.template)
        used_variables = [var for var in template_variables if var in variables]
        missing_variables = [var for var in template_variables if var not in variables]

        # 컨텍스트 정보 구성
        context_info = {
            'template_id': template.id,
            'template_name': template.name,
            'category': template.category.value,
            'rendered_at': datetime.now().isoformat(),
            'variable_count': len(template_variables),
            'used_count': len(used_variables),
            'missing_count': len(missing_variables)
        }

        return {
            'success': missing_variables == [],  # 모든 변수가 제공되면 성공
            'rendered_text': rendered_text,
            'used_variables': used_variables,
            'missing_variables': missing_variables,
            'context_info': context_info,
            'error': f"누락된 변수: {', '.join(missing_variables)}" if missing_variables else None
        }

    def preview_render(self, template: PromptTemplate, sample_variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        프롬프트 렌더링 미리보기를 생성합니다.

        Args:
            template: 프롬프트 템플릿
            sample_variables: 샘플 변수들

        Returns:
            미리보기 결과
        """
        if not template:
            return {
                'success': False,
                'error': '템플릿이 없습니다.',
                'preview_text': None,
                'variable_info': []
            }

        template_variables = self.extract_variables(template.template)

        # 샘플 변수가 제공되지 않으면 기본값 생성
        if not sample_variables:
            sample_variables = self._generate_sample_variables(template_variables)

        # 렌더링 실행
        rendered_text = self.render_prompt(template, sample_variables)

        # 변수 정보 구성
        variable_info = []
        for var in template_variables:
            var_info = {
                'name': var,
                'sample_value': sample_variables.get(var, f'<{var}>'),
                'is_provided': var in sample_variables,
                'type': type(sample_variables.get(var, '')).__name__ if var in sample_variables else 'string'
            }
            variable_info.append(var_info)

        return {
            'success': True,
            'preview_text': rendered_text,
            'variable_info': variable_info,
            'template_info': {
                'id': template.id,
                'name': template.name,
                'variable_count': len(template_variables),
                'character_count': len(template.template),
                'estimated_output_length': len(rendered_text) if rendered_text else 0
            }
        }

    def extract_variables(self, template_text: str) -> List[str]:
        """
        템플릿에서 변수들을 추출합니다.

        Args:
            template_text: 템플릿 문자열

        Returns:
            변수 이름 목록
        """
        # {variable_name} 패턴으로 변수 추출
        pattern = r'\{([^}]+)\}'
        variables = re.findall(pattern, template_text)
        return list(set(variables))  # 중복 제거

    def validate_variables(self, template_text: str, provided_variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        템플릿 변수의 유효성을 검증합니다.

        Args:
            template_text: 템플릿 문자열
            provided_variables: 제공된 변수들

        Returns:
            검증 결과
        """
        provided_variables = provided_variables or {}
        template_variables = self.extract_variables(template_text)

        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'variable_analysis': {
                'total_variables': len(template_variables),
                'provided_variables': len(provided_variables),
                'missing_variables': [],
                'unused_variables': [],
                'invalid_variable_names': []
            }
        }

        # 누락된 변수 확인
        missing_vars = [var for var in template_variables if var not in provided_variables]
        if missing_vars:
            result['variable_analysis']['missing_variables'] = missing_vars
            result['errors'].append(f"누락된 변수: {', '.join(missing_vars)}")
            result['is_valid'] = False

        # 사용되지 않는 변수 확인
        unused_vars = [var for var in provided_variables.keys() if var not in template_variables]
        if unused_vars:
            result['variable_analysis']['unused_variables'] = unused_vars
            result['warnings'].append(f"사용되지 않는 변수: {', '.join(unused_vars)}")

        # 변수명 유효성 검증
        invalid_vars = [var for var in template_variables if not self._is_valid_variable_name(var)]
        if invalid_vars:
            result['variable_analysis']['invalid_variable_names'] = invalid_vars
            result['warnings'].append(f"유효하지 않은 변수명: {', '.join(invalid_vars)}")

        return result

    def analyze_template_complexity(self, template_text: str) -> Dict[str, Any]:
        """
        템플릿의 복잡도를 분석합니다.

        Args:
            template_text: 템플릿 문자열

        Returns:
            복잡도 분석 결과
        """
        variables = self.extract_variables(template_text)

        analysis = {
            'basic_metrics': {
                'character_count': len(template_text),
                'word_count': len(template_text.split()),
                'line_count': template_text.count('\n') + 1,
                'variable_count': len(variables),
                'unique_variable_count': len(set(variables))
            },
            'complexity_score': 0,
            'complexity_level': 'simple',
            'recommendations': []
        }

        # 복잡도 점수 계산
        score = 0

        # 길이 기반 점수
        if len(template_text) > 1000:
            score += 3
        elif len(template_text) > 500:
            score += 2
        elif len(template_text) > 200:
            score += 1

        # 변수 수 기반 점수
        if len(variables) > 10:
            score += 3
        elif len(variables) > 5:
            score += 2
        elif len(variables) > 2:
            score += 1

        # 줄 수 기반 점수
        line_count = analysis['basic_metrics']['line_count']
        if line_count > 20:
            score += 2
        elif line_count > 10:
            score += 1

        analysis['complexity_score'] = score

        # 복잡도 레벨 결정
        if score >= 6:
            analysis['complexity_level'] = 'complex'
            analysis['recommendations'].append("템플릿을 여러 개의 작은 템플릿으로 나누는 것을 고려하세요.")
        elif score >= 3:
            analysis['complexity_level'] = 'moderate'
            analysis['recommendations'].append("템플릿 구조를 명확히 하고 주석을 추가하세요.")
        else:
            analysis['complexity_level'] = 'simple'

        # 추가 권장사항
        if len(variables) > 5:
            analysis['recommendations'].append("변수가 많습니다. 변수 그룹화나 기본값 설정을 고려하세요.")

        if len(template_text) > 500:
            analysis['recommendations'].append("템플릿이 깁니다. 가독성을 위해 구조화하세요.")

        return analysis

    def format_template_with_placeholder_preview(self, template_text: str) -> str:
        """
        템플릿을 플레이스홀더 미리보기와 함께 포맷팅합니다.

        Args:
            template_text: 템플릿 문자열

        Returns:
            포맷팅된 템플릿 문자열
        """
        variables = self.extract_variables(template_text)
        formatted = template_text

        for var in variables:
            placeholder = f"{{{var}}}"
            preview_placeholder = f"[{var.upper()}]"
            # 실제 치환이 아닌 시각적 표시만
            formatted = formatted.replace(placeholder, f"{placeholder} → {preview_placeholder}")

        return formatted

    def _generate_sample_variables(self, variable_names: List[str]) -> Dict[str, Any]:
        """
        변수명에 기반하여 샘플 변수를 생성합니다.

        Args:
            variable_names: 변수명 목록

        Returns:
            샘플 변수 딕셔너리
        """
        sample_values = {}

        for var_name in variable_names:
            var_lower = var_name.lower()

            # 변수명에 따른 적절한 샘플 값 생성
            if 'name' in var_lower:
                sample_values[var_name] = "사용자"
            elif 'date' in var_lower or 'time' in var_lower:
                sample_values[var_name] = "2024-01-01"
            elif 'email' in var_lower:
                sample_values[var_name] = "user@example.com"
            elif 'url' in var_lower or 'link' in var_lower:
                sample_values[var_name] = "https://example.com"
            elif 'number' in var_lower or 'count' in var_lower:
                sample_values[var_name] = "42"
            elif 'image' in var_lower or 'img' in var_lower:
                sample_values[var_name] = "이미지 설명"
            elif 'object' in var_lower or 'item' in var_lower:
                sample_values[var_name] = "객체명"
            elif 'size' in var_lower or 'dimension' in var_lower:
                sample_values[var_name] = "15cm x 10cm"
            elif 'description' in var_lower or 'desc' in var_lower:
                sample_values[var_name] = "상세 설명"
            else:
                sample_values[var_name] = f"[{var_name} 값]"

        return sample_values

    def _is_valid_variable_name(self, var_name: str) -> bool:
        """
        변수명이 유효한지 확인합니다.

        Args:
            var_name: 변수명

        Returns:
            유효성 여부
        """
        # Python 식별자 규칙 + 추가 허용 문자
        if not var_name:
            return False

        # 첫 글자는 문자 또는 언더스코어
        if not (var_name[0].isalpha() or var_name[0] == '_'):
            return False

        # 나머지는 문자, 숫자, 언더스코어
        for char in var_name[1:]:
            if not (char.isalnum() or char == '_'):
                return False

        return True


__all__ = [
    'PromptRenderer',
]