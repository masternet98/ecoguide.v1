# 라벨링 시스템 구현 문서

## 📋 개요

EcoGuide.v1에 **완전한 라벨링 및 학습 데이터 관리 시스템**이 구현되었습니다. 사용자가 폐기물 분류를 확인할 때 자동으로 학습 데이터가 저장되며, 관리자가 이를 조회하고 관리할 수 있습니다.

## 🎯 목표

1. **자동 학습 데이터 수집**: 사용자 확인 시 이미지와 분류 정보 자동 저장
2. **구조화된 저장**: JSON 형식의 메타데이터로 일관성 있는 데이터 관리
3. **효율적인 관리**: 카테고리별로 정렬된 데이터 조회 및 검색
4. **향후 활용**: 수집된 데이터를 이용한 모델 재학습 기반 마련

## 📦 구현 내용

### 1. LabelingService (`src/domains/analysis/services/labeling_service.py`)

**책임**: 라벨링 데이터의 저장, 인덱싱, 조회

**주요 기능:**
```python
# 라벨 저장
save_label(
    image_bytes: bytes,
    analysis_result: Dict,
    user_feedback: Optional[Dict]
) -> Dict[str, Any]

# 통계 조회
get_category_statistics() -> Dict[str, Any]

# 카테고리별 라벨 조회
get_labels_by_primary_category(primary_category: str) -> List[Dict]
get_labels_by_secondary_category(primary_cat: str, secondary_cat: str) -> List[Dict]

# 라벨 상세 정보
get_label_details(file_id: str) -> Optional[Dict]
```

**저장 경로:**
- 이미지: `/uploads/user_images/{uuid}.jpg`
- 라벨: `/uploads/labels/{uuid}.json`
- 인덱스: `/uploads/labels/_index.json`

### 2. CompleteStep 통합 (`app_new.py`)

**변경 사항:**
- Step 4 (분류 완료)에서 자동으로 라벨링 서비스 호출
- 이미지, 분석 결과, 사용자 피드백을 함께 저장
- 저장 성공/실패 메시지 표시
- 상세한 로깅 추가

**코드:**
```python
labeling_service = self.app_context.get_service('labeling_service')
if labeling_service and image_bytes:
    label_result = labeling_service.save_label(
        image_bytes=image_bytes,
        analysis_result=normalized,
        user_feedback=normalized.get('user_feedback', {})
    )
```

### 3. 관리자 대시보드 (`pages/admin_labeling_dashboard.py`)

**3개의 탭:**

#### 📈 통계 탭
- 전체 라벨링 데이터 개수
- 마지막 업데이트 시간
- 카테고리별 분포 (테이블 + 차트)

#### 🏷️ 데이터 조회 탭
1. 주 카테고리 선택 (8개)
2. 세부 카테고리 선택 (선택사항)
3. 매칭된 이미지 3열 그리드로 표시
4. 각 라벨에 "상세 보기" 버튼

#### 📋 상세 정보 탭
1. 파일 ID로 검색
2. 이미지 + 분류 정보 2열 레이아웃
3. 크기, 신뢰도, 판단 근거, 피드백 표시
4. 원본 JSON 데이터 확인

### 4. ServiceFactory 등록

**변경 사항:**
- `SERVICE_DOMAIN_MAP`에 `labeling_service` 추가
- `create_default_service_registry()`에 서비스 등록

```python
# SERVICE_DOMAIN_MAP
SERVICE_DOMAIN_MAP = {
    ...
    'labeling_service': 'analysis',  # 추가됨
    ...
}

# 서비스 등록
registry.register_service(
    name='labeling_service',
    service_class=type('LabelingService', (), {}),
    module_path='src.domains.analysis.services.labeling_service',
    dependencies=[],
    is_optional=False,
    singleton=True
)
```

### 5. 테스트 페이지 (`pages/test_labeling.py`)

**기능:**
- 라벨링 서비스 상태 확인
- 테스트 이미지 생성 및 저장
- 저장된 데이터 조회 및 검증

## 📊 데이터 구조

