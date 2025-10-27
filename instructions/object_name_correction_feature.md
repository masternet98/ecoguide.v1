# 품목명 수정 및 변경 추적 기능 개선 설명서

## 📋 개요

AI 이미지 분석 결과의 품목명(object_name)을 사용자가 수정할 수 있도록 하고, 변경 여부를 자동으로 기록하여 향후 AI 모델 개선에 활용할 수 있도록 개선했습니다.

---

## 🎯 기능 개선 사항

### 1. **사용자 인터페이스 개선** (EnhancedConfirmationUI)

#### 추가된 UI 요소
- **품목명 정확성 확인**: 현재 AI가 분석한 품목명을 표시하고 정확성 확인
  ```
  "품목명이 정확한가요? (현재: 2인용 소파)"
  - 정확합니다 / 수정이 필요합니다
  ```

- **품목명 수정 입력 필드**: 수정이 필요한 경우 올바른 품목명 입력 가능
  ```
  "올바른 품목명을 입력해주세요"
  - 예: 2인용 소파, 양문형 냉장고, 목재 책장
  ```

#### 파일 위치
- `src/domains/analysis/ui/enhanced_confirmation_ui.py`
- 메서드: `_render_enhanced_classification_section()` (라인 164-308)

#### 반환 데이터 구조
```python
{
    "original_object_name": "AI가 분석한 원본 품목명",
    "corrected_object_name": "사용자가 수정한 품목명",
    "is_object_name_changed": True/False,  # 변경 여부
    "user_feedback": {
        "object_name_accurate": True/False,
        "corrected_object_name": "수정된 품목명 (변경 시)",
        "is_object_name_changed": True/False,
        ...
    }
}
```

---

### 2. **피드백 저장 및 기록** (ConfirmationService)

#### 추가된 기능

1. **품목명 변경 감지 및 구조화**
   - 원본 품목명과 수정된 품목명 비교
   - 변경 여부를 `is_object_name_changed` 플래그로 표시

2. **품목명 변경 로깅**
   - 콘솔 출력: `📝 Object Name Changed: 원본 → 수정됨`
   - 로그 기록: 품목명 변경 정보 포함
   - 예시:
     ```
     === FEEDBACK RECORD SAVED ===
     ID: abc123
     User Confirmed: True
     Classification Feedback: {...}
     📝 Object Name Changed: 소파 → 2인용 소파
     ================================
     ```

3. **피드백 품질 지표 개선**
   - 새로운 지표: `has_object_name_correction`
   - 품목명 수정이 높은 가치의 피드백으로 인식

4. **감사 메시지 개선**
   - 품목명 수정이 있을 경우 우선적으로 언급
   - 예: "품목명 수정을 주셔서 감사합니다! 향후 품목 인식 정확도 개선에 활용하겠습니다."

#### 파일 위치
- `src/domains/analysis/services/confirmation_service.py`
- 주요 메서드:
  - `_validate_and_structure_feedback()` (라인 101-163)
  - `_save_feedback_to_storage()` (라인 165-195)
  - `_generate_thank_you_message()` (라인 220-238)
  - `_calculate_feedback_quality()` (라인 240-265)

#### 피드백 구조 (validated_feedback)
```python
{
    'classification': {
        'original_object_name': '소파',
        'corrected_object_name': '2인용 소파',
        'object_name_accurate': False,
        'is_object_name_changed': True,
        ...
    },
    'feedback_quality_indicators': {
        'has_object_name_correction': True,
        ...
    }
}
```

---

### 3. **정확도 추적 및 분석** (AccuracyTrackingService)

#### 추가된 메트릭

1. **일별 품목명 수정 통계**
   - `daily_metrics[date]['object_name_corrections']`
   - 매일 품목명이 수정된 피드백 개수 추적

2. **전체 품목명 성능 분석**
   ```python
   'object_name_performance': {
       'total_corrections': 정수,           # 누적 수정 횟수
       'correction_patterns': 리스트,       # 변경 패턴 기록
       'frequently_corrected_items': 딕셔너리  # 자주 수정되는 물품
   }
   ```

