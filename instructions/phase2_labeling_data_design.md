# Phase 2: 라벨링 데이터 저장소 설계서

## 🎯 목적 및 범위

### 핵심 목적
사용자가 업로드한 이미지와 분석 결과, 피드백 데이터를 체계적으로 저장하여 **독립적인 이미지 분석 모델 학습용 고품질 데이터셋** 구축

### 비즈니스 가치
- **장기적 모델 개선**: 실제 사용 데이터 기반 독립 AI 모델 학습
- **데이터 자산화**: 고품질 라벨링 데이터셋을 통한 기술 경쟁력 확보
- **연구 개발 기반**: 지속적인 알고리즘 개선 및 새로운 기능 개발 지원

### 구현 범위
- ✅ 원본 + 배경제거 이미지 저장
- ✅ 이미지 메타데이터 관리
- ✅ 사용자 피드백 연계 저장
- ✅ 학습용 데이터셋 자동 생성
- ✅ 데이터 품질 관리 시스템
- ✅ COCO/YOLO 포맷 지원

## 🔗 기존 시스템 연계점

### 주요 의존성
```python
# Phase 1 연계 (권장)
- FeedbackService: 사용자 피드백 데이터
- AccuracyTrackingService: 품질 검증 데이터

# 기존 시스템 연계
- VisionService: 이미지 분석 결과 (배경제거 포함)
- SessionState: 사용자 세션 정보
```

### 독립 실행 가능성
```python
# Phase 1 없이도 구현 가능
- 기본 이미지 + 분석 결과만으로 데이터셋 생성
- 피드백 데이터는 선택적 보강 요소
```

## 🏗️ 시스템 아키텍처

### 컴포넌트 구조
```
src/
├── domains/
│   └── infrastructure/
│       └── services/
│           ├── labeling_data_service.py     # 라벨링 데이터 관리
│           ├── image_metadata_service.py    # 이미지 메타데이터 관리
│           ├── dataset_manager_service.py   # 데이터셋 생성 관리
│           └── data_quality_service.py      # 데이터 품질 관리
└── pages/
    └── dataset_manager.py                   # 데이터셋 관리 대시보드 (선택적)
```

### 데이터 저장 구조
```
data/
├── images/
│   ├── original/                    # 원본 이미지
│   │   └── 2024/
│   │       └── 01/
│   │           └── 15/
│   │               ├── img_001.jpg
│   │               └── img_002.jpg
│   ├── background_removed/          # 배경제거 이미지
│   │   └── 2024/01/15/
│   │       ├── img_001_nobg.jpg
│   │       └── img_002_nobg.jpg
│   └── annotated/                   # 어노테이션 오버레이 (시각화용)
│       └── 2024/01/15/
│           ├── img_001_annotated.jpg
│           └── img_002_annotated.jpg
├── metadata/
│   ├── annotations.json             # 전체 어노테이션 정보
│   ├── datasets/                    # 생성된 데이터셋 메타데이터
│   │   ├── dataset_v1_0.json
│   │   └── dataset_v1_1.json
│   └── quality_reports/             # 품질 검사 보고서
│       └── 2024_01_quality.json
└── exports/
    ├── coco_format/                 # COCO 포맷 데이터셋
    │   ├── train/
    │   ├── val/
    │   └── test/
    ├── yolo_format/                 # YOLO 포맷 데이터셋
    │   ├── images/
    │   └── labels/
    └── custom/                      # 커스텀 포맷
        └── ecoguide_v1/
```

## 📋 세부 기능 설계

### 1. LabelingDataService

