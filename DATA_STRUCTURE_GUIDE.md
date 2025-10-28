# EcoGuide.v1 데이터 구조 및 Git 관리 가이드

## 📋 개요

EcoGuide.v1은 다양한 데이터를 Git으로 관리합니다. 이 문서는 데이터 구조, Git 관리 정책, 배포 시 데이터 유지 방법을 설명합니다.

---

## 📁 디렉토리 구조

```
ecoguide.v1/
├── data/
│   └── prompts/                    # ✅ Git 관리 (프롬프트 템플릿)
│       ├── templates/              # 프롬프트 템플릿 (UUID 이름)
│       │   ├── 14d2ce15-8127-...json  # 배출정보 프롬프트
│       │   ├── 9c063a86-23a1-...json  # 수수료 정보 프롬프트
│       │   └── ...
│       ├── features/               # 기능 설정
│       │   ├── feature_config.json
│       │   └── prompt_feature_registry.json
│       ├── mappings/               # 기능 매핑
│       │   └── feature_mappings.json
│       ├── stats/                  # 사용 통계
│       │   └── usage_stats.json
│       └── backups/                # ❌ Git 무시 (백업 파일)
│
├── uploads/                        # ✅ Git 관리 (라벨 데이터만)
│   ├── labels/                     # 라벨 데이터 (JSON)
│   │   ├── _index.json
│   │   └── *.json
│   ├── user_images/                # ❌ Git 무시 (이미지 파일)
│   ├── dong_cache/                 # ❌ Git 무시 (캐시)
│   └── temp/                       # ❌ Git 무시 (임시 파일)
│
├── models/                         # ❌ Git 무시 (AI 모델 파일)
└── logs/                           # ❌ Git 무시 (로그 파일)
```

---

## 🔑 Git 관리 정책

### ✅ Git에 포함하는 파일

| 항목 | 경로 | 이유 | 크기 |
|------|------|------|------|
| **프롬프트 템플릿** | `data/prompts/templates/` | 배포 후 필수 | ~50KB |
| **기능 설정** | `data/prompts/features/` | 배포 후 필수 | ~10KB |
| **매핑 설정** | `data/prompts/mappings/` | 배포 후 필수 | ~5KB |
| **라벨 데이터** | `uploads/labels/` | 데이터 관리 | ~100KB |
| **라벨 인덱스** | `uploads/labels/_index.json` | 메타데이터 | ~5KB |

### ❌ Git에 제외하는 파일

| 항목 | 경로 | 이유 | 크기 |
|------|------|------|------|
| **사용자 이미지** | `uploads/user_images/` | 개인정보, 용량 | 수백 MB |
| **AI 모델** | `models/` | 용량 큼 | 수백 MB |
| **백업 파일** | `data/prompts/backups/` | 임시 데이터 | 수십 MB |
| **캐시** | `uploads/*/cache/` | 임시 데이터 | 가변 |
| **로그** | `logs/` | 런타임 데이터 | 가변 |
| **환경변수** | `.env` | 보안 위험 | - |

---

## 🔄 배포 시나리오별 데이터 흐름

### 시나리오 1: 로컬 개발
```
로컬 머신
├── .env (로컬만, Git 제외)
├── data/prompts/ (Git 관리, 자동 사용)
├── uploads/labels/ (Git 관리)
└── uploads/user_images/ (로컬만, 개발용)
```

### 시나리오 2: Streamlit Cloud 배포
```
GitHub 저장소
├── data/prompts/ ✅ → Streamlit Cloud 자동 다운로드
├── uploads/labels/ ✅ → Cloud 자동 로드
├── uploads/districts/ ✅ → Cloud 자동 로드
├── uploads/monitoring/ ✅ → Cloud 자동 로드
├── uploads/user_images/ ❌ → Git 제외 (이미지는 사용자 업로드로 생성)
└── .env (❌ GitHub에 미포함, Cloud Secrets 사용)

Streamlit Cloud
├── 자동으로 data/prompts/ 로드
├── 자동으로 uploads/labels/ 로드 (라벨 JSON만 - 메타데이터)
├── 자동으로 행정구역/모니터링 데이터 로드
├── Secrets에서 API 키 로드
├── 사용자가 새로운 이미지 업로드 시 동적 생성
└── 완벽하게 작동 ✅
```

