"""
통합된 예외 처리 시스템.

애플리케이션 전반에서 일관된 예외 처리와 사용자 친화적인 오류 메시지를 제공합니다.
"""
from typing import Optional, Dict, Any, Callable, Type, Union
from dataclasses import dataclass
from enum import Enum
import logging
import traceback
import functools
import sys
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """오류 심각도 레벨"""
    LOW = "low"           # 경고 수준, 기능 일부 제한
    MEDIUM = "medium"     # 기능 사용 불가, 대안 제시
    HIGH = "high"         # 중요 기능 실패, 사용자 개입 필요
    CRITICAL = "critical" # 애플리케이션 중단 위험


class ErrorCategory(Enum):
    """오류 카테고리"""
    CONFIGURATION = "configuration"   # 설정 오류
    DEPENDENCY = "dependency"         # 의존성 오류
    NETWORK = "network"              # 네트워크 오류
    FILE_SYSTEM = "file_system"      # 파일 시스템 오류
    AUTHENTICATION = "authentication" # 인증 오류
    VALIDATION = "validation"         # 데이터 검증 오류
    RUNTIME = "runtime"              # 런타임 오류
    EXTERNAL_API = "external_api"    # 외부 API 오류
    USER_INPUT = "user_input"        # 사용자 입력 오류
    UNKNOWN = "unknown"              # 알 수 없는 오류


@dataclass
class ErrorContext:
    """오류 컨텍스트 정보"""
    service_name: Optional[str] = None
    function_name: Optional[str] = None
    user_action: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    additional_info: Optional[Dict[str, Any]] = None


@dataclass
class ErrorInfo:
    """구조화된 오류 정보"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    title: str
    message: str
    details: Optional[str] = None
    suggestion: Optional[str] = None
    context: Optional[ErrorContext] = None
    original_exception: Optional[Exception] = None
    stack_trace: Optional[str] = None


class BaseError(Exception):
    """애플리케이션 기본 예외 클래스"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        suggestion: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.suggestion = suggestion
        self.context = context
        self.original_exception = original_exception


class ConfigurationError(BaseError):
    """설정 관련 오류"""
    
    def __init__(self, message: str, suggestion: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            suggestion=suggestion or "설정을 확인하고 올바른 값으로 수정해주세요.",
            **kwargs
        )


class DependencyError(BaseError):
    """의존성 관련 오류"""
    
    def __init__(self, message: str, suggestion: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DEPENDENCY,
            severity=ErrorSeverity.HIGH,
            suggestion=suggestion or "필요한 패키지를 설치하거나 기능을 비활성화해주세요.",
            **kwargs
        )


class NetworkError(BaseError):
    """네트워크 관련 오류"""
    
    def __init__(self, message: str, suggestion: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            suggestion=suggestion or "네트워크 연결을 확인하고 다시 시도해주세요.",
            **kwargs
        )


class ValidationError(BaseError):
    """데이터 검증 오류"""
    
    def __init__(self, message: str, suggestion: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            suggestion=suggestion or "입력 데이터를 확인하고 올바른 형식으로 다시 시도해주세요.",
            **kwargs
        )