```python
# src/domains/infrastructure/services/labeling_data_service.py
from src.app.core.base_service import BaseService
from typing import Dict, Any, Optional, List
import os
import uuid
import json
from datetime import datetime
from PIL import Image

class LabelingDataService(BaseService):
    """라벨링 데이터 저장 및 관리 서비스"""

    def __init__(self, config):
        super().__init__(config)
        self.data_root = config.get('data_storage_path', './data')
        self.ensure_directory_structure()

    def save_analysis_data(self,
                          original_image: Image.Image,
                          vision_result: dict,
                          user_feedback: dict = None,
                          session_info: dict = None) -> dict:
        """분석 데이터 통합 저장"""

        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now()

        try:
            # 1. 이미지 파일 저장
            image_paths = self._save_image_files(
                analysis_id, original_image, vision_result, timestamp
            )

            # 2. 메타데이터 생성
            metadata = self._create_metadata(
                analysis_id, vision_result, user_feedback, session_info, timestamp
            )

            # 3. 어노테이션 정보 저장
            annotation_data = self._create_annotation_data(
                analysis_id, vision_result, image_paths, metadata
            )

            # 4. 데이터베이스 저장
            record_id = self._save_to_database(metadata, annotation_data)

            # 5. 품질 검증 (비동기)
            self._schedule_quality_check(analysis_id, record_id)

            return {
                'success': True,
                'analysis_id': analysis_id,
                'record_id': record_id,
                'image_paths': image_paths,
                'metadata': metadata
            }

        except Exception as e:
            self.logger.error(f"Failed to save analysis data: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis_id': analysis_id
            }

    def _save_image_files(self,
                         analysis_id: str,
                         original_image: Image.Image,
                         vision_result: dict,
                         timestamp: datetime) -> dict:
        """이미지 파일들을 날짜별 디렉토리에 저장"""

        date_path = timestamp.strftime("%Y/%m/%d")

        # 디렉토리 생성
        original_dir = os.path.join(self.data_root, "images", "original", date_path)
        bg_removed_dir = os.path.join(self.data_root, "images", "background_removed", date_path)
        annotated_dir = os.path.join(self.data_root, "images", "annotated", date_path)

        os.makedirs(original_dir, exist_ok=True)
        os.makedirs(bg_removed_dir, exist_ok=True)
        os.makedirs(annotated_dir, exist_ok=True)

        # 파일명 생성
        base_filename = f"{analysis_id}"

        paths = {}

        # 1. 원본 이미지 저장
        original_path = os.path.join(original_dir, f"{base_filename}.jpg")
        original_image.save(original_path, "JPEG", quality=95)
        paths['original'] = original_path

        # 2. 배경제거 이미지 저장 (vision_result에 포함된 경우)
        if 'background_removed_image' in vision_result:
            bg_removed_path = os.path.join(bg_removed_dir, f"{base_filename}_nobg.jpg")
            vision_result['background_removed_image'].save(bg_removed_path, "JPEG", quality=95)
            paths['background_removed'] = bg_removed_path

        # 3. 어노테이션 오버레이 이미지 생성 및 저장
        if 'object_detection' in vision_result:
            annotated_image = self._create_annotated_image(original_image, vision_result)
            annotated_path = os.path.join(annotated_dir, f"{base_filename}_annotated.jpg")
            annotated_image.save(annotated_path, "JPEG", quality=95)
            paths['annotated'] = annotated_path

        return paths

    def _create_metadata(self,
                        analysis_id: str,
                        vision_result: dict,
                        user_feedback: dict,
                        session_info: dict,
                        timestamp: datetime) -> dict:
        """메타데이터 생성"""

        metadata = {
            'analysis_id': analysis_id,
            'timestamp': timestamp.isoformat(),
            'version': '1.0',

            # 이미지 정보
            'image_info': {
                'width': vision_result.get('image_width', 0),
                'height': vision_result.get('image_height', 0),
                'format': 'JPEG',
                'has_background_removal': 'background_removed_image' in vision_result
            },

            # 분석 결과
            'analysis_result': {
                'detected_category': vision_result.get('category', ''),
                'confidence': vision_result.get('confidence', 0.0),
                'bbox': vision_result.get('bbox', {}),
                'size_estimation': vision_result.get('size_estimation', {}),
                'hand_detection': vision_result.get('hand_detection', {})
            },

            # 사용자 피드백 (있는 경우)
            'user_feedback': user_feedback or {},

            # 세션 정보
            'session_info': session_info or {},

            # 품질 정보
            'quality_info': {
                'initial_quality_score': self._calculate_initial_quality(vision_result),
                'has_user_feedback': user_feedback is not None,
                'feedback_quality': self._assess_feedback_quality(user_feedback) if user_feedback else None
            }
        }

        return metadata

    def _create_annotation_data(self,
                              analysis_id: str,
                              vision_result: dict,
                              image_paths: dict,
                              metadata: dict) -> dict:
        """COCO 형식 어노테이션 데이터 생성"""

        # COCO 형식 기본 구조
        annotation_data = {
            'info': {
                'description': 'EcoGuide Large Waste Classification Dataset',
                'version': '1.0',
                'year': datetime.now().year,
                'contributor': 'EcoGuide.v1',
                'date_created': datetime.now().isoformat()
            },
            'images': [{
                'id': analysis_id,
                'file_name': os.path.basename(image_paths.get('original', '')),
                'width': metadata['image_info']['width'],
                'height': metadata['image_info']['height'],
                'date_captured': metadata['timestamp']
            }],
            'annotations': [],
            'categories': self._get_category_mapping()
        }

        # 객체 검출 결과를 어노테이션으로 변환
        if 'object_detection' in vision_result:
            obj_detection = vision_result['object_detection']

            annotation = {
                'id': f"{analysis_id}_obj",
                'image_id': analysis_id,
                'category_id': self._get_category_id(obj_detection.get('label', '')),
                'bbox': self._convert_bbox_to_coco(obj_detection.get('bbox', {})),
                'area': self._calculate_bbox_area(obj_detection.get('bbox', {})),
                'iscrowd': 0,
                'segmentation': [],  # 현재는 bbox만 지원
                'confidence': obj_detection.get('confidence', 0.0),

                # 추가 메타데이터
                'size_estimation': vision_result.get('size_estimation', {}),
                'user_correction': self._extract_user_corrections(metadata.get('user_feedback', {}))
            }

            annotation_data['annotations'].append(annotation)

        return annotation_data

    def get_dataset_statistics(self, date_range: tuple = None) -> dict:
        """데이터셋 통계 조회"""

        # 데이터베이스 쿼리로 통계 계산
        stats = {
            'total_images': 0,
            'total_annotations': 0,
            'category_distribution': {},
            'quality_distribution': {
                'high_quality': 0,      # 피드백 있고 정확한 데이터
                'medium_quality': 0,    # 피드백 있거나 높은 신뢰도
                'low_quality': 0        # 기본 분석 결과만
            },
            'feedback_coverage': 0.0,   # 피드백이 있는 데이터 비율
            'latest_data_date': None,
            'storage_usage': self._calculate_storage_usage()
        }

        return stats
```

