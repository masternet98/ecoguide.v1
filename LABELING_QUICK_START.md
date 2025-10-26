# 라벨링 시스템 빠른 시작 가이드

## 🚀 5분 안에 시작하기

### 1️⃣ 현재 상태 확인

```bash
# 프로젝트 루트에서 실행
streamlit run pages/test_labeling.py
```

브라우저가 열리면:
- **탭 1: 📊 통계** - 저장된 라벨 개수 확인
- **탭 2: 💾 테스트 데이터 저장** - 테스트 라벨 저장해보기
- **탭 3: 🔍 저장된 데이터 확인** - 저장된 라벨 조회

### 2️⃣ 실제 앱에서 테스트

```bash
streamlit run app_new.py
```

**단계별:**
1. 📷 이미지 캡처 또는 업로드
2. 📝 프롬프트 설정 → "🤖 분석" 클릭
3. 📋 결과 확인 → 분류 선택 → "✅ 확인" 클릭
4. ✅ Step 4 (분류 완료) 도달
5. 🎉 "📊 학습 데이터로 저장되었습니다" 메시지 확인

### 3️⃣ 관리자 대시보드에서 확인

```bash
streamlit run pages/admin_labeling_dashboard.py
```

**조회 방법:**
1. 🏷️ 데이터 조회 탭 열기
2. 주 카테고리 선택 (예: 가구)
3. 저장된 이미지와 정보 확인

## 📁 생성된 파일

### 서비스
- `src/domains/analysis/services/labeling_service.py` - 핵심 서비스

### UI/페이지
- `pages/admin_labeling_dashboard.py` - 관리자 대시보드
- `pages/test_labeling.py` - 테스트 페이지

### 수정된 파일
- `app_new.py` - CompleteStep에 라벨링 통합
- `src/app/core/service_factory.py` - 서비스 등록

### 문서
- `LABELING_IMPLEMENTATION.md` - 상세 구현 문서
- `instructions/labeling_system_guide.md` - 기술 가이드

## 💾 저장 위치

```
uploads/
├── user_images/        # 라벨링된 이미지 저장
│   └── {uuid}.jpg
├── labels/            # 라벨 메타데이터
│   ├── _index.json    # 전체 인덱스
│   └── {uuid}.json    # 개별 라벨
```

## 🔧 구현 핵심

### 자동 저장 흐름

```
Step 4 (분류 완료) 도달
    ↓
CompleteStep.render()
    ↓
labeling_service.save_label() 자동 호출
    ↓
이미지 + JSON 메타데이터 저장
    ↓
인덱스 업데이트
    ↓
"📊 학습 데이터로 저장되었습니다" 메시지
```

### 라벨 JSON 구조

```json
{
  "file_id": "uuid",
  "image_path": "/uploads/user_images/uuid.jpg",
  "classification": {
    "primary_category": "FURN",
    "secondary_category": "FURN_BED",
    "object_name": "침대"
  },
  "dimensions": {
    "width_cm": 200,
    "height_cm": 120,
    "depth_cm": 30,
    "dimension_sum_cm": 350
  },
  "confidence": 0.95,
  "user_feedback": {
    "notes": "사용자 피드백"
  }
}
```

## ✅ 확인 사항

- [x] LabelingService 정상 작동
- [x] 자동 저장 기능
- [x] 관리자 대시보드
- [x] 테스트 페이지
- [x] 서비스 등록

## 📊 데이터 확인

### Python 코드로 확인

```python
from src.app.core.app_factory import get_application

app = get_application()
labeling_service = app.get_service('labeling_service')

# 통계
stats = labeling_service.get_category_statistics()
print(f"총 라벨: {stats['total_labels']}")

# 카테고리별 라벨
labels = labeling_service.get_labels_by_primary_category('FURN')
print(f"가구 카테고리: {len(labels)}개")
```

### 파일 시스템으로 확인

```bash
# 저장된 이미지 확인
ls -la uploads/user_images/

# 저장된 라벨 확인
ls -la uploads/labels/

# 인덱스 확인
cat uploads/labels/_index.json | python3 -m json.tool
```

## 🐛 문제 해결

### "LabelingService를 초기화할 수 없습니다" 메시지

**원인**: 서비스가 등록되지 않음

**해결책**:
1. `src/app/core/service_factory.py` 확인
2. `SERVICE_DOMAIN_MAP`에 `'labeling_service': 'analysis'` 있는지 확인
3. `create_default_service_registry()` 함수에 서비스 등록 있는지 확인

### 이미지가 저장되지 않음

**확인**:
1. `/uploads/user_images/` 디렉토리 존재하는지 확인
2. 디렉토리 권한 확인: `chmod 755 uploads/`
3. 로그에서 에러 메시지 확인

### JSON 라벨이 저장되지 않음

**확인**:
1. `/uploads/labels/` 디렉토리 존재하는지 확인
2. `_index.json` 파일 생성되었는지 확인
3. 개별 `{uuid}.json` 파일 생성되었는지 확인

## 📞 문서 참고

- **상세 구현**: `LABELING_IMPLEMENTATION.md`
- **기술 가이드**: `instructions/labeling_system_guide.md`
- **테스트 방법**: 본 문서 상단의 "5분 안에 시작하기"

## 🎯 다음 단계

1. **현재**: 라벨링 시스템이 데이터 수집 중
2. **곧**: 수집된 데이터로 모델 성능 분석
3. **향후**: 수집된 데이터로 모델 재학습

## 💡 팁

- 테스트 페이지에서 여러 번 저장해서 데이터 축적
- 관리자 대시보드에서 카테고리별 분포 확인
- 세부 정보 탭에서 개별 라벨 검토
- 로그를 통해 저장 성공/실패 추적

---

**모든 기능이 준비되었습니다!** 🎉

원하는 시점에 테스트를 시작할 수 있습니다.