class ErrorHandler:
    """통합 오류 처리기"""
    
    def __init__(self):
        self._error_mappings: Dict[Type[Exception], Callable[[Exception], ErrorInfo]] = {}
        self._context_providers: list[Callable[[], Dict[str, Any]]] = []
        self._setup_default_mappings()
    
    def _setup_default_mappings(self) -> None:
        """기본 예외 매핑을 설정합니다."""
        
        # 기본 애플리케이션 오류들
        self._error_mappings[BaseError] = self._handle_base_error
        self._error_mappings[ConfigurationError] = self._handle_base_error
        self._error_mappings[DependencyError] = self._handle_base_error
        self._error_mappings[NetworkError] = self._handle_base_error
        self._error_mappings[ValidationError] = self._handle_base_error
        
        # Python 내장 예외들
        self._error_mappings[ImportError] = self._handle_import_error
        self._error_mappings[FileNotFoundError] = self._handle_file_not_found_error
        self._error_mappings[PermissionError] = self._handle_permission_error
        self._error_mappings[ValueError] = self._handle_value_error
        self._error_mappings[KeyError] = self._handle_key_error
        self._error_mappings[ConnectionError] = self._handle_connection_error
        self._error_mappings[TimeoutError] = self._handle_timeout_error
    
    def handle_error(self, exception: Exception, context: Optional[ErrorContext] = None) -> ErrorInfo:
        """예외를 처리하고 ErrorInfo를 반환합니다."""
        
        # 컨텍스트 정보 수집
        if context is None:
            context = self._collect_context()
        
        # 예외 타입에 따른 처리
        exception_type = type(exception)
        handler = self._error_mappings.get(exception_type)
        
        if handler:
            error_info = handler(exception)
        else:
            # 기본 처리
            error_info = self._handle_unknown_error(exception)
        
        # 컨텍스트 정보 추가
        error_info.context = context
        error_info.original_exception = exception
        error_info.stack_trace = traceback.format_exc()
        
        # 로깅
        self._log_error(error_info)
        
        return error_info
    
    def _collect_context(self) -> ErrorContext:
        """현재 실행 컨텍스트 정보를 수집합니다."""
        context_data = {}
        
        # 등록된 컨텍스트 프로바이더들로부터 정보 수집
        for provider in self._context_providers:
            try:
                context_data.update(provider())
            except Exception as e:
                logger.warning(f"Context provider failed: {e}")
        
        return ErrorContext(additional_info=context_data)
    
    def _handle_base_error(self, exception: BaseError) -> ErrorInfo:
        """BaseError 처리"""
        return ErrorInfo(
            error_id=f"{exception.category.value}_{id(exception)}",
            category=exception.category,
            severity=exception.severity,
            title=f"{exception.category.value.title()} Error",
            message=str(exception),
            suggestion=exception.suggestion
        )
    
    def _handle_import_error(self, exception: ImportError) -> ErrorInfo:
        """ImportError 처리"""
        module_name = getattr(exception, 'name', 'unknown')
        return ErrorInfo(
            error_id=f"import_{id(exception)}",
            category=ErrorCategory.DEPENDENCY,
            severity=ErrorSeverity.HIGH,
            title="모듈 가져오기 실패",
            message=f"필요한 모듈을 가져올 수 없습니다: {module_name}",
            suggestion=f"pip install {module_name}으로 모듈을 설치하거나, 해당 기능을 비활성화해주세요.",
            details=str(exception)
        )
    
    def _handle_file_not_found_error(self, exception: FileNotFoundError) -> ErrorInfo:
        """FileNotFoundError 처리"""
        return ErrorInfo(
            error_id=f"file_not_found_{id(exception)}",
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            title="파일을 찾을 수 없음",
            message=f"요청한 파일을 찾을 수 없습니다: {exception.filename}",
            suggestion="파일 경로를 확인하거나 필요한 파일을 생성해주세요.",
            details=str(exception)
        )
    
    def _handle_permission_error(self, exception: PermissionError) -> ErrorInfo:
        """PermissionError 처리"""
        return ErrorInfo(
            error_id=f"permission_{id(exception)}",
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.HIGH,
            title="권한 부족",
            message="파일 또는 디렉터리에 액세스할 권한이 없습니다.",
            suggestion="관리자 권한으로 실행하거나 파일 권한을 확인해주세요.",
            details=str(exception)
        )
    
    def _handle_value_error(self, exception: ValueError) -> ErrorInfo:
        """ValueError 처리"""
        return ErrorInfo(
            error_id=f"value_{id(exception)}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            title="잘못된 값",
            message="제공된 값이 올바르지 않습니다.",
            suggestion="입력 값을 확인하고 올바른 형식으로 다시 시도해주세요.",
            details=str(exception)
        )
    
    def _handle_key_error(self, exception: KeyError) -> ErrorInfo:
        """KeyError 처리"""
        key = exception.args[0] if exception.args else "unknown"
        return ErrorInfo(
            error_id=f"key_{id(exception)}",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.MEDIUM,
            title="설정 키 누락",
            message=f"필요한 설정 항목을 찾을 수 없습니다: {key}",
            suggestion="설정 파일을 확인하고 누락된 항목을 추가해주세요.",
            details=str(exception)
        )
    
    def _handle_connection_error(self, exception: ConnectionError) -> ErrorInfo:
        """ConnectionError 처리"""
        return ErrorInfo(
            error_id=f"connection_{id(exception)}",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            title="연결 오류",
            message="서버에 연결할 수 없습니다.",
            suggestion="네트워크 연결을 확인하고 잠시 후 다시 시도해주세요.",
            details=str(exception)
        )
    
    def _handle_timeout_error(self, exception: TimeoutError) -> ErrorInfo:
        """TimeoutError 처리"""
        return ErrorInfo(
            error_id=f"timeout_{id(exception)}",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            title="시간 초과",
            message="요청이 시간 초과되었습니다.",
            suggestion="잠시 후 다시 시도하거나 타임아웃 설정을 늘려보세요.",
            details=str(exception)
        )
    
    def _handle_unknown_error(self, exception: Exception) -> ErrorInfo:
        """알 수 없는 예외 처리"""
        return ErrorInfo(
            error_id=f"unknown_{id(exception)}",
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            title="예상치 못한 오류",
            message="예상치 못한 오류가 발생했습니다.",
            suggestion="문제가 지속되면 관리자에게 문의해주세요.",
            details=str(exception)
        )
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """오류 정보를 로깅합니다."""
        log_level = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"[{error_info.error_id}] {error_info.title}: {error_info.message}",
            extra={'error_info': error_info}
        )
    
    def register_error_mapping(self, exception_type: Type[Exception], handler: Callable[[Exception], ErrorInfo]) -> None:
        """커스텀 예외 매핑을 등록합니다."""
        self._error_mappings[exception_type] = handler
    
    def add_context_provider(self, provider: Callable[[], Dict[str, Any]]) -> None:
        """컨텍스트 정보 제공자를 추가합니다."""
        self._context_providers.append(provider)