### 2. DatasetManagerService

```python
# src/domains/infrastructure/services/dataset_manager_service.py
class DatasetManagerService(BaseService):
    """데이터셋 생성 및 관리 서비스"""

    def create_training_dataset(self,
                              name: str,
                              version: str,
                              criteria: dict) -> dict:
        """학습용 데이터셋 생성"""

        dataset_id = f"{name}_v{version}"

        try:
            # 1. 데이터 필터링
            filtered_data = self._filter_data_by_criteria(criteria)

            # 2. 데이터 분할 (train/val/test)
            splits = self._split_dataset(
                filtered_data,
                train_ratio=criteria.get('train_ratio', 0.7),
                val_ratio=criteria.get('val_ratio', 0.2),
                test_ratio=criteria.get('test_ratio', 0.1)
            )

            # 3. 데이터셋 메타데이터 생성
            dataset_metadata = self._create_dataset_metadata(
                dataset_id, name, version, criteria, splits
            )

            # 4. 다양한 포맷으로 내보내기
            export_results = {}

            if criteria.get('export_coco', True):
                export_results['coco'] = self._export_coco_format(dataset_id, splits)

            if criteria.get('export_yolo', True):
                export_results['yolo'] = self._export_yolo_format(dataset_id, splits)

            if criteria.get('export_custom', False):
                export_results['custom'] = self._export_custom_format(dataset_id, splits)

            # 5. 데이터셋 등록
            self._register_dataset(dataset_metadata, export_results)

            return {
                'success': True,
                'dataset_id': dataset_id,
                'metadata': dataset_metadata,
                'export_paths': export_results,
                'statistics': self._generate_dataset_statistics(splits)
            }

        except Exception as e:
            self.logger.error(f"Failed to create dataset {dataset_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'dataset_id': dataset_id
            }

    def _filter_data_by_criteria(self, criteria: dict) -> List[dict]:
        """기준에 따른 데이터 필터링"""

        filters = []

        # 날짜 범위
        if criteria.get('date_range'):
            start_date, end_date = criteria['date_range']
            filters.append(f"timestamp BETWEEN '{start_date}' AND '{end_date}'")

        # 최소 신뢰도
        min_confidence = criteria.get('min_confidence', 0.5)
        filters.append(f"(metadata->>'analysis_result'->'confidence')::float >= {min_confidence}")

        # 피드백 있는 데이터만
        if criteria.get('feedback_only', False):
            filters.append("user_feedback IS NOT NULL")

        # 특정 카테고리만
        if criteria.get('categories'):
            categories = "', '".join(criteria['categories'])
            filters.append(f"metadata->>'analysis_result'->>'detected_category' IN ('{categories}')")

        # 품질 등급
        if criteria.get('min_quality_grade'):
            quality_grades = {
                'high': 3,
                'medium': 2,
                'low': 1
            }
            min_grade = quality_grades.get(criteria['min_quality_grade'], 1)
            filters.append(f"quality_grade >= {min_grade}")

        # SQL 쿼리 실행
        where_clause = " AND ".join(filters) if filters else "1=1"

        # 실제 데이터베이스 쿼리 로직
        # return self._execute_query(where_clause)

        return []  # 임시

    def _export_coco_format(self, dataset_id: str, splits: dict) -> dict:
        """COCO 포맷으로 데이터셋 내보내기"""

        export_path = os.path.join(self.data_root, "exports", "coco_format", dataset_id)
        os.makedirs(export_path, exist_ok=True)

        results = {}

        for split_name, data_list in splits.items():
            split_path = os.path.join(export_path, split_name)
            os.makedirs(split_path, exist_ok=True)

            # COCO JSON 파일 생성
            coco_data = {
                'info': {
                    'description': f'EcoGuide Dataset {dataset_id} - {split_name} split',
                    'version': '1.0',
                    'year': datetime.now().year,
                    'contributor': 'EcoGuide.v1',
                    'date_created': datetime.now().isoformat()
                },
                'images': [],
                'annotations': [],
                'categories': self._get_category_mapping()
            }

            # 이미지 복사 및 어노테이션 변환
            for idx, data_item in enumerate(data_list):
                # 이미지 파일 복사
                original_path = data_item['image_paths']['original']
                new_filename = f"{split_name}_{idx:06d}.jpg"
                new_path = os.path.join(split_path, new_filename)

                # 파일 복사 (또는 심볼릭 링크)
                import shutil
                shutil.copy2(original_path, new_path)

                # COCO 이미지 정보 추가
                coco_data['images'].append({
                    'id': idx,
                    'file_name': new_filename,
                    'width': data_item['metadata']['image_info']['width'],
                    'height': data_item['metadata']['image_info']['height']
                })

                # COCO 어노테이션 추가
                if data_item['annotation_data']['annotations']:
                    for ann in data_item['annotation_data']['annotations']:
                        ann_copy = ann.copy()
                        ann_copy['image_id'] = idx
                        ann_copy['id'] = len(coco_data['annotations'])
                        coco_data['annotations'].append(ann_copy)

            # JSON 파일 저장
            json_path = os.path.join(split_path, f"{split_name}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, ensure_ascii=False, indent=2)

            results[split_name] = {
                'path': split_path,
                'json_file': json_path,
                'image_count': len(data_list),
                'annotation_count': len(coco_data['annotations'])
            }

        return results
```

