"""
배치 작업 스케줄링 및 실행을 관리하는 서비스 모듈입니다.
APScheduler를 사용하여 주기적인 모니터링 작업을 자동화합니다.
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from src.core.config import Config
from src.core.logger import log_error, log_info, LogCategory
from src.services.monitoring_service import (
    run_monitoring_check, MonitoringConfig, get_monitoring_storage_path
)
from src.services.notification_service import (
    process_monitoring_results, load_notification_config, send_daily_summary_email
)

class BatchJobStatus(Enum):
    """배치 작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BatchJobType(Enum):
    """배치 작업 유형"""
    MONITORING_CHECK = "monitoring_check"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_REPORT = "weekly_report"
    CLEANUP = "cleanup"

@dataclass
class BatchJob:
    """배치 작업 정의"""
    id: str
    job_type: BatchJobType
    name: str
    description: str
    schedule_pattern: str  # cron-like pattern
    enabled: bool = True
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    last_status: BatchJobStatus = BatchJobStatus.PENDING
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}

@dataclass
class BatchConfig:
    """배치 시스템 설정"""
    enabled: bool = True
    max_concurrent_jobs: int = 3
    job_timeout_minutes: int = 30
    retry_attempts: int = 2
    retry_delay_seconds: int = 60
    cleanup_days: int = 30
    enable_monitoring_check: bool = True
    enable_daily_summary: bool = True
    enable_weekly_report: bool = False
    
    # 스케줄 설정
    monitoring_check_schedule: str = "0 2 * * *"  # 매일 새벽 2시
    daily_summary_schedule: str = "0 8 * * *"    # 매일 오전 8시
    weekly_report_schedule: str = "0 9 * * 1"    # 매주 월요일 오전 9시
    cleanup_schedule: str = "0 1 * * 0"          # 매주 일요일 새벽 1시