# 전역 오류 처리기 인스턴스
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """전역 오류 처리기를 반환합니다."""
    return _global_error_handler


def handle_errors(
    show_user_message: bool = True,
    reraise: bool = False,
    fallback_return=None
):
    """함수 데코레이터: 자동 오류 처리"""
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = get_error_handler().handle_error(
                    e, 
                    ErrorContext(
                        function_name=func.__name__,
                        input_data={'args': str(args), 'kwargs': str(kwargs)}
                    )
                )
                
                if show_user_message:
                    # Streamlit UI에서 오류 표시 (실제 구현에서는 streamlit import)
                    try:
                        import streamlit as st
                        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                            st.error(f"🚨 {error_info.title}: {error_info.message}")
                        else:
                            st.warning(f"⚠️ {error_info.title}: {error_info.message}")
                        
                        if error_info.suggestion:
                            st.info(f"💡 {error_info.suggestion}")
                    except ImportError:
                        # Streamlit이 없는 환경에서는 일반 로깅만
                        pass
                
                if reraise:
                    raise
                
                return fallback_return
        
        return wrapper
    return decorator


def create_streamlit_error_ui(error_info: ErrorInfo) -> None:
    """Streamlit UI에 오류 정보를 표시합니다."""
    try:
        import streamlit as st
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            st.error(f"🆘 **{error_info.title}**")
            st.error(error_info.message)
        elif error_info.severity == ErrorSeverity.HIGH:
            st.error(f"🚨 **{error_info.title}**")
            st.error(error_info.message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            st.warning(f"⚠️ **{error_info.title}**")
            st.warning(error_info.message)
        else:
            st.info(f"ℹ️ **{error_info.title}**")
            st.info(error_info.message)
        
        if error_info.suggestion:
            st.info(f"💡 **제안사항:** {error_info.suggestion}")
        
        # 디버그 정보 (개발 모드에서만)
        if error_info.details and st.session_state.get('debug_mode', False):
            with st.expander("🔍 상세 정보 (개발용)"):
                st.code(error_info.details)
                if error_info.stack_trace:
                    st.code(error_info.stack_trace)
    
    except ImportError:
        logger.warning("Streamlit not available for error UI display")


def setup_streamlit_context_provider():
    """Streamlit 세션 컨텍스트 정보를 제공하는 프로바이더를 설정합니다."""
    
    def get_streamlit_context():
        try:
            import streamlit as st
            return {
                'session_id': getattr(st.session_state, '_get_session_id', lambda: 'unknown')(),
                'user_agent': st.get_option('browser.userAgent') if hasattr(st, 'get_option') else 'unknown'
            }
        except ImportError:
            return {'streamlit': 'not_available'}
    
    get_error_handler().add_context_provider(get_streamlit_context)