### 3. DataQualityService

```python
# src/domains/infrastructure/services/data_quality_service.py
class DataQualityService(BaseService):
    """데이터 품질 관리 서비스"""

    def assess_data_quality(self, analysis_record: dict) -> dict:
        """데이터 품질 평가"""

        quality_scores = {}

        # 1. 이미지 품질 평가
        quality_scores['image_quality'] = self._assess_image_quality(analysis_record)

        # 2. 분석 결과 품질 평가
        quality_scores['analysis_quality'] = self._assess_analysis_quality(analysis_record)

        # 3. 피드백 품질 평가 (있는 경우)
        if analysis_record.get('user_feedback'):
            quality_scores['feedback_quality'] = self._assess_feedback_quality(analysis_record)

        # 4. 종합 품질 점수 계산
        overall_score = self._calculate_overall_quality_score(quality_scores)

        # 5. 품질 등급 결정
        quality_grade = self._determine_quality_grade(overall_score)

        return {
            'overall_score': overall_score,
            'quality_grade': quality_grade,  # 'high', 'medium', 'low'
            'detailed_scores': quality_scores,
            'recommendations': self._generate_quality_recommendations(quality_scores),
            'usable_for_training': overall_score >= 0.6
        }

    def _assess_image_quality(self, record: dict) -> float:
        """이미지 품질 평가"""

        # 기본 점수
        score = 0.5

        image_info = record.get('metadata', {}).get('image_info', {})

        # 해상도 점수
        width = image_info.get('width', 0)
        height = image_info.get('height', 0)

        if width >= 800 and height >= 600:
            score += 0.2
        elif width >= 400 and height >= 300:
            score += 0.1

        # 배경 제거 가능 여부
        if image_info.get('has_background_removal'):
            score += 0.1

        # 추가적인 이미지 품질 지표들...
        # (흐림 정도, 조명 상태, 노이즈 등은 추후 구현)

        return min(score, 1.0)

    def _assess_analysis_quality(self, record: dict) -> float:
        """분석 결과 품질 평가"""

        analysis_result = record.get('metadata', {}).get('analysis_result', {})

        # 신뢰도 기반 점수
        confidence = analysis_result.get('confidence', 0.0)

        # 바운딩 박스 품질 (크기, 위치의 합리성)
        bbox_quality = self._assess_bbox_quality(analysis_result.get('bbox', {}))

        # 크기 추정 품질 (손 검출 성공 여부 등)
        size_quality = self._assess_size_estimation_quality(analysis_result.get('size_estimation', {}))

        return (confidence * 0.5 + bbox_quality * 0.3 + size_quality * 0.2)

    def generate_quality_report(self, period: str = 'weekly') -> dict:
        """품질 보고서 생성"""

        # 기간별 데이터 품질 통계
        report = {
            'period': period,
            'summary': {
                'total_records': 0,
                'high_quality_count': 0,
                'medium_quality_count': 0,
                'low_quality_count': 0,
                'average_quality_score': 0.0
            },
            'trends': {
                'quality_improvement': 0.0,
                'feedback_coverage_trend': 0.0
            },
            'recommendations': [],
            'detailed_analysis': {}
        }

        return report
```