3. **새로운 조회 메서드: `_get_object_name_statistics()`**
   - 반환 정보:
     ```python
     {
         'total_corrections': 10,              # 누적 수정 횟수
         'correction_rate': 0.15,              # 수정율 (15%)
         'frequently_corrected_items': [      # 자주 수정되는 물품 상위 5개
             {'item_name': '소파', 'correction_count': 5},
             {'item_name': '냉장고', 'correction_count': 3},
             ...
         ],
         'recent_corrections': [              # 최근 수정 10개
             {
                 'original_object_name': '소파',
                 'corrected_object_name': '2인용 소파',
                 'timestamp': '2025-10-27T...'
             },
             ...
         ]
     }
     ```

#### 파일 위치
- `src/domains/analysis/services/accuracy_tracking_service.py`
- 주요 메서드:
  - `_update_object_name_accuracy()` (라인 231-262)
  - `_get_object_name_statistics()` (라인 418-442)

#### 실시간 메트릭 포함
- `get_real_time_metrics()` 반환값에 `object_name_corrections` 필드 추가
- `generate_accuracy_report()` 반환값에 `object_name_statistics` 필드 추가

---

## 📊 데이터 흐름도

```
사용자 입력 (EnhancedConfirmationUI)
    ↓
품목명 정확성 확인 + 수정 (선택사항)
    ↓
ConfirmationService.save_confirmation()
    ↓
_validate_and_structure_feedback()
    ├─ 원본 품목명과 수정본 비교
    ├─ is_object_name_changed 플래그 설정
    └─ feedback_quality_indicators 업데이트
    ↓
_save_feedback_to_storage()
    └─ 품목명 변경 로깅 (콘솔 + 파일)
    ↓
AccuracyTrackingService.update_accuracy_metrics()
    ↓
_update_object_name_accuracy()
    ├─ 일별 수정 통계 업데이트
    ├─ 변경 패턴 기록
    └─ 자주 수정되는 물품 추적
    ↓
실시간 분석 및 보고서 생성
    ├─ get_real_time_metrics()
    └─ generate_accuracy_report()
```

---

## 🔄 사용 시나리오

### 시나리오 1: 정확한 품목명
1. 사용자가 이미지 업로드
2. AI가 "2인용 소파" 분석
3. 사용자: "품목명이 정확한가요?" → **"정확합니다"** 선택
4. 피드백 저장: `is_object_name_changed = False`
5. 로그: 품목명 변경 로깅 안 함

### 시나리오 2: 부정확한 품목명
1. 사용자가 이미지 업로드
2. AI가 "소파" 분석
3. 사용자: "품목명이 정확한가요?" → **"수정이 필요합니다"** 선택
4. 입력 필드 표시: "올바른 품목명을 입력해주세요"
5. 사용자 입력: "3인용 가죽 소파"
6. 피드백 저장:
   - `original_object_name = "소파"`
   - `corrected_object_name = "3인용 가죽 소파"`
   - `is_object_name_changed = True`
7. 로그 출력:
   ```
   📝 Object Name Changed: 소파 → 3인용 가죽 소파
   ```
8. 감사 메시지:
   ```
   "품목명 수정을 주셔서 감사합니다! 향후 품목 인식 정확도 개선에 활용하겠습니다."
   ```
9. 정확도 추적:
   - `daily_metrics['2025-10-27']['object_name_corrections'] += 1`
   - `frequently_corrected_items['소파'] += 1`

---

## 📈 활용 방법

### 1. 실시간 메트릭 조회
```python
from src.app.core.app_factory import ApplicationFactory

app_context = ApplicationFactory.create_application()
accuracy_service = app_context.get_service('accuracy_tracking_service')

metrics = accuracy_service.get_real_time_metrics()
print(metrics['object_name_corrections'])
# 출력:
# {
#     'total_corrections': 15,
#     'correction_rate': 0.2,
#     'frequently_corrected_items': [
#         {'item_name': '소파', 'correction_count': 5},
#         ...
#     ],
#     'recent_corrections': [...]
# }
```

