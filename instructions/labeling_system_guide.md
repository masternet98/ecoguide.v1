# 라벨링 시스템 가이드

## 개요

EcoGuide.v1의 **라벨링 시스템**은 사용자가 확인한 이미지 분석 결과를 학습 데이터로 자동 저장하고, 이를 관리자가 조회할 수 있도록 지원합니다.

## 목적

- **학습 데이터 수집**: 확인된 폐기물 분류와 크기 정보를 구조화된 형태로 저장
- **향후 모델 개선**: 수집된 데이터를 이용하여 이미지 분석 모델 재학습
- **분류별 관리**: 카테고리별로 라벨링된 데이터를 효율적으로 검색 및 관리

## 아키텍처

### 1. LabelingService (`src/domains/analysis/services/labeling_service.py`)

라벨링 데이터의 저장 및 관리를 담당하는 핵심 서비스입니다.

**주요 기능:**
- 이미지 파일 저장 (`/uploads/user_images/{uuid}.jpg`)
- JSON 라벨 메타데이터 저장 (`/uploads/labels/{uuid}.json`)
- 라벨 인덱스 관리 (`/uploads/labels/_index.json`)
- 카테고리별 라벨 조회

**핵심 메서드:**

```python
# 라벨 저장
def save_label(
    image_bytes: bytes,
    analysis_result: Dict[str, Any],
    user_feedback: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]

# 통계 조회
def get_category_statistics() -> Dict[str, Any]

# 주 카테고리별 라벨 조회
def get_labels_by_primary_category(primary_category: str) -> List[Dict[str, Any]]

# 세부 카테고리별 라벨 조회
def get_labels_by_secondary_category(
    primary_category: str,
    secondary_category: str
) -> List[Dict[str, Any]]

# 라벨 상세 정보 조회
def get_label_details(file_id: str) -> Optional[Dict[str, Any]]
```

### 2. CompleteStep의 라벨링 통합 (`app_new.py`)

Step 4 (분류 완료)에서 자동으로 라벨링 데이터를 저장합니다.

```python
# 라벨링 서비스를 통해 학습 데이터로 저장
labeling_service = self.app_context.get_service('labeling_service')
if labeling_service and image_bytes:
    label_result = labeling_service.save_label(
        image_bytes=image_bytes,
        analysis_result=normalized,
        user_feedback=normalized.get('user_feedback', {})
    )
```

### 3. 관리자 대시보드 (`pages/admin_labeling_dashboard.py`)

라벨링 데이터를 조회하고 관리하는 Streamlit 페이지입니다.

## 데이터 구조

### 라벨 JSON 파일 (`/uploads/labels/{uuid}.json`)

```json
{
  "file_id": "d686bcdb-7e8c-47df-b986-6d48a88babc1",
  "image_path": "/uploads/user_images/d686bcdb-7e8c-47df-b986-6d48a88babc1.jpg",
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
  "reasoning": "분석 근거 텍스트",
  "user_feedback": {
    "notes": "사용자 피드백",
    "timestamp": "2025-10-26T20:04:16"
  },
  "metadata": {
    "labeling_quality": 0.98
  }
}
```

### 인덱스 JSON 파일 (`/uploads/labels/_index.json`)

```json
{
  "version": "1.0",
  "created_at": "2025-10-26T20:04:16.109684",
  "total_labels": 100,
  "labels_by_category": {
    "FURN": {
      "count": 30,
      "subcategories": {
        "FURN_BED": 15,
        "FURN_SOFA": 10,
        "FURN_TABLE": 5
      }
    },
    "APPL": {
      "count": 25,
      "subcategories": {
        "APPL_FRIDGE": 12,
        "APPL_WASH": 13
      }
    }
  },
  "labels": [
    {
      "file_id": "uuid",
      "timestamp": "2025-10-26T...",
      "primary_category": "FURN",
      "secondary_category": "FURN_BED",
      "object_name": "침대",
      "confidence": 0.95,
      "labeling_quality": 0.98
    }
  ]
}
```

## 워크플로우

### 1. 사용자가 분류를 확인할 때

```
[이미지 분석]
    ↓
[분류 확인 (Step 3)]
    ↓
[제출 (Step 4)]
    ↓
[LabelingService.save_label()]
    ├── 이미지 저장: /uploads/user_images/{uuid}.jpg
    ├── 라벨 저장: /uploads/labels/{uuid}.json
    └── 인덱스 업데이트: /uploads/labels/_index.json
    ↓
["📊 학습 데이터로 저장되었습니다" 메시지 표시]
```

