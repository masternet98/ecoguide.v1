"""
모니터링 시스템의 기본 기능을 테스트하는 스크립트입니다.
실제 네트워크 요청 없이 모니터링 로직을 검증합니다.
"""
import os
import sys
import json
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domains.monitoring.services.monitoring_service import (
    MonitoringResult, MonitoringConfig, check_single_url,
    get_url_content_hash, get_file_content_hash,
    load_monitoring_history, save_monitoring_history
)
from src.domains.monitoring.services.notification_service import (
    NotificationEvent, NotificationPriority, create_notification_event,
    determine_notification_priority
)
from src.domains.infrastructure.services.batch_service import BatchScheduler, BatchConfig

def test_url_hash_calculation():
    """URL 해시 계산 기능을 테스트합니다."""
    print("=== URL Hash Calculation Test ===")
    
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Test content</body></html>"
    
    with patch('src.services.monitoring_service.requests.get', return_value=mock_response):
        hash_value, error, response_time = get_url_content_hash("http://example.com", timeout=10)
        
        print(f"Hash calculated: {hash_value}")
        print(f"Error: {error}")
        print(f"Response time: {response_time}")
        
        assert hash_value is not None, "Hash should be calculated"
        assert error is None, "No error should occur"
        assert response_time is not None, "Response time should be recorded"
        
        print("[PASS] URL hash calculation test passed")
        
def test_file_hash_calculation():
    """파일 해시 계산 기능을 테스트합니다."""
    print("\n=== File Hash Calculation Test ===")
    
    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
        temp_file.write("Test file content for hashing")
        temp_file_path = temp_file.name
    
    try:
        # 파일 해시 계산
        hash_value = get_file_content_hash(temp_file_path)
        
        print(f"File hash: {hash_value}")
        assert hash_value is not None, "File hash should be calculated"
        
        # 존재하지 않는 파일 테스트
        no_file_hash = get_file_content_hash("nonexistent_file.txt")
        print(f"Non-existent file hash: {no_file_hash}")
        assert no_file_hash is None, "Non-existent file should return None"
        
        print("[PASS] File hash calculation test passed")
        
    finally:
        # 임시 파일 삭제
        os.unlink(temp_file_path)

def test_monitoring_history():
    """모니터링 이력 저장/로드 기능을 테스트합니다."""
    print("\n=== Monitoring History Test ===")
    
    # 임시 디렉토리에서 테스트
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock config
        mock_config = MagicMock()
        mock_config.district.uploads_dir = temp_dir
        
        with patch('src.services.monitoring_service.get_monitoring_storage_path', return_value=temp_dir):
            # 이력 로드 (파일이 없는 상태)
            history = load_monitoring_history(mock_config)
            print(f"Initial history: {history.keys()}")
            
            assert "metadata" in history, "Metadata should exist"
            assert "districts" in history, "Districts should exist"
            
            # 테스트 데이터 추가
            history["districts"]["test_district"] = {
                "last_checked": datetime.now().isoformat(),
                "info_url_hash": "test_hash_123"
            }
            
            # 이력 저장
            success = save_monitoring_history(history, mock_config)
            print(f"History save result: {success}")
            assert success, "History should be saved successfully"
            
            # 다시 로드하여 확인
            loaded_history = load_monitoring_history(mock_config)
            print(f"Loaded history districts: {list(loaded_history['districts'].keys())}")
            
            assert "test_district" in loaded_history["districts"], "Test district should exist"
            assert loaded_history["districts"]["test_district"]["info_url_hash"] == "test_hash_123"
            
            print("[PASS] Monitoring history test passed")

def test_notification_priority():
    """알림 우선순위 결정 로직을 테스트합니다."""
    print("\n=== Notification Priority Test ===")
    
    test_cases = [
        {
            "status": "unreachable",
            "expected": NotificationPriority.CRITICAL,
            "description": "Unreachable URL should be critical"
        },
        {
            "status": "error",
            "url_type": "info_url",
            "error_message": "HTTP 500",
            "expected": NotificationPriority.HIGH,
            "description": "URL error should be high priority"
        },
        {
            "status": "error",
            "url_type": "info_file",
            "error_message": "File not found",
            "expected": NotificationPriority.MEDIUM,
            "description": "File error should be medium priority"
        },
        {
            "status": "changed",
            "change_type": "structure",
            "expected": NotificationPriority.HIGH,
            "description": "Structure change should be high priority"
        },
        {
            "status": "changed",
            "change_type": "content",
            "expected": NotificationPriority.MEDIUM,
            "description": "Content change should be medium priority"
        }
    ]
    
    for case in test_cases:
        result = MonitoringResult(
            district_key="test_district",
            url_type=case.get("url_type", "info_url"),
            status=case["status"],
            change_type=case.get("change_type"),
            error_message=case.get("error_message")
        )
        
        priority = determine_notification_priority(result)
        print(f"Case: {case['description']}")
        print(f"  Expected: {case['expected'].value}, Got: {priority.value}")
        
        assert priority == case["expected"], f"Priority mismatch for {case['description']}"
    
    print("[PASS] Notification priority test passed")

