"""
중앙화된 로깅 시스템
확장 가능하고 구조화된 로깅을 제공합니다.
"""
import os
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from enum import Enum
import threading
from dataclasses import dataclass, asdict


class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """로그 카테고리"""
    SYSTEM = "SYSTEM"
    CSV_PROCESSING = "CSV_PROCESSING"
    WEB_SCRAPING = "WEB_SCRAPING"
    API_CALL = "API_CALL"
    FILE_OPERATION = "FILE_OPERATION"
    UI_INTERACTION = "UI_INTERACTION"
    DATABASE = "DATABASE"
    VALIDATION = "VALIDATION"


@dataclass
class LogContext:
    """로그 컨텍스트 정보"""
    function_name: str
    module_name: str
    step: str
    category: LogCategory
    start_time: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    

@dataclass
class LogEntry:
    """구조화된 로그 엔트리"""
    timestamp: str
    level: LogLevel
    category: LogCategory
    module: str
    function: str
    step: str
    message: str
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error_type: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    correlation_id: Optional[str] = None


class EcoGuideLogger:
    """EcoGuide 애플리케이션 전용 로깅 시스템"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.log_entries: List[LogEntry] = []
        self._max_entries = 10000  # 메모리 관리를 위한 최대 엔트리 수
        self._setup_file_logging()
        
    def _setup_file_logging(self):
        """파일 로깅 설정"""
        # 프로젝트 루트의 logs 디렉토리 사용 (도커/클라우드 배포 호환)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        logs_dir = os.path.join(project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # 날짜별 로그 파일
        today = datetime.now().strftime("%Y%m%d")
        self.log_file_path = os.path.join(logs_dir, f"ecoguide_{today}.jsonl")
        
        # 표준 Python 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(logs_dir, f"ecoguide_standard_{today}.log"), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.python_logger = logging.getLogger('EcoGuide')
    
    def log(self, 
            level: LogLevel, 
            category: LogCategory,
            module: str,
            function: str,
            step: str,
            message: str,
            success: Optional[bool] = None,
            duration_ms: Optional[float] = None,
            error: Optional[Exception] = None,
            context_data: Optional[Dict[str, Any]] = None,
            correlation_id: Optional[str] = None):
        """구조화된 로그 생성"""
        
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            category=category,
            module=module,
            function=function,
            step=step,
            message=message,
            success=success,
            duration_ms=duration_ms,
            context_data=context_data,
            correlation_id=correlation_id
        )
        
        # 에러 정보 추가
        if error:
            entry.error_type = type(error).__name__
            entry.error_details = {
                "message": str(error),
                "args": list(error.args) if error.args else None
            }
            entry.stack_trace = traceback.format_exc()
            entry.success = False
        
        # 메모리에 저장
        self.log_entries.append(entry)
        
        # 메모리 관리
        if len(self.log_entries) > self._max_entries:
            self.log_entries = self.log_entries[-self._max_entries//2:]
        
        # 파일에 저장
        self._write_to_file(entry)
        
        # 표준 로깅도 수행
        log_line = f"[{category.value}] {module}::{function}::{step} - {message}"
        if success is not None:
            log_line += f" (성공: {success})"
        if duration_ms:
            log_line += f" ({duration_ms:.2f}ms)"
        
        python_level = getattr(logging, level.value)
        self.python_logger.log(python_level, log_line)
        
        return entry
    
    def _write_to_file(self, entry: LogEntry):
        """로그 엔트리를 JSONL 파일에 저장"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                json.dump(asdict(entry), f, ensure_ascii=False, default=str)
                f.write('\n')
        except Exception as e:
            # 로깅 실패는 애플리케이션을 중단시키면 안됨
            print(f"로그 파일 쓰기 실패: {e}")
    
    def get_logs(self, 
                 level_filter: Optional[LogLevel] = None,
                 category_filter: Optional[LogCategory] = None,
                 module_filter: Optional[str] = None,
                 function_filter: Optional[str] = None,
                 success_filter: Optional[bool] = None,
                 limit: Optional[int] = None) -> List[LogEntry]:
        """필터링된 로그 조회"""
        
        filtered_logs = self.log_entries.copy()
        
        if level_filter:
            filtered_logs = [log for log in filtered_logs if log.level == level_filter]
        
        if category_filter:
            filtered_logs = [log for log in filtered_logs if log.category == category_filter]
        
        if module_filter:
            filtered_logs = [log for log in filtered_logs if module_filter.lower() in log.module.lower()]
        
        if function_filter:
            filtered_logs = [log for log in filtered_logs if function_filter.lower() in log.function.lower()]
        
        if success_filter is not None:
            filtered_logs = [log for log in filtered_logs if log.success == success_filter]
        
        # 최신순 정렬
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        if limit:
            filtered_logs = filtered_logs[:limit]
        
        return filtered_logs
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """최근 N시간 내 에러 요약"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        error_logs = [
            log for log in self.log_entries 
            if log.level == LogLevel.ERROR and log.timestamp > cutoff_str
        ]
        
        # 에러 타입별 집계
        error_counts = {}
        for log in error_logs:
            error_type = log.error_type or "Unknown"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # 모듈별 에러 집계
        module_errors = {}
        for log in error_logs:
            module = log.module
            module_errors[module] = module_errors.get(module, 0) + 1
        
        return {
            "total_errors": len(error_logs),
            "error_by_type": error_counts,
            "error_by_module": module_errors,
            "recent_errors": error_logs[:10]  # 최근 10개
        }
    
    def clear_logs(self):
        """메모리의 로그 클리어 (파일은 유지)"""
        self.log_entries.clear()


# 전역 로거 인스턴스
logger = EcoGuideLogger()


def log_function(category: LogCategory, 
                step_name: Optional[str] = None,
                include_args: bool = False,
                include_result: bool = False):
    """함수 실행을 자동으로 로깅하는 데코레이터"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            module_name = func.__module__
            function_name = func.__name__
            step = step_name or f"{function_name}_execution"
            
            # 함수 시작 로그
            start_time = datetime.now()
            context_data = {}
            
            if include_args:
                context_data["args"] = [str(arg) for arg in args]
                context_data["kwargs"] = {k: str(v) for k, v in kwargs.items()}
            
            logger.log(
                LogLevel.INFO,
                category,
                module_name,
                function_name,
                f"{step}_시작",
                f"{function_name} 함수 실행 시작",
                context_data=context_data
            )
            
            try:
                # 함수 실행
                result = func(*args, **kwargs)
                
                # 성공 로그
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                result_data = {}
                if include_result:
                    result_data["result"] = str(result)[:500]  # 결과는 500자로 제한
                
                logger.log(
                    LogLevel.INFO,
                    category,
                    module_name,
                    function_name,
                    f"{step}_완료",
                    f"{function_name} 함수 실행 완료",
                    success=True,
                    duration_ms=duration_ms,
                    context_data=result_data
                )
                
                return result
                
            except Exception as e:
                # 에러 로그
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                logger.log(
                    LogLevel.ERROR,
                    category,
                    module_name,
                    function_name,
                    f"{step}_오류",
                    f"{function_name} 함수 실행 중 오류 발생",
                    success=False,
                    duration_ms=duration_ms,
                    error=e,
                    context_data=context_data
                )
                
                raise  # 원본 예외를 다시 발생
        
        return wrapper
    return decorator