**주요 차이:**
- **라벨 JSON 데이터:** Git에서 로드 (배포 시 유지)
- **라벨 이미지:** 사용자가 업로드 시 동적 생성 (Git 제외, 용량 관리)

### 시나리오 3: Docker 배포
```
Docker 이미지 빌드
├── Dockerfile: data/prompts/ 복사
├── Dockerfile: uploads/labels/ 복사
└── docker-compose.yml: .env 환경변수 사용

컨테이너 실행
├── 모든 프롬프트 파일 사용 가능
├── 라벨 데이터 마운트
└── 완벽하게 작동 ✅
```

---

## 📊 프롬프트 파일 구조

### 템플릿 파일 형식

```json
{
  "template_id": "14d2ce15-8127-4b77-9be4-a0cb56600ead",
  "name": "배출정보 조회",
  "description": "행정구역 기반 배출정보 조회 프롬프트",
  "version": "1.0",
  "type": "disposal_guidance",
  "variables": ["district_context", "object_info"],
  "content": "행정구역: {district_context}\n물품: {object_info}\n...",
  "max_tokens": 2048,
  "created_at": "2025-09-11T...",
  "updated_at": "2025-10-27T..."
}
```

### 등록된 프롬프트 템플릿

| ID (처음 8글자) | 이름 | 용도 | 변수 |
|-----------------|------|------|------|
| `14d2ce15...` | 배출정보 조회 | 지자체 배출 정보 검색 | district_context, object_info |
| `9c063a86...` | 수수료 정보 | 처리 수수료 계산 | object_info, district_context |
| `ca7a6fc5...` | 분류 기본 | 폐기물 기본 분류 | object_description |
| `25ff6989...` | 분류 고급 | 고급 분류 추론 | object_description, context |
| `53099b76...` | 이미지 분석 | 이미지 기반 분석 | image_context |
| `8c3e474d...` | 확인 및 수정 | 사용자 확인용 | classification_result |
| `7d9b54a4...` | 기본 분석 | 기본 AI 분석 | object_description |

---

## 🔐 보안 및 프라이버시

### 민감한 파일 (Git 제외)

```bash
# .gitignore에 이미 포함된 항목
.env                    # API 키, 비밀번호
uploads/user_images/    # 사용자 이미지 (개인정보)
uploads/temp/          # 임시 업로드
models/                # AI 모델 (용량)
logs/                  # 실행 로그
```

### 환경변수 관리

**로컬 개발:**
```bash
cp .env.example .env
# .env 파일에 실제 키 입력 (Git 제외)
```

**배포 환경:**
```bash
# Streamlit Cloud
앱 설정 → Secrets → .streamlit/secrets.toml 내용 입력

# Docker/Heroku
docker-compose.yml에서 environment 섹션으로 관리
```

---

## 🚀 배포 후 데이터 유지 확인

### Streamlit Cloud 배포 후 확인

```bash
# 1. 앱이 정상 로드되는가?
✅ 초기 로드 화면 표시

# 2. 프롬프트가 로드되었는가?
✅ 이미지 분석 기능 작동

# 3. 라벨 데이터가 있는가?
✅ 관리자 페이지에서 라벨 조회 가능

# 4. 환경변수가 설정되었는가?
✅ API 키 사용 가능 (프롬프트 렌더링 성공)
```

### Docker 배포 후 확인

```bash
# 1. 컨테이너 로그 확인
docker-compose logs ecoguide

# 2. 프롬프트 파일 확인
docker exec ecoguide-ecoguide-1 ls -la /app/data/prompts/templates/

# 3. 앱 접근
curl http://localhost:8080
```

---

## 📝 데이터 관리 워크플로우

### 프롬프트 수정 절차

