"""
설정 값 검증 및 유효성 확인 시스템.

애플리케이션 설정의 무결성을 보장하고 올바른 설정값을 제공합니다.
"""
from typing import Any, Dict, List, Optional, Union, Callable, Type, get_origin, get_args
from dataclasses import dataclass, fields
from abc import ABC, abstractmethod
from enum import Enum
import os
import re
import logging
from pathlib import Path

from src.core.config import Config
from src.core.error_handler import ValidationError, ConfigurationError

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """검증 오류의 심각도"""
    WARNING = "warning"   # 경고, 기본값 사용 가능
    ERROR = "error"       # 오류, 수정 필요
    CRITICAL = "critical" # 심각, 애플리케이션 실행 불가


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    severity: ValidationSeverity
    field_name: str
    message: str
    suggested_value: Optional[Any] = None
    current_value: Optional[Any] = None


class ValidationRule(ABC):
    """설정 값 검증 규칙의 추상 기반 클래스"""
    
    def __init__(self, field_name: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.field_name = field_name
        self.severity = severity
    
    @abstractmethod
    def validate(self, value: Any, config: Config) -> ValidationResult:
        """값을 검증하고 결과를 반환합니다."""
        pass


class RangeValidationRule(ValidationRule):
    """숫자 범위 검증 규칙"""
    
    def __init__(self, field_name: str, min_value: Union[int, float], max_value: Union[int, float], **kwargs):
        super().__init__(field_name, **kwargs)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any, config: Config) -> ValidationResult:
        if not isinstance(value, (int, float)):
            return ValidationResult(
                is_valid=False,
                severity=self.severity,
                field_name=self.field_name,
                message=f"{self.field_name}은 숫자여야 합니다.",
                current_value=value,
                suggested_value=self.min_value
            )
        
        if not (self.min_value <= value <= self.max_value):
            return ValidationResult(
                is_valid=False,
                severity=self.severity,
                field_name=self.field_name,
                message=f"{self.field_name}은 {self.min_value}과 {self.max_value} 사이의 값이어야 합니다.",
                current_value=value,
                suggested_value=max(self.min_value, min(value, self.max_value))
            )
        
        return ValidationResult(
            is_valid=True,
            severity=self.severity,
            field_name=self.field_name,
            message=f"{self.field_name} 검증 통과",
            current_value=value
        )


class PathValidationRule(ValidationRule):
    """파일/디렉터리 경로 검증 규칙"""
    
    def __init__(self, field_name: str, must_exist: bool = False, is_directory: bool = False, 
                 create_if_missing: bool = False, **kwargs):
        super().__init__(field_name, **kwargs)
        self.must_exist = must_exist
        self.is_directory = is_directory
        self.create_if_missing = create_if_missing
    
    def validate(self, value: Any, config: Config) -> ValidationResult:
        if not isinstance(value, (str, Path)):
            return ValidationResult(
                is_valid=False,
                severity=self.severity,
                field_name=self.field_name,
                message=f"{self.field_name}은 유효한 경로여야 합니다.",
                current_value=value
            )
        
        path = Path(value)
        
        # 존재 여부 확인
        if self.must_exist and not path.exists():
            if self.create_if_missing and self.is_directory:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created missing directory: {path}")
                except Exception as e:
                    return ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        field_name=self.field_name,
                        message=f"디렉터리를 생성할 수 없습니다: {e}",
                        current_value=value
                    )
            else:
                return ValidationResult(
                    is_valid=False,
                    severity=self.severity,
                    field_name=self.field_name,
                    message=f"경로가 존재하지 않습니다: {path}",
                    current_value=value
                )
        
        # 디렉터리 여부 확인
        if path.exists() and self.is_directory and not path.is_dir():
            return ValidationResult(
                is_valid=False,
                severity=self.severity,
                field_name=self.field_name,
                message=f"디렉터리여야 하지만 파일입니다: {path}",
                current_value=value
            )
        
        return ValidationResult(
            is_valid=True,
            severity=self.severity,
            field_name=self.field_name,
            message=f"{self.field_name} 경로 검증 통과",
            current_value=value
        )


class RegexValidationRule(ValidationRule):
    """정규표현식 검증 규칙"""
    
    def __init__(self, field_name: str, pattern: str, description: str = "", **kwargs):
        super().__init__(field_name, **kwargs)
        self.pattern = re.compile(pattern)
        self.description = description
    
    def validate(self, value: Any, config: Config) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                severity=self.severity,
                field_name=self.field_name,
                message=f"{self.field_name}은 문자열이어야 합니다.",
                current_value=value
            )
        
        if not self.pattern.match(value):
            message = f"{self.field_name}이 올바른 형식이 아닙니다."
            if self.description:
                message += f" {self.description}"
            
            return ValidationResult(
                is_valid=False,
                severity=self.severity,
                field_name=self.field_name,
                message=message,
                current_value=value
            )
        
        return ValidationResult(
            is_valid=True,
            severity=self.severity,
            field_name=self.field_name,
            message=f"{self.field_name} 형식 검증 통과",
            current_value=value
        )


