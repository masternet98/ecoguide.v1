"""
프롬프트 검증 및 품질 관리를 담당하는 모듈입니다.

프롬프트 템플릿의 유효성 검증, 품질 분석, 개선사항 제안을 담당합니다.
"""
import re
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.app.core.prompt_types import PromptTemplate, PromptCategory, PromptConfig


class PromptValidator:
    """
    프롬프트 검증 및 품질 관리를 담당하는 클래스입니다.
    """

    def __init__(self, config: PromptConfig, logger=None):
        """
        프롬프트 검증기를 초기화합니다.

        Args:
            config: 프롬프트 설정
            logger: 로거 인스턴스
        """
        self.config = config
        self.logger = logger

    def validate_prompt_template(self, template: str) -> Dict[str, Any]:
        """
        프롬프트 템플릿의 유효성을 검증합니다.

        Args:
            template: 검증할 템플릿 문자열

        Returns:
            검증 결과 딕셔너리
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'variables': [],
            'statistics': {}
        }

        if not template or not template.strip():
            result['is_valid'] = False
            result['errors'].append("템플릿이 비어있습니다.")
            return result

        # 변수 추출 및 검증
        variables = self._extract_variables(template)
        result['variables'] = variables

        # 변수 유효성 검증
        for var in variables:
            if not var.isidentifier():
                result['warnings'].append(f"변수명 '{var}'은 Python 식별자 규칙에 맞지 않습니다.")

        # 템플릿 통계
        result['statistics'] = {
            'character_count': len(template),
            'word_count': len(template.split()),
            'variable_count': len(variables),
            'line_count': template.count('\n') + 1
        }

        # 길이 검증
        if len(template) > 10000:
            result['warnings'].append("템플릿이 너무 깁니다. (10,000자 초과)")

        if len(template) < 10:
            result['warnings'].append("템플릿이 너무 짧습니다.")

        # 기본적인 구조 검증
        if '{' in template and '}' not in template:
            result['errors'].append("닫히지 않은 중괄호가 있습니다.")
            result['is_valid'] = False

        if '}' in template and '{' not in template:
            result['errors'].append("열리지 않은 중괄호가 있습니다.")
            result['is_valid'] = False

        return result

    def validate_prompt_structure(self, template: PromptTemplate) -> Dict[str, Any]:
        """
        프롬프트 전체 구조의 유효성을 검증합니다.

        Args:
            template: 프롬프트 템플릿

        Returns:
            구조 검증 결과
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'structure_analysis': {}
        }

        if not template:
            result['is_valid'] = False
            result['errors'].append("템플릿 객체가 없습니다.")
            return result

        # 필수 필드 검증
        if not template.name or not template.name.strip():
            result['errors'].append("프롬프트 이름이 없습니다.")
            result['is_valid'] = False

        if not template.description or not template.description.strip():
            result['warnings'].append("프롬프트 설명이 없습니다.")

        if not template.template or not template.template.strip():
            result['errors'].append("프롬프트 템플릿 내용이 없습니다.")
            result['is_valid'] = False

        # 이름 유효성 검증
        if template.name and len(template.name) > 100:
            result['warnings'].append("프롬프트 이름이 너무 깁니다. (100자 이하 권장)")

        if template.name and len(template.name) < 3:
            result['warnings'].append("프롬프트 이름이 너무 짧습니다. (3자 이상 권장)")

        # 설명 유효성 검증
        if template.description and len(template.description) > 500:
            result['warnings'].append("프롬프트 설명이 너무 깁니다. (500자 이하 권장)")

        # 태그 검증
        if template.tags:
            for tag in template.tags:
                if not isinstance(tag, str) or not tag.strip():
                    result['warnings'].append(f"유효하지 않은 태그: '{tag}'")
                elif len(tag) > 50:
                    result['warnings'].append(f"태그가 너무 깁니다: '{tag}' (50자 이하 권장)")

        # 메타데이터 검증
        if template.metadata:
            if not isinstance(template.metadata, dict):
                result['errors'].append("메타데이터는 딕셔너리 형태여야 합니다.")
                result['is_valid'] = False

        # 구조 분석
        result['structure_analysis'] = {
            'has_name': bool(template.name and template.name.strip()),
            'has_description': bool(template.description and template.description.strip()),
            'has_tags': bool(template.tags),
            'has_metadata': bool(template.metadata),
            'tag_count': len(template.tags) if template.tags else 0,
            'metadata_keys': list(template.metadata.keys()) if template.metadata else []
        }

        return result

    def validate_prompt_content(self, template: str, category: Optional[PromptCategory] = None) -> Dict[str, Any]:
        """
        프롬프트 내용의 유효성을 검증합니다.

        Args:
            template: 템플릿 문자열
            category: 프롬프트 카테고리

        Returns:
            내용 검증 결과
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'content_analysis': {}
        }

        if not template:
            result['is_valid'] = False
            result['errors'].append("템플릿 내용이 없습니다.")
            return result

        # 기본 내용 분석
        content_analysis = {
            'has_instructions': self._contains_instructions(template),
            'has_context': self._contains_context_markers(template),
            'has_examples': self._contains_examples(template),
            'has_constraints': self._contains_constraints(template),
            'tone_indicators': self._extract_tone_indicators(template),
            'formatting_elements': self._extract_formatting_elements(template)
        }

        result['content_analysis'] = content_analysis

        # 카테고리별 특화 검증
        if category:
            category_validation = self._validate_by_category(template, category)
            result['warnings'].extend(category_validation.get('warnings', []))
            result['errors'].extend(category_validation.get('errors', []))

        # 품질 점검
        quality_issues = self._check_content_quality(template)
        result['warnings'].extend(quality_issues)

        return result

    def check_template_syntax(self, template: str) -> Dict[str, Any]:
        """
        템플릿 문법을 검증합니다.

        Args:
            template: 템플릿 문자열

        Returns:
            문법 검증 결과
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'syntax_analysis': {}
        }

        if not template:
            result['is_valid'] = False
            result['errors'].append("템플릿이 없습니다.")
            return result

        # 중괄호 균형 검사
        brace_check = self._check_brace_balance(template)
        if not brace_check['is_balanced']:
            result['is_valid'] = False
            result['errors'].extend(brace_check['errors'])

        # 변수 문법 검사
        variable_check = self._check_variable_syntax(template)
        result['warnings'].extend(variable_check['warnings'])
        if variable_check['errors']:
            result['is_valid'] = False
            result['errors'].extend(variable_check['errors'])

        # 특수 문자 검사
        special_char_check = self._check_special_characters(template)
        result['warnings'].extend(special_char_check['warnings'])

        result['syntax_analysis'] = {
            'brace_pairs': brace_check['brace_count'],
            'variable_count': len(self._extract_variables(template)),
            'special_characters': special_char_check['found_characters'],
            'encoding_issues': self._check_encoding_issues(template)
        }

        return result

    def analyze_template_quality(self, template: PromptTemplate) -> Dict[str, Any]:
        """
        템플릿의 품질을 분석합니다.

        Args:
            template: 프롬프트 템플릿

        Returns:
            품질 분석 결과
        """
        if not template:
            return {
                'overall_score': 0,
                'quality_level': 'poor',
                'dimensions': {},
                'recommendations': ['템플릿이 없습니다.']
            }

        # 품질 차원별 분석
        dimensions = {
            'clarity': self._analyze_clarity(template.template),
            'completeness': self._analyze_completeness(template),
            'consistency': self._analyze_consistency(template),
            'usability': self._analyze_usability(template),
            'maintainability': self._analyze_maintainability(template)
        }

        # 전체 점수 계산 (각 차원의 평균)
        dimension_scores = [dim['score'] for dim in dimensions.values()]
        overall_score = sum(dimension_scores) / len(dimension_scores)

        # 품질 레벨 결정
        if overall_score >= 80:
            quality_level = 'excellent'
        elif overall_score >= 60:
            quality_level = 'good'
        elif overall_score >= 40:
            quality_level = 'fair'
        else:
            quality_level = 'poor'

        # 개선 권장사항 수집
        recommendations = []
        for dim_name, dim_result in dimensions.items():
            recommendations.extend(dim_result.get('recommendations', []))

        return {
            'overall_score': round(overall_score, 1),
            'quality_level': quality_level,
            'dimensions': dimensions,
            'recommendations': recommendations,
            'analysis_date': datetime.now().isoformat()
        }

    def suggest_improvements(self, template: PromptTemplate) -> Dict[str, Any]:
        """
        템플릿 개선사항을 제안합니다.

        Args:
            template: 프롬프트 템플릿

        Returns:
            개선사항 제안
        """
        if not template:
            return {
                'suggestions': [],
                'priority_levels': {},
                'estimated_impact': 'none'
            }

        suggestions = []
        priority_levels = {'high': [], 'medium': [], 'low': []}

        # 구조적 개선사항
        structure_suggestions = self._suggest_structure_improvements(template)
        suggestions.extend(structure_suggestions)

        # 내용적 개선사항
        content_suggestions = self._suggest_content_improvements(template.template)
        suggestions.extend(content_suggestions)

        # 사용성 개선사항
        usability_suggestions = self._suggest_usability_improvements(template)
        suggestions.extend(usability_suggestions)

        # 우선순위별 분류
        for suggestion in suggestions:
            priority = suggestion.get('priority', 'medium')
            if priority in priority_levels:
                priority_levels[priority].append(suggestion)

        # 예상 영향도 계산
        high_count = len(priority_levels['high'])
        medium_count = len(priority_levels['medium'])

        if high_count >= 3:
            estimated_impact = 'high'
        elif high_count >= 1 or medium_count >= 3:
            estimated_impact = 'medium'
        elif medium_count >= 1 or len(priority_levels['low']) >= 3:
            estimated_impact = 'low'
        else:
            estimated_impact = 'minimal'

        return {
            'suggestions': suggestions,
            'priority_levels': priority_levels,
            'estimated_impact': estimated_impact,
            'total_suggestions': len(suggestions),
            'suggestion_date': datetime.now().isoformat()
        }

    def _extract_variables(self, template: str) -> List[str]:
        """템플릿에서 변수들을 추출합니다."""
        pattern = r'\{([^}]+)\}'
        variables = re.findall(pattern, template)
        return list(set(variables))

    def _contains_instructions(self, template: str) -> bool:
        """템플릿에 지시사항이 포함되어 있는지 확인합니다."""
        instruction_patterns = [
            r'\b(분석|설명|찾|확인|검토|평가|판단|추천|제안)\w*',
            r'\b(analyze|describe|find|check|review|evaluate|recommend)\w*',
            r'(해주세요|하세요|바랍니다|하시오)',
            r'(please|kindly|help|assist)'
        ]

        for pattern in instruction_patterns:
            if re.search(pattern, template, re.IGNORECASE | re.UNICODE):
                return True
        return False

    def _contains_context_markers(self, template: str) -> bool:
        """템플릿에 컨텍스트 마커가 있는지 확인합니다."""
        context_patterns = [
            r'(컨텍스트|상황|배경|환경)',
            r'(context|situation|background|environment)',
            r'(이미지|사진|그림)',
            r'(image|photo|picture)'
        ]

        for pattern in context_patterns:
            if re.search(pattern, template, re.IGNORECASE | re.UNICODE):
                return True
        return False

    def _contains_examples(self, template: str) -> bool:
        """템플릿에 예시가 포함되어 있는지 확인합니다."""
        example_patterns = [
            r'(예시|예제|예:|예를 들어)',
            r'(example|instance|for example|such as)',
            r'(다음과 같이|아래와 같이)',
            r'(as follows|like this)'
        ]

        for pattern in example_patterns:
            if re.search(pattern, template, re.IGNORECASE | re.UNICODE):
                return True
        return False

    def _contains_constraints(self, template: str) -> bool:
        """템플릿에 제약사항이 포함되어 있는지 확인합니다."""
        constraint_patterns = [
            r'(제약|제한|조건|규칙)',
            r'(constraint|limitation|condition|rule)',
            r'(금지|허용하지|불가)',
            r'(forbidden|not allowed|prohibited)'
        ]

        for pattern in constraint_patterns:
            if re.search(pattern, template, re.IGNORECASE | re.UNICODE):
                return True
        return False

    def _extract_tone_indicators(self, template: str) -> List[str]:
        """템플릿에서 톤 지시자를 추출합니다."""
        tone_patterns = {
            'formal': r'(공식적|정중하게|존댓말)',
            'casual': r'(친근하게|편하게|반말)',
            'professional': r'(전문적|비즈니스)',
            'friendly': r'(친절하게|따뜻하게)',
            'concise': r'(간결하게|짧게|요약)',
            'detailed': r'(자세하게|상세하게|구체적)'
        }

        found_tones = []
        for tone, pattern in tone_patterns.items():
            if re.search(pattern, template, re.IGNORECASE | re.UNICODE):
                found_tones.append(tone)

        return found_tones

    def _extract_formatting_elements(self, template: str) -> List[str]:
        """템플릿에서 포맷팅 요소를 추출합니다."""
        formatting_elements = []

        if re.search(r'\*\*.*?\*\*|\*.*?\*', template):
            formatting_elements.append('markdown_emphasis')

        if re.search(r'```.*?```|`.*?`', template, re.DOTALL):
            formatting_elements.append('code_blocks')

        if re.search(r'^\s*[-*+]\s', template, re.MULTILINE):
            formatting_elements.append('bullet_lists')

        if re.search(r'^\s*\d+\.\s', template, re.MULTILINE):
            formatting_elements.append('numbered_lists')

        if re.search(r'#+\s', template):
            formatting_elements.append('headers')

        return formatting_elements

    def _validate_by_category(self, template: str, category: PromptCategory) -> Dict[str, List[str]]:
        """카테고리별 특화 검증을 수행합니다."""
        warnings = []
        errors = []

        if category == PromptCategory.VISION_ANALYSIS:
            if not re.search(r'(이미지|사진|그림|시각)', template, re.IGNORECASE):
                warnings.append("비전 분석 프롬프트에 이미지 관련 언급이 없습니다.")

        elif category == PromptCategory.SIZE_ESTIMATION:
            if not re.search(r'(크기|사이즈|크기|치수|길이)', template, re.IGNORECASE):
                warnings.append("크기 추정 프롬프트에 크기 관련 언급이 없습니다.")

        elif category == PromptCategory.WASTE_CLASSIFICATION:
            if not re.search(r'(폐기물|쓰레기|분류|재활용)', template, re.IGNORECASE):
                warnings.append("폐기물 분류 프롬프트에 폐기물 관련 언급이 없습니다.")

        return {'warnings': warnings, 'errors': errors}

    def _check_content_quality(self, template: str) -> List[str]:
        """내용 품질을 점검합니다."""
        warnings = []

        # 너무 모호한 지시사항
        if re.search(r'\b(뭔가|어떤|그런|이런)\b', template):
            warnings.append("모호한 표현이 포함되어 있습니다. 더 구체적으로 작성하세요.")

        # 부정적 표현 과다
        negative_count = len(re.findall(r'\b(안|못|없|말|금지|제외)\w*', template))
        if negative_count > 3:
            warnings.append("부정적 표현이 많습니다. 긍정적 표현으로 바꿔보세요.")

        # 문장이 너무 김
        sentences = re.split(r'[.!?]', template)
        long_sentences = [s for s in sentences if len(s.strip()) > 100]
        if len(long_sentences) > 2:
            warnings.append("너무 긴 문장이 있습니다. 문장을 나누는 것을 고려하세요.")

        return warnings

    def _check_brace_balance(self, template: str) -> Dict[str, Any]:
        """중괄호 균형을 검사합니다."""
        open_braces = template.count('{')
        close_braces = template.count('}')

        result = {
            'is_balanced': open_braces == close_braces,
            'brace_count': {'open': open_braces, 'close': close_braces},
            'errors': []
        }

        if open_braces != close_braces:
            if open_braces > close_braces:
                result['errors'].append(f"닫히지 않은 중괄호 {open_braces - close_braces}개")
            else:
                result['errors'].append(f"열리지 않은 중괄호 {close_braces - open_braces}개")

        return result

    def _check_variable_syntax(self, template: str) -> Dict[str, List[str]]:
        """변수 문법을 검사합니다."""
        warnings = []
        errors = []

        # 빈 변수 확인
        if re.search(r'\{\s*\}', template):
            errors.append("빈 변수가 있습니다: {}")

        # 중첩된 중괄호 확인
        if re.search(r'\{[^}]*\{', template) or re.search(r'\}[^{]*\}', template):
            warnings.append("중첩된 중괄호가 있을 수 있습니다.")

        # 변수명에 공백 확인
        variables_with_spaces = re.findall(r'\{([^}]*\s+[^}]*)\}', template)
        if variables_with_spaces:
            warnings.append(f"공백이 포함된 변수명: {variables_with_spaces}")

        return {'warnings': warnings, 'errors': errors}

    def _check_special_characters(self, template: str) -> Dict[str, Any]:
        """특수 문자를 검사합니다."""
        warnings = []
        special_chars = []

        # 검사할 특수 문자들
        problematic_chars = ['<', '>', '&', '"', "'", '\\', '\r', '\t']

        for char in problematic_chars:
            if char in template:
                special_chars.append(char)
                if char in ['<', '>']:
                    warnings.append(f"HTML 태그로 해석될 수 있는 문자 '{char}'가 있습니다.")
                elif char == '&':
                    warnings.append("HTML 엔티티로 해석될 수 있는 '&' 문자가 있습니다.")

        return {'warnings': warnings, 'found_characters': special_chars}

    def _check_encoding_issues(self, template: str) -> List[str]:
        """인코딩 문제를 검사합니다."""
        issues = []

        try:
            template.encode('utf-8')
        except UnicodeEncodeError:
            issues.append("UTF-8 인코딩에 문제가 있습니다.")

        # BOM 확인
        if template.startswith('\ufeff'):
            issues.append("BOM(Byte Order Mark)이 포함되어 있습니다.")

        return issues

    def _analyze_clarity(self, template: str) -> Dict[str, Any]:
        """명확성을 분석합니다."""
        score = 100
        issues = []

        # 모호한 표현 확인
        ambiguous_words = ['뭔가', '어떤', '그런', '이런', '좀', '약간']
        ambiguous_count = sum(template.lower().count(word) for word in ambiguous_words)
        if ambiguous_count > 0:
            score -= min(ambiguous_count * 10, 30)
            issues.append(f"모호한 표현 {ambiguous_count}개 발견")

        # 문장 길이 확인
        sentences = re.split(r'[.!?]', template)
        long_sentences = [s for s in sentences if len(s.strip()) > 80]
        if long_sentences:
            score -= len(long_sentences) * 5
            issues.append(f"긴 문장 {len(long_sentences)}개")

        return {
            'score': max(score, 0),
            'issues': issues,
            'recommendations': ["모호한 표현을 구체적으로 바꾸세요"] if ambiguous_count > 0 else []
        }

    def _analyze_completeness(self, template: PromptTemplate) -> Dict[str, Any]:
        """완성도를 분석합니다."""
        score = 100
        issues = []
        recommendations = []

        # 필수 요소 확인
        if not template.description or len(template.description.strip()) < 10:
            score -= 20
            issues.append("설명이 부족합니다")
            recommendations.append("의미있는 설명을 추가하세요")

        if not template.tags:
            score -= 10
            issues.append("태그가 없습니다")
            recommendations.append("관련 태그를 추가하세요")

        # 템플릿 내용 완성도
        content_analysis = {
            'has_instructions': self._contains_instructions(template.template),
            'has_context': self._contains_context_markers(template.template),
            'has_examples': self._contains_examples(template.template)
        }

        missing_elements = [k for k, v in content_analysis.items() if not v]
        score -= len(missing_elements) * 15

        if missing_elements:
            issues.append(f"누락된 요소: {missing_elements}")
            recommendations.append("지시사항, 컨텍스트, 예시를 보완하세요")

        return {
            'score': max(score, 0),
            'issues': issues,
            'recommendations': recommendations
        }

    def _analyze_consistency(self, template: PromptTemplate) -> Dict[str, Any]:
        """일관성을 분석합니다."""
        score = 100
        issues = []
        recommendations = []

        # 명명 규칙 일관성 (변수명)
        variables = self._extract_variables(template.template)
        naming_styles = []

        for var in variables:
            if '_' in var:
                naming_styles.append('snake_case')
            elif any(c.isupper() for c in var[1:]):
                naming_styles.append('camelCase')
            else:
                naming_styles.append('lowercase')

        if len(set(naming_styles)) > 1:
            score -= 15
            issues.append("변수 명명 규칙이 일관되지 않습니다")
            recommendations.append("변수 명명 규칙을 통일하세요")

        return {
            'score': max(score, 0),
            'issues': issues,
            'recommendations': recommendations
        }

    def _analyze_usability(self, template: PromptTemplate) -> Dict[str, Any]:
        """사용성을 분석합니다."""
        score = 100
        issues = []
        recommendations = []

        # 변수 복잡도
        variables = self._extract_variables(template.template)
        if len(variables) > 10:
            score -= 20
            issues.append(f"변수가 너무 많습니다 ({len(variables)}개)")
            recommendations.append("변수 수를 줄이거나 그룹화하세요")

        # 템플릿 길이
        if len(template.template) > 1000:
            score -= 15
            issues.append("템플릿이 너무 깁니다")
            recommendations.append("템플릿을 여러 개로 나누는 것을 고려하세요")

        return {
            'score': max(score, 0),
            'issues': issues,
            'recommendations': recommendations
        }

    def _analyze_maintainability(self, template: PromptTemplate) -> Dict[str, Any]:
        """유지보수성을 분석합니다."""
        score = 100
        issues = []
        recommendations = []

        # 버전 관리
        if not template.version or template.version == '1.0':
            score -= 10
            issues.append("버전 정보가 기본값입니다")
            recommendations.append("의미있는 버전 번호를 사용하세요")

        # 메타데이터 활용
        if not template.metadata:
            score -= 15
            issues.append("메타데이터가 없습니다")
            recommendations.append("유지보수에 도움이 되는 메타데이터를 추가하세요")

        return {
            'score': max(score, 0),
            'issues': issues,
            'recommendations': recommendations
        }

    def _suggest_structure_improvements(self, template: PromptTemplate) -> List[Dict[str, Any]]:
        """구조적 개선사항을 제안합니다."""
        suggestions = []

        if not template.description or len(template.description) < 20:
            suggestions.append({
                'type': 'structure',
                'title': '설명 보완',
                'description': '프롬프트의 목적과 사용법을 명확히 설명하세요',
                'priority': 'high',
                'effort': 'low'
            })

        if not template.tags:
            suggestions.append({
                'type': 'structure',
                'title': '태그 추가',
                'description': '검색과 분류를 위한 관련 태그를 추가하세요',
                'priority': 'medium',
                'effort': 'low'
            })

        return suggestions

    def _suggest_content_improvements(self, template: str) -> List[Dict[str, Any]]:
        """내용적 개선사항을 제안합니다."""
        suggestions = []

        if not self._contains_examples(template):
            suggestions.append({
                'type': 'content',
                'title': '예시 추가',
                'description': '사용자 이해를 돕기 위한 예시를 추가하세요',
                'priority': 'medium',
                'effort': 'medium'
            })

        if len(template) > 800:
            suggestions.append({
                'type': 'content',
                'title': '길이 단축',
                'description': '템플릿이 너무 깁니다. 핵심 내용으로 압축하세요',
                'priority': 'medium',
                'effort': 'high'
            })

        return suggestions

    def _suggest_usability_improvements(self, template: PromptTemplate) -> List[Dict[str, Any]]:
        """사용성 개선사항을 제안합니다."""
        suggestions = []

        variables = self._extract_variables(template.template)
        if len(variables) > 8:
            suggestions.append({
                'type': 'usability',
                'title': '변수 수 최적화',
                'description': f'변수가 {len(variables)}개로 많습니다. 필수 변수만 남기고 나머지는 기본값을 설정하세요',
                'priority': 'high',
                'effort': 'medium'
            })

        return suggestions


__all__ = [
    'PromptValidator',
]