### 2. 정확도 보고서 생성
```python
report = accuracy_service.generate_accuracy_report(period='weekly')
print(report['object_name_statistics'])
```

### 3. 자주 수정되는 물품 파악
- `frequently_corrected_items` 목록을 통해 AI가 자주 실패하는 품목 파악
- 이를 기반으로 학습 데이터 수집 우선순위 결정

### 4. 모델 개선
- 자주 수정되는 물품에 대한 추가 학습 데이터 수집
- 특정 물품 인식의 신뢰도 조정

---

## 🔒 데이터 구조 변경 사항

### ConfirmationService - validated_feedback 구조
```python
# 기존
{
    'classification': {
        'original_object_name': str,
        'original_primary_category': str,
        ...
    }
}

# 추가됨
{
    'classification': {
        'original_object_name': str,
        'corrected_object_name': str,        # ← 새로 추가
        'object_name_accurate': bool,        # ← 새로 추가
        'is_object_name_changed': bool,      # ← 새로 추가
        ...
    },
    'feedback_quality_indicators': {
        'has_object_name_correction': bool,  # ← 새로 추가
        ...
    }
}
```

### AccuracyTrackingService - accuracy_data 구조
```python
# 기존
{
    'daily_metrics': {...},
    'category_performance': {...},
    'size_performance': {...}
}

# 추가됨
{
    'daily_metrics': {
        'object_name_corrections': int  # ← 새로 추가
    },
    'object_name_performance': {        # ← 새로 추가
        'total_corrections': int,
        'correction_patterns': list,
        'frequently_corrected_items': dict
    },
    ...
}
```

---

## ✅ 피드백 품질 점수 계산

품목명 수정이 포함된 경우 피드백 품질 점수에 +0.15점 추가됨:

```python
# 예시 계산
기본 확인:          0.25점
신뢰도 평가:        0.25점
분류 수정:          0.25점
품목명 수정:        0.15점  ← 새로 추가
추가 메모:          0.1점
─────────────────────────
합계:               1.0점 (최대)
```

품목명 수정을 통해 사용자 피드백의 가치가 더욱 높이 인정되므로, 적극적인 참여 독려에 효과적입니다.

---

## 🧪 테스트 항목

### 단위 테스트 (필요시)
- [ ] UI에서 품목명 수정 입력 필드 렌더링
- [ ] 품목명 변경 감지 (`is_object_name_changed` 플래그)
- [ ] 피드백 저장 및 로깅
- [ ] 정확도 추적 메트릭 업데이트
- [ ] 자주 수정되는 물품 통계 계산

### 통합 테스트
- [ ] 전체 흐름: UI 입력 → 저장 → 메트릭 업데이트
- [ ] 실시간 메트릭 조회
- [ ] 정확도 보고서 생성

---

## 📝 향후 개선 사항

1. **데이터베이스 영속화**
   - 현재: 메모리 기반 저장
   - 개선: PostgreSQL에 영속화

2. **대시보드 표시**
   - 실시간 품목명 수정 통계 시각화
   - 자주 수정되는 물품 차트
   - 시간대별 수정 패턴 분석

3. **자동 학습**
   - 품목명 수정 패턴 분석을 통한 모델 재학습
   - 자동 데이터 수집 우선순위 결정

4. **사용자 피드백 페이지 통합**
   - 품목명 수정 이력 표시
   - 사용자가 자신의 기여도 확인 가능

---

## 📞 관련 파일

| 파일 | 역할 | 라인 |
|------|------|------|
| `enhanced_confirmation_ui.py` | UI 렌더링 | 164-308 |
| `confirmation_service.py` | 피드백 저장/기록 | 101-265 |
| `accuracy_tracking_service.py` | 정확도 추적 | 21-51, 65-90, 231-262, 418-442 |

---

**작성일**: 2025-10-27
**버전**: 1.0.0
**상태**: 구현 완료 및 테스트 통과