def test_notification_event_creation():
    """알림 이벤트 생성 기능을 테스트합니다."""
    print("\n=== Notification Event Creation Test ===")
    
    # 변경 감지 결과 생성
    result = MonitoringResult(
        district_key="서울특별시_강남구",
        url_type="info_url",
        status="changed",
        change_type="content",
        checked_at=datetime.now().isoformat()
    )
    
    # 알림 이벤트 생성
    event = create_notification_event(result)
    
    print(f"Event ID: {event.id}")
    print(f"Priority: {event.priority.value}")
    print(f"Title: {event.title}")
    print(f"Message: {event.message}")
    
    assert event is not None, "Event should be created"
    assert event.priority == NotificationPriority.MEDIUM, "Content change should be medium priority"
    assert "서울특별시 강남구" in event.title, "District name should be in title"
    assert "배출정보" in event.title, "URL type should be translated"
    
    print("[PASS] Notification event creation test passed")

def test_batch_scheduler():
    """배치 스케줄러 기본 기능을 테스트합니다."""
    print("\n=== Batch Scheduler Test ===")
    
    # Mock config
    mock_config = MagicMock()
    batch_config = BatchConfig(enabled=False)  # 스케줄러 비활성화
    
    # 스케줄러 생성
    scheduler = BatchScheduler(mock_config, batch_config)
    
    print(f"Total jobs: {len(scheduler.jobs)}")
    print(f"Job IDs: {list(scheduler.jobs.keys())}")
    
    assert len(scheduler.jobs) > 0, "Default jobs should be created"
    assert "monitoring_check" in scheduler.jobs, "Monitoring check job should exist"
    assert "daily_summary" in scheduler.jobs, "Daily summary job should exist"
    
    # 작업 상태 조회
    status = scheduler.get_job_status()
    print(f"Scheduler running: {status['scheduler_running']}")
    print(f"Total jobs: {status['total_jobs']}")
    
    assert status['scheduler_running'] == False, "Scheduler should not be running"
    assert status['total_jobs'] == len(scheduler.jobs), "Job count should match"
    
    print("[PASS] Batch scheduler test passed")

def test_schedule_pattern_checking():
    """스케줄 패턴 확인 기능을 테스트합니다."""
    print("\n=== Schedule Pattern Test ===")
    
    mock_config = MagicMock()
    batch_config = BatchConfig(enabled=False)
    scheduler = BatchScheduler(mock_config, batch_config)
    
    # 현재 시간에 맞는 패턴과 맞지 않는 패턴 테스트
    now = datetime.now()
    
    # 항상 실행되어야 하는 패턴
    always_pattern = "* * * * *"
    result = scheduler._check_schedule_pattern(always_pattern)
    print(f"Always pattern (* * * * *): {result}")
    assert result == True, "Always pattern should return True"
    
    # 현재 시간과 일치하는 패턴
    current_pattern = f"{now.minute} {now.hour} * * *"
    result = scheduler._check_schedule_pattern(current_pattern)
    print(f"Current time pattern ({current_pattern}): {result}")
    assert result == True, "Current time pattern should return True"
    
    # 절대 실행되지 않을 패턴 (99분 99시)
    never_pattern = "99 99 * * *"
    result = scheduler._check_schedule_pattern(never_pattern)
    print(f"Never pattern (99 99 * * *): {result}")
    assert result == False, "Never pattern should return False"
    
    print("[PASS] Schedule pattern test passed")

def main():
    """모든 테스트를 실행합니다."""
    print("Starting monitoring system tests...")
    print("=" * 50)
    
    try:
        test_url_hash_calculation()
        test_file_hash_calculation()
        test_monitoring_history()
        test_notification_priority()
        test_notification_event_creation()
        test_batch_scheduler()
        test_schedule_pattern_checking()
        
        print("\n" + "=" * 50)
        print("[PASS] All monitoring system tests passed!")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)