## 🗄️ 데이터베이스 스키마

### 라벨링 데이터 관련 테이블

```sql
-- 라벨링 데이터 메인 테이블
CREATE TABLE labeling_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 식별 정보
    analysis_id TEXT UNIQUE NOT NULL,
    session_id TEXT,

    -- 이미지 파일 경로
    original_image_path TEXT NOT NULL,
    background_removed_path TEXT,
    annotated_image_path TEXT,

    -- 메타데이터 (JSON)
    metadata JSONB NOT NULL,
    annotation_data JSONB NOT NULL,

    -- 품질 정보
    quality_score FLOAT DEFAULT 0.0,
    quality_grade TEXT DEFAULT 'medium', -- 'high', 'medium', 'low'
    quality_assessment JSONB,

    -- 연결 정보
    feedback_id UUID, -- user_feedback 테이블과 연결

    -- 사용 여부
    is_active BOOLEAN DEFAULT TRUE,
    is_training_ready BOOLEAN DEFAULT FALSE,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 데이터셋 관리 테이블
CREATE TABLE training_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    dataset_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,

    -- 데이터셋 정보
    description TEXT,
    creation_criteria JSONB NOT NULL,

    -- 통계 정보
    total_images INTEGER DEFAULT 0,
    train_images INTEGER DEFAULT 0,
    val_images INTEGER DEFAULT 0,
    test_images INTEGER DEFAULT 0,

    -- 분포 정보
    category_distribution JSONB,
    quality_distribution JSONB,

    -- 파일 정보
    export_paths JSONB, -- 각 포맷별 경로
    file_size_mb FLOAT DEFAULT 0.0,

    -- 상태
    status TEXT DEFAULT 'created', -- 'created', 'processing', 'ready', 'archived'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system'
);

-- 데이터셋 구성 요소 테이블 (다대다 관계)
CREATE TABLE dataset_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    dataset_id UUID REFERENCES training_datasets(id) ON DELETE CASCADE,
    labeling_data_id UUID REFERENCES labeling_data(id) ON DELETE CASCADE,

    split_type TEXT NOT NULL, -- 'train', 'val', 'test'
    item_index INTEGER NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(dataset_id, labeling_data_id)
);

-- 품질 검사 이력 테이블
CREATE TABLE quality_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    labeling_data_id UUID REFERENCES labeling_data(id) ON DELETE CASCADE,

    check_type TEXT NOT NULL, -- 'initial', 'periodic', 'manual'
    check_version TEXT DEFAULT '1.0',

    quality_scores JSONB NOT NULL,
    issues_found JSONB,
    recommendations JSONB,

    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checked_by TEXT DEFAULT 'system'
);
```

