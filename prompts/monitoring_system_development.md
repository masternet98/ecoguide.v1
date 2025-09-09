# 시군구 등록 정보 자동 변경 감지 및 관리 시스템 개발 가이드

## 📋 개요

시군구별 등록된 URL 정보 및 첨부파일의 변경사항을 주기적으로 자동 감지하고, 관리자에게 알림을 제공하는 시스템입니다. 향후 RAG(Retrieval-Augmented Generation) 시스템과 연계하여 사용자에게 최신 정보를 제공할 수 있도록 설계되었습니다.

## 🏗️ 시스템 아키텍처

### 핵심 컴포넌트

1. **변경 감지 엔진** (`monitoring_service.py`)
2. **알림 발송 시스템** (`notification_service.py`)
3. **배치 스케줄러** (`batch_service.py`)
4. **관리자 UI** (`monitoring_ui.py`, `pages/monitoring.py`)
5. **데이터 구조 확장** (기존 서비스 모듈 수정)

### 데이터 흐름

```
등록된 URL/파일 → 변경 감지 → 우선순위 결정 → 알림 발송 → 이력 저장
                     ↓
                배치 스케줄러 ← 관리자 UI
```

## 🔧 구현 상세

### 1. 변경 감지 시스템 (`src/services/monitoring_service.py`)

#### 주요 클래스 및 함수

```python
@dataclass
class MonitoringResult:
    """모니터링 결과를 담는 데이터 클래스"""
    district_key: str
    url_type: str
    status: str  # 'ok', 'changed', 'error', 'unreachable'
    change_type: Optional[str] = None
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    error_message: Optional[str] = None
    response_time: Optional[float] = None
    checked_at: Optional[str] = None

@dataclass
class MonitoringConfig:
    """모니터링 설정"""
    check_interval_hours: int = 24
    request_timeout: int = 30
    max_concurrent_checks: int = 5
    retry_attempts: int = 3
    keywords_to_track: List[str] = ["대형폐기물", "신고", "배출", "수수료"]
```

#### 핵심 기능

- **URL 콘텐츠 해시 계산**: 동적 요소 제거 후 MD5 해시 생성
- **파일 해시 검증**: 바이너리 파일의 무결성 검증
- **병렬 검사**: ThreadPoolExecutor를 활용한 동시 처리
- **단계적 검증**: 접근성 → 구조 → 내용 순차 검사

```python
def get_url_content_hash(url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """URL의 콘텐츠 해시값을 계산합니다."""
    # 동적 콘텐츠 제거 정규식
    content = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', content)
    content = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', content)
    content = re.sub(r'timestamp=\d+', 'timestamp=TIMESTAMP', content)
    
    hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()
    return hash_value, None, response_time
```

### 2. 알림 시스템 (`src/services/notification_service.py`)

#### 우선순위 결정 로직

```python
def determine_notification_priority(result: MonitoringResult) -> NotificationPriority:
    """모니터링 결과를 바탕으로 알림 우선순위를 결정합니다."""
    if result.status == 'unreachable':
        return NotificationPriority.CRITICAL      # 즉시 알림
    elif result.status == 'error':
        if 'file' in result.error_message.lower():
            return NotificationPriority.MEDIUM    # 주간 요약
        else:
            return NotificationPriority.HIGH      # 일일 요약
    elif result.status == 'changed':
        if result.change_type == 'structure':
            return NotificationPriority.HIGH      # 일일 요약
        else:
            return NotificationPriority.MEDIUM    # 주간 요약
```

#### 다채널 알림 발송

- **이메일**: SMTP를 통한 HTML/텍스트 메시지
- **로그**: 구조화된 로그 메시지
- **대시보드**: 실시간 상태 표시

### 3. 배치 스케줄러 (`src/services/batch_service.py`)

#### 기본 작업 정의

```python
# 모니터링 검사 (매일 새벽 2시)
"monitoring_check": {
    "schedule_pattern": "0 2 * * *",
    "description": "시군구별 URL 및 파일 변경사항 자동 검사"
}

# 일일 요약 발송 (매일 오전 8시)
"daily_summary": {
    "schedule_pattern": "0 8 * * *", 
    "description": "일일 모니터링 결과 요약 이메일 발송"
}

# 데이터 정리 (매주 일요일 새벽 1시)
"cleanup": {
    "schedule_pattern": "0 1 * * 0",
    "description": "오래된 로그 및 임시 파일 정리"
}
```