### 라벨 JSON (`/uploads/labels/{uuid}.json`)

```json
{
  "file_id": "uuid",
  "image_path": "/uploads/user_images/uuid.jpg",
  "timestamp": "2025-10-26T20:04:16.120082",
  "classification": {
    "primary_category": "FURN",
    "primary_category_name": "가구",
    "secondary_category": "FURN_BED",
    "secondary_category_name": "침대/매트리스",
    "object_name": "침대"
  },
  "dimensions": {
    "width_cm": 200,
    "height_cm": 120,
    "depth_cm": 30,
    "dimension_sum_cm": 350
  },
  "confidence": 0.95,
  "reasoning": "분석 근거",
  "user_feedback": {
    "notes": "사용자 피드백",
    "timestamp": "2025-10-26T..."
  },
  "metadata": {
    "labeling_quality": 0.98
  }
}
```

### 인덱스 JSON (`/uploads/labels/_index.json`)

```json
{
  "version": "1.0",
  "created_at": "2025-10-26T...",
  "total_labels": 100,
  "labels_by_category": {
    "FURN": {
      "count": 30,
      "subcategories": {
        "FURN_BED": 15,
        "FURN_SOFA": 10,
        "FURN_TABLE": 5
      }
    }
  },
  "labels": [...]
}
```

## 🚀 사용 흐름

### 1. 사용자 입장 (자동)

```
이미지 업로드 (Step 1)
    ↓
이미지 분석 (Step 2)
    ↓
결과 확인 및 수정 (Step 3)
    ↓
제출 (Step 4)
    ↓
[자동] LabelingService.save_label()
    ├── 이미지 저장
    ├── JSON 라벨 저장
    ├── 인덱스 업데이트
    └── 확인 메시지 표시
```

### 2. 관리자 입장 (수동)

```
admin_labeling_dashboard.py 접속
    ↓
카테고리 선택
    ↓
라벨링 데이터 조회/분석
    ↓
필요시 상세 정보 확인
```

## 🧪 테스트 방법

### 방법 1: 테스트 페이지 사용

```bash
# Streamlit 실행
streamlit run pages/test_labeling.py
```

**탭 2: 💾 테스트 데이터 저장**
1. 이미지 색상 선택
2. 분석 결과 입력 (물품명, 카테고리, 신뢰도, 크기)
3. "💾 라벨 저장" 버튼 클릭
4. 저장 성공 메시지 확인

**탭 3: 🔍 저장된 데이터 확인**
1. 카테고리 선택
2. 저장된 라벨 목록 확인
3. 각 라벨 상세 정보 확인

### 방법 2: app_new.py에서 실제 테스트

```bash
streamlit run app_new.py
```

**단계:**
1. 📷 이미지 캡처 또는 업로드
2. 📝 프롬프트 설정 후 "🤖 분석" 클릭
3. 📋 결과 확인 및 분류 선택
4. ✅ "✅ 확인" 버튼 클릭
5. 📊 "📊 학습 데이터로 저장되었습니다" 메시지 확인

### 방법 3: Python 직접 테스트

```python
from src.domains.analysis.services.labeling_service import LabelingService
from src.app.core.config import load_config
from PIL import Image
import io

# 서비스 초기화
config = load_config()
service = LabelingService(config)

# 테스트 이미지 생성
test_image = Image.new('RGB', (100, 100), color='red')
img_bytes = io.BytesIO()
test_image.save(img_bytes, format='JPEG')
image_bytes = img_bytes.getvalue()

# 라벨 저장
result = service.save_label(
    image_bytes=image_bytes,
    analysis_result={
        'object_name': '침대',
        'primary_category': 'FURN',
        'secondary_category': 'FURN_BED',
        'confidence': 0.95,
        'dimensions': {'width_cm': 200, 'height_cm': 120, 'depth_cm': 30}
    }
)

print(f"성공: {result['success']}")
print(f"파일 ID: {result['file_id']}")
```

## 🔧 구성 요소

### 파일 생성