### 인덱스 최적화

```sql
-- 성능 최적화 인덱스
CREATE INDEX idx_labeling_data_analysis_id ON labeling_data(analysis_id);
CREATE INDEX idx_labeling_data_quality_grade ON labeling_data(quality_grade);
CREATE INDEX idx_labeling_data_training_ready ON labeling_data(is_training_ready);
CREATE INDEX idx_labeling_data_created_at ON labeling_data(created_at);
CREATE INDEX idx_datasets_status ON training_datasets(status);
CREATE INDEX idx_dataset_items_split ON dataset_items(split_type);
CREATE INDEX idx_quality_checks_data_id ON quality_checks(labeling_data_id);
```

## 🚀 구현 가이드

### 1단계: 기본 구조 구축 (1-2일)

```bash
# 1. 서비스 클래스 생성
mkdir -p src/domains/infrastructure/services
touch src/domains/infrastructure/services/labeling_data_service.py
touch src/domains/infrastructure/services/dataset_manager_service.py
touch src/domains/infrastructure/services/data_quality_service.py

# 2. 데이터 디렉토리 구조 생성
mkdir -p data/{images/{original,background_removed,annotated},metadata/{datasets,quality_reports},exports/{coco_format,yolo_format,custom}}

# 3. 데이터베이스 스키마 적용
```

### 2단계: 핵심 저장 기능 구현 (3-4일)

```python
# ServiceFactory에 새 서비스들 등록
registry.register_service(
    name='labeling_data_service',
    service_class=type('LabelingDataService', (), {}),
    module_path='src.domains.infrastructure.services.labeling_data_service',
    dependencies=[],
    is_optional=False,
    singleton=True
)
```

### 3단계: 데이터셋 생성 기능 구현 (2-3일)

```python
# 기존 이미지 분석 플로우에 데이터 저장 추가
# camera_analysis.py 또는 해당 분석 페이지에서

from src.domains.infrastructure.services.labeling_data_service import LabelingDataService

# 분석 완료 후
if vision_result and vision_result.success:
    # 기존 결과 표시...

    # 라벨링 데이터 저장
    labeling_service = get_service('labeling_data_service')

    save_result = labeling_service.save_analysis_data(
        original_image=uploaded_image,
        vision_result=vision_result.to_dict(),
        user_feedback=st.session_state.get('latest_feedback'),
        session_info={
            'session_id': st.session_state.get('session_id'),
            'user_agent': st.context.headers.get('user-agent'),
            'timestamp': datetime.now().isoformat()
        }
    )

    if save_result['success']:
        st.info(f"🗄️ 분석 데이터가 저장되었습니다 (ID: {save_result['analysis_id'][:8]}...)")
```

### 4단계: 데이터셋 관리 대시보드 (선택사항, 2-3일)