class BatchScheduler:
    """배치 작업 스케줄러 클래스"""
    
    def __init__(self, config: Optional[Config] = None, batch_config: Optional[BatchConfig] = None):
        self.config = config
        self.batch_config = batch_config or BatchConfig()
        self.jobs: Dict[str, BatchJob] = {}
        self.running_jobs: Dict[str, threading.Thread] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.batch_config.max_concurrent_jobs)
        self.scheduler_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        self._initialize_default_jobs()
    
    def _initialize_default_jobs(self):
        """기본 배치 작업들을 초기화합니다."""
        if self.batch_config.enable_monitoring_check:
            self.jobs["monitoring_check"] = BatchJob(
                id="monitoring_check",
                job_type=BatchJobType.MONITORING_CHECK,
                name="모니터링 검사",
                description="시군구별 URL 및 파일 변경사항 자동 검사",
                schedule_pattern=self.batch_config.monitoring_check_schedule,
                config={
                    "check_all_districts": True,
                    "send_notifications": True,
                    "max_concurrent_checks": 5
                }
            )
        
        if self.batch_config.enable_daily_summary:
            self.jobs["daily_summary"] = BatchJob(
                id="daily_summary",
                job_type=BatchJobType.DAILY_SUMMARY,
                name="일일 요약 발송",
                description="일일 모니터링 결과 요약 이메일 발송",
                schedule_pattern=self.batch_config.daily_summary_schedule,
                config={
                    "include_statistics": True,
                    "send_email": True
                }
            )
        
        if self.batch_config.enable_weekly_report:
            self.jobs["weekly_report"] = BatchJob(
                id="weekly_report",
                job_type=BatchJobType.WEEKLY_REPORT,
                name="주간 보고서",
                description="주간 모니터링 통계 및 트렌드 분석",
                schedule_pattern=self.batch_config.weekly_report_schedule,
                config={
                    "analyze_trends": True,
                    "generate_charts": False
                }
            )
        
        # 정리 작업
        self.jobs["cleanup"] = BatchJob(
            id="cleanup",
            job_type=BatchJobType.CLEANUP,
            name="데이터 정리",
            description="오래된 로그 및 임시 파일 정리",
            schedule_pattern=self.batch_config.cleanup_schedule,
            config={
                "cleanup_days": self.batch_config.cleanup_days,
                "cleanup_logs": True,
                "cleanup_temp_files": True
            }
        )
    
    def get_batch_storage_path(self) -> str:
        """배치 작업 데이터 저장 경로를 반환합니다."""
        monitoring_dir = get_monitoring_storage_path(self.config)
        batch_dir = os.path.join(monitoring_dir, 'batch')
        os.makedirs(batch_dir, exist_ok=True)
        return batch_dir
    
    def get_batch_history_path(self) -> str:
        """배치 실행 이력 파일 경로를 반환합니다."""
        storage_dir = self.get_batch_storage_path()
        return os.path.join(storage_dir, "batch_history.json")
    
    def load_job_history(self) -> Dict[str, Any]:
        """배치 작업 이력을 로드합니다."""
        history_path = self.get_batch_history_path()
        if not os.path.exists(history_path):
            return {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                },
                "jobs": {}
            }
        
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "batch_service", "load_job_history",
                "배치 이력 로드 실패", f"Error: {str(e)}", error=e
            )
            return {"metadata": {}, "jobs": {}}
    
    def save_job_history(self, history_data: Dict[str, Any]) -> bool:
        """배치 작업 이력을 저장합니다."""
        history_path = self.get_batch_history_path()
        try:
            history_data["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log_error(
                LogCategory.FILE_OPERATION, "batch_service", "save_job_history",
                "배치 이력 저장 실패", f"Error: {str(e)}", error=e
            )
            return False
    
    def _should_run_job(self, job: BatchJob) -> bool:
        """작업을 실행해야 하는지 확인합니다."""
        if not job.enabled:
            return False
        
        if job.id in self.running_jobs:
            return False  # 이미 실행 중인 작업
        
        # 스케줄 패턴 확인 (간단한 cron-like 패턴 파싱)
        # 형식: "분 시 일 월 요일" (예: "0 2 * * *" = 매일 새벽 2시)
        return self._check_schedule_pattern(job.schedule_pattern)
    
    def _check_schedule_pattern(self, pattern: str) -> bool:
        """
        간단한 cron-like 스케줄 패턴을 확인합니다.
        현재는 기본적인 패턴만 지원합니다.
        """
        try:
            parts = pattern.split()
            if len(parts) != 5:
                return False
            
            now = datetime.now()
            minute, hour, day, month, weekday = parts
            
            # 분 확인
            if minute != "*" and int(minute) != now.minute:
                return False
            
            # 시간 확인
            if hour != "*" and int(hour) != now.hour:
                return False
            
            # 일 확인
            if day != "*" and int(day) != now.day:
                return False
            
            # 월 확인
            if month != "*" and int(month) != now.month:
                return False
            
            # 요일 확인 (0=일요일, 1=월요일, ...)
            if weekday != "*" and int(weekday) != now.weekday() + 1:
                return False
            
            return True
            
        except (ValueError, IndexError):
            return False
    
    def _execute_monitoring_check(self, job: BatchJob) -> Dict[str, Any]:
        """모니터링 검사 작업을 실행합니다."""
        log_info(
            LogCategory.SYSTEM, "batch_service", "_execute_monitoring_check",
            "모니터링 검사 시작", f"Job: {job.id}"
        )
        
        try:
            # 모니터링 설정
            monitoring_config = MonitoringConfig(
                max_concurrent_checks=job.config.get("max_concurrent_checks", 5)
            )
            
            # 모니터링 실행
            monitoring_result = run_monitoring_check(
                config=self.config,
                monitoring_config=monitoring_config
            )
            
            # 알림 처리
            if job.config.get("send_notifications", True):
                from src.services.monitoring_service import MonitoringResult
                # 모니터링 결과에서 문제가 있는 경우들을 추출
                problem_results = []
                for district_key, district_summary in monitoring_result["districts"].items():
                    for result_data in district_summary["results"]:
                        if result_data["status"] in ["changed", "error", "unreachable"]:
                            mock_result = MonitoringResult(
                                district_key=district_key,
                                url_type=result_data.get("url_type", ""),
                                status=result_data.get("status", "error"),
                                change_type=result_data.get("change_type"),
                                error_message=result_data.get("error_message"),
                                response_time=result_data.get("response_time"),
                                checked_at=datetime.now().isoformat()
                            )
                            problem_results.append(mock_result)
                
                notification_result = process_monitoring_results(
                    problem_results, self.config
                )
                monitoring_result["notification_summary"] = notification_result
            
            log_info(
                LogCategory.SYSTEM, "batch_service", "_execute_monitoring_check",
                "모니터링 검사 완료", 
                f"Total: {monitoring_result['total_checked']}, Changed: {monitoring_result['changed_count']}"
            )
            
            return {
                "success": True,
                "result": monitoring_result
            }
            
        except Exception as e:
            log_error(
                LogCategory.SYSTEM, "batch_service", "_execute_monitoring_check",
                "모니터링 검사 실패", f"Job: {job.id}, Error: {str(e)}", error=e
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    def _execute_daily_summary(self, job: BatchJob) -> Dict[str, Any]:
        """일일 요약 발송 작업을 실행합니다."""
        log_info(
            LogCategory.SYSTEM, "batch_service", "_execute_daily_summary",
            "일일 요약 발송 시작", f"Job: {job.id}"
        )
        
        try:
            success = False
            
            if job.config.get("send_email", True):
                notification_config = load_notification_config(self.config)
                success = send_daily_summary_email(self.config, notification_config)
            
            log_info(
                LogCategory.SYSTEM, "batch_service", "_execute_daily_summary",
                "일일 요약 발송 완료", f"Success: {success}"
            )
            
            return {
                "success": success,
                "result": {
                    "email_sent": success
                }
            }
            
        except Exception as e:
            log_error(
                LogCategory.SYSTEM, "batch_service", "_execute_daily_summary",
                "일일 요약 발송 실패", f"Job: {job.id}, Error: {str(e)}", error=e
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    def _execute_cleanup(self, job: BatchJob) -> Dict[str, Any]:
        """정리 작업을 실행합니다."""
        log_info(
            LogCategory.SYSTEM, "batch_service", "_execute_cleanup",
            "데이터 정리 시작", f"Job: {job.id}"
        )
        
        try:
            cleanup_days = job.config.get("cleanup_days", 30)
            cutoff_date = datetime.now() - timedelta(days=cleanup_days)
            
            cleaned_items = []
            
            # 모니터링 이력 정리
            if job.config.get("cleanup_logs", True):
                from src.services.monitoring_service import get_monitoring_history_path
                history_path = get_monitoring_history_path(self.config)
                if os.path.exists(history_path):
                    # 이력 파일을 읽고 오래된 항목 제거
                    try:
                        with open(history_path, 'r', encoding='utf-8') as f:
                            history_data = json.load(f)
                        
                        original_count = 0
                        cleaned_count = 0
                        
                        for district_key, district_data in history_data.get("districts", {}).items():
                            change_history = district_data.get("change_history", [])
                            original_count += len(change_history)
                            
                            # 오래된 변경 이력 제거
                            filtered_history = []
                            for change in change_history:
                                change_date = datetime.fromisoformat(change["changed_at"])
                                if change_date >= cutoff_date:
                                    filtered_history.append(change)
                                else:
                                    cleaned_count += 1
                            
                            district_data["change_history"] = filtered_history
                        
                        if cleaned_count > 0:
                            with open(history_path, 'w', encoding='utf-8') as f:
                                json.dump(history_data, f, ensure_ascii=False, indent=2)
                            
                            cleaned_items.append(f"모니터링 이력 {cleaned_count}개 정리")
                    
                    except Exception as e:
                        log_error(
                            LogCategory.FILE_OPERATION, "batch_service", "_execute_cleanup",
                            "모니터링 이력 정리 실패", f"Error: {str(e)}", error=e
                        )
            
            # 알림 이력 정리
            from src.services.notification_service import get_notification_history_path
            notification_history_path = get_notification_history_path(self.config)
            if os.path.exists(notification_history_path):
                try:
                    with open(notification_history_path, 'r', encoding='utf-8') as f:
                        notification_data = json.load(f)
                    
                    events = notification_data.get("events", [])
                    original_count = len(events)
                    
                    # 오래된 이벤트 제거
                    filtered_events = []
                    for event in events:
                        event_date = datetime.fromisoformat(event["created_at"])
                        if event_date >= cutoff_date:
                            filtered_events.append(event)
                    
                    cleaned_count = original_count - len(filtered_events)
                    
                    if cleaned_count > 0:
                        notification_data["events"] = filtered_events
                        with open(notification_history_path, 'w', encoding='utf-8') as f:
                            json.dump(notification_data, f, ensure_ascii=False, indent=2)
                        
                        cleaned_items.append(f"알림 이력 {cleaned_count}개 정리")
                
                except Exception as e:
                    log_error(
                        LogCategory.FILE_OPERATION, "batch_service", "_execute_cleanup",
                        "알림 이력 정리 실패", f"Error: {str(e)}", error=e
                    )
            
            log_info(
                LogCategory.SYSTEM, "batch_service", "_execute_cleanup",
                "데이터 정리 완료", f"Items: {len(cleaned_items)}"
            )
            
            return {
                "success": True,
                "result": {
                    "cleaned_items": cleaned_items,
                    "cleanup_date": cutoff_date.isoformat()
                }
            }
            
        except Exception as e:
            log_error(
                LogCategory.SYSTEM, "batch_service", "_execute_cleanup",
                "데이터 정리 실패", f"Job: {job.id}, Error: {str(e)}", error=e
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    def _execute_job(self, job: BatchJob) -> Dict[str, Any]:
        """배치 작업을 실행합니다."""
        start_time = datetime.now()
        
        try:
            # 작업 상태 업데이트
            job.last_status = BatchJobStatus.RUNNING
            job.run_count += 1
            
            # 작업 유형별 실행
            if job.job_type == BatchJobType.MONITORING_CHECK:
                result = self._execute_monitoring_check(job)
            elif job.job_type == BatchJobType.DAILY_SUMMARY:
                result = self._execute_daily_summary(job)
            elif job.job_type == BatchJobType.CLEANUP:
                result = self._execute_cleanup(job)
            else:
                result = {"success": False, "error": f"Unknown job type: {job.job_type}"}
            
            # 실행 결과 처리
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if result["success"]:
                job.last_status = BatchJobStatus.COMPLETED
                job.last_run = datetime.now().isoformat()
                job.last_error = None
            else:
                job.last_status = BatchJobStatus.FAILED
                job.error_count += 1
                job.last_error = result.get("error", "Unknown error")
            
            # 이력에 저장
            history_data = self.load_job_history()
            
            if "jobs" not in history_data:
                history_data["jobs"] = {}
            
            if job.id not in history_data["jobs"]:
                history_data["jobs"][job.id] = {"executions": []}
            
            execution_record = {
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "execution_time_seconds": execution_time,
                "status": job.last_status.value,
                "success": result["success"],
                "result": result.get("result"),
                "error": result.get("error")
            }
            
            history_data["jobs"][job.id]["executions"].append(execution_record)
            # 최근 100개 실행 기록만 유지
            history_data["jobs"][job.id]["executions"] = history_data["jobs"][job.id]["executions"][-100:]
            
            self.save_job_history(history_data)
            
            return result
            
        except Exception as e:
            job.last_status = BatchJobStatus.FAILED
            job.error_count += 1
            job.last_error = str(e)
            
            log_error(
                LogCategory.SYSTEM, "batch_service", "_execute_job",
                "배치 작업 실행 실패", f"Job: {job.id}, Error: {str(e)}", error=e
            )
            
            return {"success": False, "error": str(e)}
    
    def run_job_manually(self, job_id: str) -> Dict[str, Any]:
        """배치 작업을 수동으로 실행합니다."""
        if job_id not in self.jobs:
            return {"success": False, "error": f"Job not found: {job_id}"}
        
        if job_id in self.running_jobs:
            return {"success": False, "error": f"Job already running: {job_id}"}
        
        job = self.jobs[job_id]
        
        log_info(
            LogCategory.SYSTEM, "batch_service", "run_job_manually",
            "수동 배치 작업 실행", f"Job: {job_id} ({job.name})"
        )
        
        return self._execute_job(job)
    
    def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        log_info(
            LogCategory.SYSTEM, "batch_service", "_scheduler_loop",
            "배치 스케줄러 시작", "자동 스케줄링 활성화"
        )
        
        while self.is_running:
            try:
                current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # 실행해야 할 작업들 확인
                for job_id, job in self.jobs.items():
                    if self._should_run_job(job):
                        log_info(
                            LogCategory.SYSTEM, "batch_service", "_scheduler_loop",
                            "스케줄된 배치 작업 실행", f"Job: {job_id} ({job.name})"
                        )
                        
                        # 별도 스레드에서 실행
                        thread = threading.Thread(
                            target=self._execute_job,
                            args=(job,),
                            name=f"batch_job_{job_id}"
                        )
                        thread.start()
                        self.running_jobs[job_id] = thread
                
                # 완료된 작업들 정리
                completed_jobs = []
                for job_id, thread in self.running_jobs.items():
                    if not thread.is_alive():
                        completed_jobs.append(job_id)
                
                for job_id in completed_jobs:
                    del self.running_jobs[job_id]
                
                # 1분마다 체크
                time.sleep(60)
                
            except Exception as e:
                log_error(
                    LogCategory.SYSTEM, "batch_service", "_scheduler_loop",
                    "스케줄러 루프 오류", f"Error: {str(e)}", error=e
                )
                time.sleep(60)
    
    def start_scheduler(self):
        """배치 스케줄러를 시작합니다."""
        if self.is_running:
            return False
        
        if not self.batch_config.enabled:
            log_info(
                LogCategory.SYSTEM, "batch_service", "start_scheduler",
                "배치 스케줄러", "비활성화 상태로 시작하지 않음"
            )
            return False
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="batch_scheduler",
            daemon=True
        )
        self.scheduler_thread.start()
        
        log_info(
            LogCategory.SYSTEM, "batch_service", "start_scheduler",
            "배치 스케줄러 시작됨", f"Jobs: {len(self.jobs)}"
        )
        
        return True
    
    def stop_scheduler(self):
        """배치 스케줄러를 중지합니다."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 실행 중인 작업들 완료 대기
        for job_id, thread in self.running_jobs.items():
            thread.join(timeout=30)  # 최대 30초 대기
        
        self.running_jobs.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        log_info(
            LogCategory.SYSTEM, "batch_service", "stop_scheduler",
            "배치 스케줄러 중지됨", ""
        )
    
    def get_job_status(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """배치 작업 상태를 조회합니다."""
        if job_id:
            if job_id not in self.jobs:
                return {"error": f"Job not found: {job_id}"}
            
            job = self.jobs[job_id]
            return {
                "id": job.id,
                "name": job.name,
                "type": job.job_type.value,
                "enabled": job.enabled,
                "status": job.last_status.value,
                "next_run": job.next_run,
                "last_run": job.last_run,
                "run_count": job.run_count,
                "error_count": job.error_count,
                "last_error": job.last_error,
                "is_running": job_id in self.running_jobs
            }
        else:
            # 전체 작업 상태
            return {
                "scheduler_running": self.is_running,
                "total_jobs": len(self.jobs),
                "running_jobs": len(self.running_jobs),
                "jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "enabled": job.enabled,
                        "status": job.last_status.value,
                        "last_run": job.last_run,
                        "is_running": job.id in self.running_jobs
                    }
                    for job in self.jobs.values()
                ]
            }

# 전역 스케줄러 인스턴스
_scheduler_instance: Optional[BatchScheduler] = None

def get_batch_scheduler(config: Optional[Config] = None, 
                       batch_config: Optional[BatchConfig] = None) -> BatchScheduler:
    """배치 스케줄러 싱글톤 인스턴스를 반환합니다."""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = BatchScheduler(config, batch_config)
    
    return _scheduler_instance

def initialize_batch_system(config: Optional[Config] = None, 
                          batch_config: Optional[BatchConfig] = None,
                          start_scheduler: bool = True) -> BatchScheduler:
    """배치 시스템을 초기화합니다."""
    scheduler = get_batch_scheduler(config, batch_config)
    
    if start_scheduler:
        scheduler.start_scheduler()
    
    return scheduler

def shutdown_batch_system():
    """배치 시스템을 종료합니다."""
    global _scheduler_instance
    
    if _scheduler_instance:
        _scheduler_instance.stop_scheduler()
        _scheduler_instance = None