```
src/domains/analysis/services/
└── labeling_service.py          ✅ 새로 생성

pages/
├── admin_labeling_dashboard.py  ✅ 새로 생성
└── test_labeling.py             ✅ 새로 생성

instructions/
└── labeling_system_guide.md     ✅ 새로 생성
```

### 파일 수정

```
app_new.py
├── logger 임포트 추가
└── CompleteStep.render() 수정
    └── 라벨링 서비스 호출 추가

src/app/core/service_factory.py
├── SERVICE_DOMAIN_MAP에 labeling_service 추가
└── create_default_service_registry()에 서비스 등록
```

## 📁 디렉토리 구조

```
uploads/
├── user_images/              # 라벨링된 이미지
│   ├── {uuid}.jpg
│   ├── {uuid}.jpg
│   └── ...
├── labels/                   # 라벨 메타데이터
│   ├── _index.json          # 전체 인덱스
│   ├── {uuid}.json          # 개별 라벨
│   └── ...
├── districts/               # 기존 지역 데이터
├── monitoring/              # 기존 모니터링 데이터
└── waste_types/             # 기존 폐기물 분류 데이터
```

## ✅ 검증 체크리스트

- [x] LabelingService 구현
- [x] 이미지 저장 기능
- [x] JSON 라벨 저장 기능
- [x] 인덱스 관리 기능
- [x] 카테고리별 조회 기능
- [x] 라벨 상세 정보 조회 기능
- [x] CompleteStep에 라벨링 통합
- [x] ServiceFactory에 등록
- [x] 관리자 대시보드 (3개 탭)
- [x] 테스트 페이지
- [x] 문서화
- [x] 기본 테스트 완료

## 🔍 주의사항

### 경로 문제

LabelingService의 경로 계산:
```python
current_file = Path(__file__).resolve()
project_root = current_file.parents[4]
base_path = project_root / 'uploads'
```

`src/domains/analysis/services/labeling_service.py`에서 프로젝트 루트까지:
- `labeling_service.py` (파일)
- `services` (1단계)
- `analysis` (2단계)
- `domains` (3단계)
- `src` (4단계)
- 프로젝트 루트 (부모 4개)

### 세션 상태

Streamlit의 재실행(rerun)으로 인해 상태가 초기화될 수 있으므로, `AnalysisState`에서 세션 상태를 사용하여 데이터 보존:
```python
if 'analysis_step' not in st.session_state:
    st.session_state.analysis_step = 'image_input'
```

### 라벨링 품질 점수

자동 계산 (0.0 ~ 1.0):
- 신뢰도 (40%): AI의 분석 신뢰도
- 크기 정보 (30%): 차원 정보 포함 여부
- 사용자 피드백 (30%): 피드백 메모 입력 여부

## 📚 추가 문서

- `instructions/labeling_system_guide.md`: 상세 기술 가이드
- 각 페이지의 inline 문서: 함수별 상세 설명

## 🚫 알려진 제한사항

1. **데이터베이스 미지원**: 현재 파일 기반 저장 (향후 DB 연동 예정)
2. **데이터 마이그레이션**: 파일 경로 변경 시 수동 마이그레이션 필요
3. **동시성**: 다중 사용자 환경에서 인덱스 충돌 가능 (락 메커니즘 추가 필요)

## 🔮 향후 확장 계획

- [ ] CSV/Excel 내보내기
- [ ] 데이터 검증 및 품질 필터링
- [ ] 모델 재학습 파이프라인
- [ ] 데이터 버전 관리
- [ ] 다중 모델 성능 비교
- [ ] 데이터베이스 백엔드 지원
- [ ] 동시성 제어 (락, 트랜잭션)
- [ ] 데이터 암호화

## 📞 지원

문제가 발생하는 경우:

1. **테스트 페이지** (`pages/test_labeling.py`)에서 서비스 상태 확인
2. **로그** 확인: `logger.info/warning/error` 메시지
3. **파일 시스템** 확인: `/uploads/user_images/`, `/uploads/labels/` 디렉토리
4. **세션 상태** 확인: Streamlit 개발자 도구에서 세션 상태 확인