```python
# src/pages/dataset_manager.py
def render_dataset_dashboard():
    """데이터셋 관리 대시보드"""

    st.title("📊 라벨링 데이터 & 데이터셋 관리")

    # 탭으로 기능 분리
    tab1, tab2, tab3 = st.tabs(["📈 데이터 현황", "🎯 데이터셋 생성", "🔍 품질 관리"])

    with tab1:
        render_data_statistics()

    with tab2:
        render_dataset_creation()

    with tab3:
        render_quality_management()

def render_dataset_creation():
    """데이터셋 생성 인터페이스"""

    st.subheader("🎯 새 데이터셋 생성")

    with st.form("create_dataset"):
        # 기본 정보
        name = st.text_input("데이터셋 이름", "ecoguide_waste_classification")
        version = st.text_input("버전", "1.0")
        description = st.text_area("설명", "대형폐기물 분류 학습용 데이터셋")

        # 필터링 조건
        st.subheader("데이터 선택 조건")

        col1, col2 = st.columns(2)
        with col1:
            date_range = st.date_input("데이터 수집 기간", value=[])
            min_confidence = st.slider("최소 신뢰도", 0.0, 1.0, 0.5)

        with col2:
            feedback_only = st.checkbox("피드백이 있는 데이터만")
            categories = st.multiselect("포함할 카테고리", ["의자", "테이블", "소파", "기타"])

        # 데이터 분할 비율
        st.subheader("데이터 분할")
        col1, col2, col3 = st.columns(3)
        with col1:
            train_ratio = st.number_input("학습", 0.1, 0.9, 0.7)
        with col2:
            val_ratio = st.number_input("검증", 0.1, 0.9, 0.2)
        with col3:
            test_ratio = st.number_input("테스트", 0.1, 0.9, 0.1)

        # 내보내기 형식
        st.subheader("내보내기 형식")
        export_coco = st.checkbox("COCO 형식", True)
        export_yolo = st.checkbox("YOLO 형식", True)
        export_custom = st.checkbox("커스텀 형식", False)

        submitted = st.form_submit_button("데이터셋 생성")

        if submitted:
            # 검증
            if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.01:
                st.error("데이터 분할 비율의 합이 1.0이 되어야 합니다.")
                return

            # 데이터셋 생성
            dataset_manager = get_service('dataset_manager_service')

            criteria = {
                'date_range': date_range if date_range else None,
                'min_confidence': min_confidence,
                'feedback_only': feedback_only,
                'categories': categories,
                'train_ratio': train_ratio,
                'val_ratio': val_ratio,
                'test_ratio': test_ratio,
                'export_coco': export_coco,
                'export_yolo': export_yolo,
                'export_custom': export_custom
            }

            with st.spinner("데이터셋 생성 중..."):
                result = dataset_manager.create_training_dataset(name, version, criteria)

            if result['success']:
                st.success(f"✅ 데이터셋 '{name} v{version}'이 성공적으로 생성되었습니다!")
                st.json(result['statistics'])
            else:
                st.error(f"❌ 데이터셋 생성 실패: {result['error']}")
```

## 📊 성공 지표 및 모니터링

### 핵심 KPI
1. **데이터 수집량**: 월 1,000개 이상의 라벨링 데이터
2. **데이터 품질**: 고품질 데이터 비율 > 60%
3. **피드백 연계율**: 피드백이 있는 데이터 > 40%
4. **데이터셋 생성 효율**: 자동화율 > 95%

### 모니터링 대시보드
- 일별/월별 데이터 수집 현황
- 카테고리별 분포 및 품질 현황
- 데이터셋 생성 이력 및 사용 현황
- 저장공간 사용량 및 최적화 제안

## 🔮 다음 Phase 연계점

### Phase 1 (피드백) 연계 강화
```python
# 더 정확한 라벨링을 위한 피드백 활용
- 사용자 수정 정보 → 정확한 어노테이션
- 품질 평가 → 피드백 신뢰도 반영
- 패턴 분석 → 공통 오류 탐지
```

### Phase 4 (프롬프트 최적화) 연계
```python
# 라벨링 데이터를 프롬프트 개선에 활용
- 오분류 패턴 → 프롬프트 보완 포인트
- 성공 사례 → 설명 개선 방향
- 데이터 분포 → 균형있는 학습 전략
```

## 💡 구현 팁

1. **점진적 저장**: 초기에는 기본 정보만 저장하고 점차 메타데이터 확장
2. **비동기 처리**: 이미지 저장과 품질 검사는 백그라운드에서 처리
3. **저장공간 최적화**: 중복 이미지 제거, 압축 최적화
4. **백업 전략**: 중요한 라벨링 데이터의 정기적 백업 및 버전 관리

이 Phase 2는 **Phase 1과 연계하여 더 큰 가치**를 제공하며, 장기적으로 독립 AI 모델 개발의 핵심 기반이 됩니다.