```
1. 로컬에서 프롬프트 수정
   ├── UI에서 수정 또는
   └── 파일 직접 편집

2. data/prompts/ 파일 변경
   └── 자동으로 data/prompts/templates/*.json 수정

3. Git에 커밋
   git add data/prompts/
   git commit -m "feat: 프롬프트 개선"

4. GitHub 푸시
   git push

5. 배포 환경 자동 반영
   Streamlit Cloud: 자동 재배포
   Docker: 이미지 재빌드 시 반영
```

### 라벨 데이터 추가 절차

```
1. 관리자가 라벨링 수행
   ├── 이미지 업로드 (uploads/user_images/) - 로컬 임시 저장
   └── 라벨 정보 저장 (uploads/labels/*.json) - 메타데이터

2. Git에 커밋 (주기적 - 라벨 JSON만)
   git add uploads/labels/
   git commit -m "feat(labels): 새 라벨 데이터 추가"

3. GitHub 푸시
   git push

4. 배포 환경에 반영
   ✅ 라벨 JSON 메타데이터 자동 포함
   ✅ 라벨 이미지는 사용자가 Streamlit Cloud에서 다시 업로드
```

---

## 📸 라벨 이미지 관리 시스템

### 라벨 이미지와 JSON 메타데이터

**라벨 시스템은 두 부분으로 구성:**

```
라벨 데이터 (uploads/labels/)
├── _index.json                          # 라벨 메타데이터 (Git ✅)
├── a4329e80-562c-4e50-86e1-...json     # 라벨 1 정보 (Git ✅)
├── d9e2bed9-8fd0-4e95-a88f-...json     # 라벨 2 정보 (Git ✅)
└── ...

라벨 이미지 (uploads/user_images/)
├── a4329e80-562c-4e50-86e1-....jpg     # 라벨 1 원본 이미지 (Git ❌)
├── d9e2bed9-8fd0-4e95-a88f-....jpg     # 라벨 2 원본 이미지 (Git ❌)
└── ...
```

### 배포 시 라벨 데이터 유지 방식

**로컬 개발 (완전한 데이터):**
```
uploads/labels/ (JSON)        ✅ Git
uploads/user_images/ (사진)   ✅ 로컬 저장
└─ 라벨 정보 + 이미지 모두 표시
```

**Streamlit Cloud (메타데이터 기반):**
```
uploads/labels/ (JSON)        ✅ Git → Cloud 자동 로드
uploads/user_images/ (사진)   ❌ Git 제외
└─ 라벨 정보만 표시 (이미지는 필요시 다시 업로드)
```

**Docker/Heroku (선택적):**
```
uploads/labels/ (JSON)        ✅ Volume 마운트
uploads/user_images/ (사진)   ✅ Volume 마운트 (선택)
└─ 라벨 정보 + 이미지 모두 표시
```

### 라벨 JSON 구조 예시

```json
{
  "file_id": "a4329e80-562c-4e50-86e1-9888f6220b6b",
  "timestamp": "2025-10-26T21:43:00.701365",
  "primary_category": "가구",
  "secondary_category": "침대/매트리스",
  "object_name": "아기 침대",
  "confidence": 0.8,
  "labeling_quality": 0.62
}
```

**주요 특징:**
- ✅ 라벨 정보만 저장 (이미지 경로 X)
- ✅ 배포 환경에서 메타데이터 자동 로드
- ✅ 원본 이미지는 로컬에서만 저장 (용량 관리)

### 배포 환경별 라벨 데이터 처리

| 환경 | 라벨 JSON | 라벨 이미지 | 설명 |
|------|----------|----------|------|
| **로컬** | Git + 로컬 | 로컬 | 완벽한 개발 환경 |
| **Streamlit Cloud** | Git ✅ | 사용자 업로드 | JSON만 배포, 이미지는 필요시 업로드 |
| **Docker** | Git ✅ | Volume 마운트 | 선택적으로 이미지 포함 가능 |
| **Heroku** | Git ✅ | 임시 저장소 | JSON만 배포, 영구 저장소 권장 |

### 라벨 데이터 활용 방안

**배포 후에도 라벨 데이터 유지:**