class ChoiceValidationRule(ValidationRule):
    """선택지 검증 규칙"""
    
    def __init__(self, field_name: str, choices: List[Any], case_sensitive: bool = True, **kwargs):
        super().__init__(field_name, **kwargs)
        self.choices = choices
        self.case_sensitive = case_sensitive
    
    def validate(self, value: Any, config: Config) -> ValidationResult:
        comparison_value = value
        comparison_choices = self.choices
        
        if isinstance(value, str) and not self.case_sensitive:
            comparison_value = value.lower()
            comparison_choices = [choice.lower() if isinstance(choice, str) else choice 
                                for choice in self.choices]
        
        if comparison_value not in comparison_choices:
            return ValidationResult(
                is_valid=False,
                severity=self.severity,
                field_name=self.field_name,
                message=f"{self.field_name}은 다음 중 하나여야 합니다: {self.choices}",
                current_value=value,
                suggested_value=self.choices[0] if self.choices else None
            )
        
        return ValidationResult(
            is_valid=True,
            severity=self.severity,
            field_name=self.field_name,
            message=f"{self.field_name} 선택지 검증 통과",
            current_value=value
        )


class EnvironmentVariableRule(ValidationRule):
    """환경 변수 존재 여부 검증 규칙"""
    
    def __init__(self, field_name: str, env_var_name: str, required: bool = True, **kwargs):
        super().__init__(field_name, **kwargs)
        self.env_var_name = env_var_name
        self.required = required
    
    def validate(self, value: Any, config: Config) -> ValidationResult:
        env_value = os.environ.get(self.env_var_name)
        
        if self.required and not env_value:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                field_name=self.field_name,
                message=f"필수 환경 변수가 설정되지 않았습니다: {self.env_var_name}",
                current_value=None
            )
        
        if not self.required and not env_value:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.WARNING,
                field_name=self.field_name,
                message=f"선택적 환경 변수가 설정되지 않았습니다: {self.env_var_name}",
                current_value=None
            )
        
        return ValidationResult(
            is_valid=True,
            severity=self.severity,
            field_name=self.field_name,
            message=f"환경 변수 {self.env_var_name} 확인됨",
            current_value=env_value
        )


class CustomValidationRule(ValidationRule):
    """커스텀 검증 규칙"""
    
    def __init__(self, field_name: str, validator_func: Callable[[Any, Config], bool], 
                 error_message: str, **kwargs):
        super().__init__(field_name, **kwargs)
        self.validator_func = validator_func
        self.error_message = error_message
    
    def validate(self, value: Any, config: Config) -> ValidationResult:
        try:
            is_valid = self.validator_func(value, config)
            
            return ValidationResult(
                is_valid=is_valid,
                severity=self.severity,
                field_name=self.field_name,
                message=self.error_message if not is_valid else f"{self.field_name} 커스텀 검증 통과",
                current_value=value
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                field_name=self.field_name,
                message=f"검증 중 오류 발생: {e}",
                current_value=value
            )