### 2. 관리자가 데이터를 조회할 때

```
[관리자 대시보드 열기]
    ↓
[카테고리 선택]
    ├── 주 카테고리 (8개): FURN, APPL, HLTH, LIFE, SPOR, MUSC, HOBB, MISC
    └── 세부 카테고리 (선택사항)
    ↓
[라벨링 데이터 표시]
    ├── 이미지 그리드 뷰
    ├── 분류 및 신뢰도 정보
    └── 상세 정보 조회 옵션
```

## 관리자 대시보드 사용법

### 탭 1: 📈 통계
- 전체 라벨링 데이터 개수
- 마지막 업데이트 시간
- 카테고리별 분포 (테이블 및 차트)

### 탭 2: 🏷️ 데이터 조회
1. **주 카테고리 선택**: 8개 주 카테고리 중 선택
2. **세부 카테고리 선택** (선택사항): 해당 주 카테고리의 세부 항목 선택
3. **결과 표시**: 조건에 맞는 이미지와 정보를 3열 그리드로 표시
4. **상세 보기**: "📋 상세 보기" 버튼으로 개별 라벨 상세 정보 확인

### 탭 3: 📋 상세 정보
1. **파일 ID 입력**: UUID 입력 (또는 탭 2에서 상세 보기 클릭)
2. **검색**: 🔍 검색 버튼 클릭
3. **정보 표시**:
   - 분석 이미지 표시
   - 분류, 신뢰도, 크기 정보 표시
   - 판단 근거 및 사용자 피드백 표시
   - 원본 JSON 확인 가능

## 파일 구조

```
uploads/
├── user_images/              # 라벨링된 이미지 저장
│   ├── {uuid}.jpg
│   ├── {uuid}.jpg
│   └── ...
├── labels/                   # 라벨 메타데이터 저장
│   ├── _index.json          # 라벨 인덱스 (모든 라벨 목록)
│   ├── {uuid}.json          # 개별 라벨 메타데이터
│   ├── {uuid}.json
│   └── ...
├── districts/
├── monitoring/
└── waste_types/
```

## 서비스 등록

LabelingService는 ServiceFactory에 자동으로 등록됩니다.

```python
# service_factory.py의 SERVICE_DOMAIN_MAP
SERVICE_DOMAIN_MAP = {
    ...
    'labeling_service': 'analysis',  # LabelingService 등록
    ...
}
```

## 라벨링 품질 점수 계산

라벨링 품질은 0.0 ~ 1.0 범위의 점수로 계산됩니다:

- **신뢰도** (40%): AI의 분석 신뢰도
- **크기 정보** (30%): 차원 정보 포함 여부
- **사용자 피드백** (30%): 사용자가 추가 메모를 입력했는지

```python
score = 0.0
score += min(confidence, 1.0) * 0.4       # 신뢰도
score += 0.3 if dimensions_exist else 0    # 크기 정보
score += 0.3 if user_notes_exist else 0    # 사용자 피드백
```

## 사용 예시

### 라벨 저장

```python
labeling_service = app_context.get_service('labeling_service')

result = labeling_service.save_label(
    image_bytes=image_bytes,
    analysis_result={
        'object_name': '침대',
        'primary_category': 'FURN',
        'secondary_category': 'FURN_BED',
        'confidence': 0.95,
        'dimensions': {
            'width_cm': 200,
            'height_cm': 120,
            'depth_cm': 30,
            'dimension_sum_cm': 350
        }
    },
    user_feedback={'notes': '정확한 분류입니다'}
)

print(f"저장 성공: {result['success']}")
print(f"파일 ID: {result['file_id']}")
```

### 통계 조회

```python
stats = labeling_service.get_category_statistics()
print(f"총 라벨: {stats['total_labels']}")
print(f"카테고리별: {stats['by_primary_category']}")
```

### 카테고리별 라벨 조회

```python
# 가구 카테고리의 모든 라벨
furniture_labels = labeling_service.get_labels_by_primary_category('FURN')

# 침대 카테고리의 라벨
bed_labels = labeling_service.get_labels_by_secondary_category('FURN', 'FURN_BED')
```

## 향후 확장

- **데이터 내보내기**: CSV/Excel 형식으로 라벨링 데이터 내보내기
- **데이터 검증**: 라벨 품질 자동 검증 및 필터링
- **모델 학습**: 저장된 데이터를 이용한 모델 재학습 파이프라인
- **데이터 버전 관리**: 시간 경과에 따른 데이터 버전 추적
- **다중 모델 평가**: 여러 모델의 성능 비교 분석