#### Cron-like 스케줄 패턴

```python
def _check_schedule_pattern(self, pattern: str) -> bool:
    """간단한 cron-like 스케줄 패턴을 확인합니다."""
    # 형식: "분 시 일 월 요일" (예: "0 2 * * *" = 매일 새벽 2시)
    parts = pattern.split()
    if len(parts) != 5:
        return False
    
    now = datetime.now()
    minute, hour, day, month, weekday = parts
    
    # 각 필드별 검증 로직
    return True  # 모든 조건 만족 시
```

### 4. 관리자 UI (`src/components/monitoring_ui.py`)

#### 탭 구성

1. **📈 대시보드**: 전체 시스템 상태 및 최근 변경사항
2. **🔍 수동 검사**: 즉시 모니터링 실행 및 결과 확인
3. **⚙️ 배치 관리**: 스케줄러 제어 및 작업 상태
4. **📧 알림 이력**: 과거 알림 내역 및 통계
5. **⚙️ 설정**: 이메일 알림 및 모니터링 설정

#### 핵심 UI 컴포넌트

```python
def show_monitoring_dashboard(config: Config):
    """모니터링 대시보드를 표시합니다."""
    # 메트릭 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 관리 지역", summary["overview"]["total_districts"])
    with col2:
        st.metric("건강한 지역", summary["overview"]["healthy_districts"])
    with col3:
        st.metric("문제 지역", len(summary["error_districts"]))
    
    # 최근 변경사항 테이블
    if summary["recent_changes"]:
        df = pd.DataFrame(changes_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
```

### 5. 데이터 구조 확장

#### 기존 링크 데이터에 모니터링 메타데이터 추가

```python
# src/services/link_collector_service.py 수정사항
def save_link(district_key: str, link_data: Dict[str, str], config: Optional[Config] = None) -> bool:
    # 기존 저장 로직 후...
    
    # 모니터링 메타데이터 초기화 (새로 생성된 경우)
    if "monitoring" not in data["links"][district_key]:
        data["links"][district_key]["monitoring"] = {
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "last_checked": None,
            "check_frequency": "daily",
            "priority": "medium",
            "failure_count": 0,
            "last_failure": None
        }
```

#### 이력 데이터 구조

```json
{
  "metadata": {
    "last_full_check": "2025-01-01T02:00:00",
    "total_checks": 150,
    "monitoring_enabled": true
  },
  "districts": {
    "서울특별시_강남구": {
      "info_url_hash": "abc123...",
      "system_url_hash": "def456...",
      "last_checked": "2025-01-01T02:00:00",
      "change_history": [
        {
          "url_type": "info_url",
          "change_type": "content",
          "previous_hash": "old_hash",
          "current_hash": "new_hash", 
          "changed_at": "2025-01-01T02:00:00"
        }
      ]
    }
  }
}
```

## 🚀 구현 순서

### 1단계: 핵심 서비스 개발
- `monitoring_service.py`: 변경 감지 핵심 로직
- `notification_service.py`: 알림 발송 관리
- `batch_service.py`: 배치 작업 스케줄링

### 2단계: 데이터 구조 확장
- 기존 `link_collector_service.py`에 모니터링 메타데이터 추가
- 이력 관리 함수 구현

### 3단계: 관리자 UI 개발
- `monitoring_ui.py`: UI 컴포넌트
- `pages/monitoring.py`: 독립 페이지

### 4단계: 테스트 및 검증
- 단위 테스트 작성
- 통합 테스트 실행
- 성능 검증

## 🔍 테스트 전략

### 단위 테스트 (`test/test_monitoring_system.py`)

```python
def test_url_hash_calculation():
    """URL 해시 계산 기능 테스트"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Test content</body></html>"
    
    with patch('requests.get', return_value=mock_response):
        hash_value, error, response_time = get_url_content_hash("http://example.com")
        assert hash_value is not None
        assert error is None
```

### 통합 테스트 시나리오

1. **URL 변경 감지**: Mock 서버로 콘텐츠 변경 시뮬레이션
2. **파일 무결성 검증**: 임시 파일 생성/수정/삭제
3. **알림 발송**: 이메일 Mock으로 발송 확인
4. **배치 스케줄**: 시간 Mock으로 스케줄링 테스트

## ⚙️ 설정 및 환경변수

### 필수 환경변수