```python
# 1. JSON 메타데이터 로드 (배포 환경에서 자동 로드)
from src.domains.infrastructure.services.detail_content_service import get_label_metadata
metadata = get_label_metadata(file_id)  # 시도, 시군구, 폐기물 정보 등

# 2. UI에서 라벨 정보 표시
st.write(f"대분류: {metadata['primary_category']}")
st.write(f"세분류: {metadata['secondary_category']}")

# 3. 원본 이미지가 필요한 경우
# - 로컬: uploads/user_images/{file_id}.jpg 에서 로드
# - Streamlit Cloud: 사용자가 새로 업로드
```

---

## 🔧 트러블슈팅

### 문제 1: 배포 후 프롬프트 사라짐

**원인:** `data/` 디렉토리가 `.gitignore`에 포함되어 있음

**해결:**
```bash
# 확인
git check-ignore -v data/prompts/templates/14d2ce15-8127-...json

# 수정
# .gitignore에서 data/ 제외 처리
# data/prompts/ 파일 추가
git add data/prompts/
```

### 문제 2: 용량이 너무 큼

**원인:** 사용자 이미지나 모델 파일이 Git에 포함됨

**해결:**
```bash
# .gitignore 확인
grep -n "uploads/user_images\|models/" .gitignore

# 큰 파일 제거
git rm -r --cached uploads/user_images/
git commit -m "Remove large image files"
```

### 문제 3: 백업 파일이 계속 추가됨

**원인:** `data/prompts/backups/`가 Git에 추가됨

**해결:**
```bash
# .gitignore에 백업 폴더 추가
echo "data/prompts/backups/" >> .gitignore

# 이미 추가된 파일 제거
git rm -r --cached data/prompts/backups/
git commit -m "Remove prompt backups from git"
```

### 문제 4: 배포 후 라벨 이미지 파일 사라짐

**원인:** `uploads/user_images/`는 Git에 제외되어 있음

**증상:**
- 로컬: ✅ 라벨 이미지 + 라벨 정보 모두 표시
- 배포: ❌ 라벨 정보만 표시 (이미지 없음)

**설명:**
이는 **의도된 동작**입니다.
- 라벨 **JSON 메타데이터** (uploads/labels/): Git 관리 ✅
- 라벨 **이미지 파일** (uploads/user_images/): Git 제외 ❌

**이유:**
1. 이미지는 용량이 크고 개인정보 포함 가능
2. 배포 환경에서 이미지 스토리지 관리 복잡
3. 라벨 정보(메타데이터)만 있으면 폐기물 분류, 배출정보 조회 등은 가능

**활용 방안:**

**로컬 개발:**
```
라벨 정보 + 이미지 모두 표시 (uploads/labels/ + uploads/user_images/)
```

**Streamlit Cloud:**
```
라벨 정보만 표시 (uploads/labels/)
원본 이미지가 필요하면 사용자가 다시 업로드
```

**Docker (Volume 마운트):**
```
docker-compose.yml에서 uploads/ 전체 마운트하면
라벨 정보 + 이미지 모두 표시 가능
```

**확인:**
```bash
# .gitignore 확인
grep "uploads/user_images" .gitignore
# 결과: uploads/user_images/ (제외됨)

# Git 상태 확인
git check-ignore uploads/user_images/test.jpg
# 결과: uploads/user_images/test.jpg (무시됨)
```

---

## 📚 참고 자료

- [프롬프트 관리 가이드](instructions/comprehensive_development_guidelines.md)
- [배포 가이드](DEPLOYMENT_GUIDE.md)
- [아키텍처 가이드](instructions/architecture_development_guidelines.md)

---

**Last Updated:** 2025-10-28
**Git Managed Files:**
- data/prompts/: 7개 템플릿 + 설정 파일
- uploads/labels/: 34개 라벨 JSON 메타데이터
- uploads/districts/: 행정구역 데이터
- uploads/monitoring/: 모니터링 데이터
- uploads/waste_types/, waste_links/: 폐기물 정보

**Total Size:** ~200KB (배포 포함)
**Excluded from Git:** 라벨 이미지, 모델, 로그 등