def log_step(category: LogCategory, 
            module: str, 
            function: str, 
            step: str):
    """개별 단계 로깅을 위한 컨텍스트 매니저"""
    
    class StepLogger:
        def __init__(self, category, module, function, step):
            self.category = category
            self.module = module
            self.function = function
            self.step = step
            self.start_time = None
            
        def __enter__(self):
            self.start_time = datetime.now()
            logger.log(
                LogLevel.INFO,
                self.category,
                self.module,
                self.function,
                f"{self.step}_시작",
                f"{self.step} 단계 시작"
            )
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            end_time = datetime.now()
            duration_ms = (end_time - self.start_time).total_seconds() * 1000
            
            if exc_type is None:
                logger.log(
                    LogLevel.INFO,
                    self.category,
                    self.module,
                    self.function,
                    f"{self.step}_완료",
                    f"{self.step} 단계 완료",
                    success=True,
                    duration_ms=duration_ms
                )
            else:
                logger.log(
                    LogLevel.ERROR,
                    self.category,
                    self.module,
                    self.function,
                    f"{self.step}_오류",
                    f"{self.step} 단계 중 오류 발생",
                    success=False,
                    duration_ms=duration_ms,
                    error=exc_val
                )
    
    return StepLogger(category, module, function, step)


# 편의 함수들
def log_info(category: LogCategory, module: str, function: str, step: str, message: str, **kwargs):
    """INFO 레벨 로그"""
    return logger.log(LogLevel.INFO, category, module, function, step, message, **kwargs)


def log_warning(category: LogCategory, module: str, function: str, step: str, message: str, **kwargs):
    """WARNING 레벨 로그"""
    return logger.log(LogLevel.WARNING, category, module, function, step, message, **kwargs)


def log_error(category: LogCategory, module: str, function: str, step: str, message: str, error: Exception = None, **kwargs):
    """ERROR 레벨 로그"""
    return logger.log(LogLevel.ERROR, category, module, function, step, message, error=error, **kwargs)


def log_debug(category: LogCategory, module: str, function: str, step: str, message: str, **kwargs):
    """DEBUG 레벨 로그"""
    return logger.log(LogLevel.DEBUG, category, module, function, step, message, **kwargs)