```bash
# 이메일 알림 설정
NOTIFICATION_EMAIL_USER=your-email@gmail.com
NOTIFICATION_EMAIL_PASSWORD=your-app-password
NOTIFICATION_EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com

# 모니터링 설정 (선택사항)
MONITORING_CHECK_INTERVAL=24    # 시간 단위
MONITORING_TIMEOUT=30           # 초 단위
MONITORING_MAX_CONCURRENT=5     # 동시 검사 수
```

### Streamlit 페이지 설정

```python
# pages/monitoring.py
st.set_page_config(
    page_title="EcoGuide - 시스템 모니터링",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

## 📊 성능 고려사항

### 최적화 전략

1. **병렬 처리**: ThreadPoolExecutor로 다중 URL 동시 검사
2. **캐싱**: 동적 콘텐츠 제거로 불필요한 변경 감지 방지
3. **배치 분할**: 대량 지역 처리 시 점진적 실행
4. **이력 관리**: 오래된 데이터 자동 정리 (기본 30일)

### 리소스 관리

```python
# 동시 실행 제한
max_concurrent_checks: int = 5

# 요청 타임아웃
request_timeout: int = 30

# 이력 보관 기간
cleanup_days: int = 30
```

## 🔮 향후 확장 가능성

### RAG 시스템 연계

```python
# 사용자 문의 시 최신 정보 제공
def get_latest_district_info(district_key: str, url_type: str):
    """최신 지역 정보 및 변경사항 안내"""
    monitoring_data = load_monitoring_history()
    district_data = monitoring_data.get("districts", {}).get(district_key, {})
    
    if district_data.get(f"{url_type}_last_status") == "changed":
        return f"⚠️ 주의: 해당 정보가 최근 변경되었습니다. 최신 정보를 확인해주세요."
    
    return "✅ 최신 정보입니다."
```

### 추가 기능 아이디어

- **AI 기반 변경 중요도 분석**: OpenAI API로 변경 내용 분석
- **Slack/Teams 연동**: 추가 알림 채널
- **대시보드 API**: 외부 시스템 연계
- **모바일 앱 알림**: Push notification
- **웹훅 지원**: 외부 시스템 자동 연동

## 🐛 알려진 제한사항 및 해결방안

### 제한사항

1. **JavaScript 렌더링**: 정적 HTML만 분석 가능
2. **대용량 파일**: 메모리 사용량 증가
3. **네트워크 의존성**: 외부 사이트 접근 제한 시 오류

### 해결방안

1. **Selenium/Playwright 추가**: 동적 콘텐츠 렌더링
2. **스트리밍 해시**: 대용량 파일 청크 단위 처리
3. **VPN/프록시 지원**: 접근 제한 우회
4. **재시도 로직**: 일시적 네트워크 오류 대응

## 📝 코딩 컨벤션

### 파일 구조

```
src/
├── services/
│   ├── monitoring_service.py      # 변경 감지 핵심 로직
│   ├── notification_service.py    # 알림 발송 관리  
│   └── batch_service.py          # 배치 작업 스케줄링
├── components/
│   └── monitoring_ui.py          # UI 컴포넌트
└── pages/
    └── monitoring.py             # 독립 페이지

test/
└── test_monitoring_system.py    # 통합 테스트
```

### 네이밍 규칙

- **클래스**: PascalCase (`MonitoringResult`, `NotificationEvent`)
- **함수**: snake_case (`get_url_content_hash`, `determine_priority`)
- **상수**: UPPER_CASE (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- **파일명**: snake_case (`monitoring_service.py`)

### 에러 처리

```python
try:
    result = risky_operation()
except SpecificException as e:
    log_error(LogCategory.SYSTEM, "module", "function", "설명", f"Error: {str(e)}", error=e)
    return {"success": False, "error": str(e)}
```

## 🎯 마무리

이 시스템은 시군구별 등록 정보의 변경을 자동으로 감지하고 관리자에게 적시에 알림을 제공하는 완전한 솔루션입니다. 모듈화된 설계로 향후 확장이 용이하며, 철저한 테스트를 통해 안정성을 확보했습니다.

핵심 가치:
- **자동화**: 수동 확인 작업 없이 변경사항 자동 감지
- **지능적 알림**: 우선순위 기반 알림으로 중요도별 대응
- **확장성**: RAG 시스템과의 연계 가능한 구조
- **사용성**: 직관적인 관리자 UI로 쉬운 운영 관리

이 가이드를 참고하여 동일한 품질의 모니터링 시스템을 구축하거나 기존 시스템을 확장할 수 있습니다.