class ConfigValidator:
    """설정 검증기 메인 클래스"""
    
    def __init__(self):
        self.rules: Dict[str, List[ValidationRule]] = {}
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """기본 검증 규칙들을 설정합니다."""
        
        # 포트 번호 검증
        self.add_rule(RangeValidationRule(
            'default_port', 1024, 65535, 
            severity=ValidationSeverity.ERROR
        ))
        
        # 이미지 크기 검증
        self.add_rule(RangeValidationRule(
            'max_image_size', 128, 4096,
            severity=ValidationSeverity.WARNING
        ))
        
        # JPEG 품질 검증
        self.add_rule(RangeValidationRule(
            'jpeg_quality', 1, 100,
            severity=ValidationSeverity.WARNING
        ))
        
        # Vision 모델 선택지 검증
        self.add_rule(ChoiceValidationRule(
            'default_model', 
            ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-3.5-turbo'],
            severity=ValidationSeverity.ERROR
        ))
        
        # 디렉터리 경로 검증 (행정구역 업로드 디렉터리)
        self.add_rule(PathValidationRule(
            'district.uploads_dir',
            must_exist=False,
            is_directory=True,
            create_if_missing=True,
            severity=ValidationSeverity.WARNING
        ))
        
        # OpenAI API 키 환경 변수 검증
        self.add_rule(EnvironmentVariableRule(
            'openai_api_key',
            'OPENAI_API_KEY',
            required=False,  # 선택적으로 설정
            severity=ValidationSeverity.WARNING
        ))
        
        # URL 형식 검증
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        self.add_rule(RegexValidationRule(
            'district.base_url',
            url_pattern,
            "올바른 URL 형식이어야 합니다 (http:// 또는 https://로 시작)",
            severity=ValidationSeverity.ERROR
        ))
        
        # 타임아웃 값 검증
        self.add_rule(RangeValidationRule(
            'district.request_timeout', 1, 300,
            severity=ValidationSeverity.WARNING
        ))
        
        self.add_rule(RangeValidationRule(
            'district.download_timeout', 1, 1800,
            severity=ValidationSeverity.WARNING
        ))
    
    def add_rule(self, rule: ValidationRule) -> None:
        """검증 규칙을 추가합니다."""
        if rule.field_name not in self.rules:
            self.rules[rule.field_name] = []
        self.rules[rule.field_name].append(rule)
        logger.debug(f"Validation rule added for {rule.field_name}")
    
    def validate_config(self, config: Config) -> List[ValidationResult]:
        """설정 전체를 검증하고 결과 목록을 반환합니다."""
        results = []
        
        for field_name, rules in self.rules.items():
            try:
                # 중첩된 필드 처리 (예: district.uploads_dir)
                value = self._get_nested_value(config, field_name)
                
                for rule in rules:
                    result = rule.validate(value, config)
                    results.append(result)
                    
            except AttributeError as e:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    field_name=field_name,
                    message=f"설정 필드를 찾을 수 없습니다: {field_name}",
                    current_value=None
                ))
                logger.warning(f"Config field not found: {field_name}")
            
            except Exception as e:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    field_name=field_name,
                    message=f"검증 중 오류 발생: {e}",
                    current_value=None
                ))
                logger.error(f"Validation error for {field_name}: {e}")
        
        return results
    
    def _get_nested_value(self, config: Config, field_name: str) -> Any:
        """중첩된 필드 값을 가져옵니다 (예: district.uploads_dir)."""
        parts = field_name.split('.')
        value = config
        
        for part in parts:
            value = getattr(value, part)
        
        return value
    
    def validate_and_fix(self, config: Config, auto_fix: bool = False) -> tuple[Config, List[ValidationResult]]:
        """
        설정을 검증하고 선택적으로 자동 수정합니다.
        
        Args:
            config: 검증할 설정 객체
            auto_fix: 자동 수정 여부
            
        Returns:
            tuple[Config, List[ValidationResult]]: (수정된 설정, 검증 결과 목록)
        """
        results = self.validate_config(config)
        
        if auto_fix:
            # 경고 수준의 오류만 자동 수정
            for result in results:
                if (not result.is_valid and 
                    result.severity == ValidationSeverity.WARNING and 
                    result.suggested_value is not None):
                    
                    try:
                        self._set_nested_value(config, result.field_name, result.suggested_value)
                        result.is_valid = True
                        result.message += " (자동 수정됨)"
                        logger.info(f"Auto-fixed config field {result.field_name}: {result.suggested_value}")
                    except Exception as e:
                        logger.error(f"Failed to auto-fix {result.field_name}: {e}")
        
        return config, results
    
    def _set_nested_value(self, config: Config, field_name: str, value: Any) -> None:
        """중첩된 필드 값을 설정합니다."""
        parts = field_name.split('.')
        obj = config
        
        # 마지막 부분을 제외하고 탐색
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        # 마지막 필드에 값 설정
        setattr(obj, parts[-1], value)
    
    def get_critical_errors(self, results: List[ValidationResult]) -> List[ValidationResult]:
        """심각한 오류만 필터링하여 반환합니다."""
        return [r for r in results if not r.is_valid and r.severity == ValidationSeverity.CRITICAL]
    
    def get_error_summary(self, results: List[ValidationResult]) -> Dict[str, int]:
        """오류 요약 통계를 반환합니다."""
        summary = {
            'total': len(results),
            'valid': len([r for r in results if r.is_valid]),
            'warnings': len([r for r in results if not r.is_valid and r.severity == ValidationSeverity.WARNING]),
            'errors': len([r for r in results if not r.is_valid and r.severity == ValidationSeverity.ERROR]),
            'critical': len([r for r in results if not r.is_valid and r.severity == ValidationSeverity.CRITICAL])
        }
        return summary


def validate_config(config: Config, auto_fix: bool = False) -> tuple[Config, List[ValidationResult]]:
    """설정을 검증하는 편의 함수"""
    validator = ConfigValidator()
    return validator.validate_and_fix(config, auto_fix)


def ensure_valid_config(config: Config) -> Config:
    """
    설정이 유효한지 확인하고, 심각한 오류가 있으면 예외를 발생시킵니다.
    
    Args:
        config: 검증할 설정 객체
        
    Returns:
        Config: 검증된 설정 객체
        
    Raises:
        ConfigurationError: 심각한 설정 오류가 있는 경우
    """
    validator = ConfigValidator()
    config, results = validator.validate_and_fix(config, auto_fix=True)
    
    critical_errors = validator.get_critical_errors(results)
    
    if critical_errors:
        error_messages = [f"{e.field_name}: {e.message}" for e in critical_errors]
        raise ConfigurationError(
            f"심각한 설정 오류가 발견되었습니다: {'; '.join(error_messages)}",
            suggestion="설정을 수정하고 다시 시도해주세요."
        )
    
    # 경고 및 오류 로깅
    for result in results:
        if not result.is_valid:
            if result.severity == ValidationSeverity.WARNING:
                logger.warning(f"Config warning - {result.field_name}: {result.message}")
            else:
                logger.error(f"Config error - {result.field_name}: {result.message}")
    
    return config