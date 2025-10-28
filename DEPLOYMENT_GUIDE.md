# EcoGuide.v1 배포 가이드

이 문서는 EcoGuide.v1을 다양한 환경에 배포하는 방법을 설명합니다.

## 📋 목차

- [Streamlit Cloud 배포](#streamlit-cloud-배포)
- [Docker 배포](#docker-배포)
- [Heroku 배포](#heroku-배포)
- [환경 변수 설정](#환경-변수-설정)
- [헬스체크 및 모니터링](#헬스체크-및-모니터링)

---

## Streamlit Cloud 배포

### 요구사항

- GitHub 저장소 연동
- Streamlit 계정 (https://streamlit.io)
- 환경 변수 설정 (API 키, 시크릿 등)

### 단계별 배포

#### 1️⃣ GitHub 저장소 준비

```bash
# 현재 코드 커밋
git add .
git commit -m "Deploy to Streamlit Cloud"
git push
```

#### 2️⃣ Streamlit Cloud 연결

1. https://share.streamlit.io 접속
2. "New app" 버튼 클릭
3. GitHub 저장소 선택: `masternet98/ecoguide.v1`
4. Branch: `master`
5. Main file path: `app_new.py`

#### 3️⃣ 환경 변수 설정

Streamlit Cloud 대시보드에서:

1. 앱 설정 (⚙️) 클릭
2. **Secrets** 탭 선택
3. 다음 내용을 입력 (`.streamlit/secrets.toml.example` 참조):

```toml
OPENAI_API_KEY = "sk-proj-your_key_here"
NOTIFICATION_EMAIL_USER = "ecoguide.ai@gmail.com"
NOTIFICATION_EMAIL_PASSWORD = "your_password_here"
VWORLD_API_KEY = "your_vworld_key_here"
# GOOGLE_CSE_API_KEY = "your_google_key_here"  # 선택사항
```

**중요:** `.env` 파일은 GitHub에 커밋하지 마세요. Streamlit Cloud의 Secrets 기능을 사용하세요.

#### 4️⃣ 포트 설정 확인

- ✅ `.streamlit/config.toml`: `port` 설정 제거 또는 주석 처리
- ✅ `Procfile`: 올바르게 설정됨 (이미 수정됨)
- ✅ `app_new.py`: 8501 포트 가정하지 않음

#### 5️⃣ 배포 확인

배포 후 다음 확인:

```
1. 앱이 정상 로드되는가?
2. 이미지 업로드 가능한가?
3. AI 분석이 정상 작동하는가?
4. 위치 기능이 작동하는가?
```

### 🐛 Streamlit Cloud 헬스체크 오류 해결

**오류 메시지:**
```
The service has encountered an error while checking the health of the Streamlit app:
Get "http://localhost:8501/healthz": dial tcp 127.0.0.1:8501: connect: connection refused
```

**원인:**
- `.streamlit/config.toml`의 `port = 8080` 설정이 Streamlit Cloud의 포트 할당과 충돌
- Streamlit Cloud는 자동으로 PORT 환경변수를 할당하는데, config.toml의 고정 포트가 우선됨

**해결책:**
1. `.streamlit/config.toml`에서 `port` 설정 주석 처리 ✅ (이미 수정됨)
2. Streamlit Cloud가 자동으로 PORT를 할당하도록 함

---

## Docker 배포

### 로컬 테스트

```bash
# Docker 이미지 빌드
docker build -t ecoguide:latest .

# 컨테이너 실행
docker run -p 8080:8080 \
  -e OPENAI_API_KEY="your_key" \
  -e NOTIFICATION_EMAIL_USER="your_email" \
  -e NOTIFICATION_EMAIL_PASSWORD="your_password" \
  ecoguide:latest
```

### Docker Compose 사용 (권장)

```bash
# .env 파일에 환경변수 설정
cp .env.example .env
# .env 파일 편집

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f ecoguide

# 서비스 중지
docker-compose down
```

**접근 URL:** http://localhost:8080

### Google Cloud Run 배포

```bash
# 프로젝트 설정
gcloud config set project YOUR_PROJECT_ID

# 이미지 빌드 및 푸시
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ecoguide:latest

# Cloud Run 배포
gcloud run deploy ecoguide \
  --image gcr.io/YOUR_PROJECT_ID/ecoguide:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=your_key \
  --set-env-vars NOTIFICATION_EMAIL_USER=your_email \
  --set-env-vars NOTIFICATION_EMAIL_PASSWORD=your_password \
  --set-env-vars VWORLD_API_KEY=your_vworld_key
```

---

## Heroku 배포

### 사전 요구사항

- Heroku 계정
- Heroku CLI 설치

### 배포 단계

```bash
# Heroku 로그인
heroku login

# 앱 생성
heroku create ecoguide-app

# 환경 변수 설정
heroku config:set OPENAI_API_KEY="your_key" -a ecoguide-app
heroku config:set NOTIFICATION_EMAIL_USER="your_email" -a ecoguide-app
heroku config:set NOTIFICATION_EMAIL_PASSWORD="your_password" -a ecoguide-app
heroku config:set VWORLD_API_KEY="your_vworld_key" -a ecoguide-app

# 배포
git push heroku master  # 또는 git push heroku main (GitHub 연동 사용)

# 로그 확인
heroku logs --tail
```

---

## 환경 변수 설정

### 필수 환경 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 | `sk-proj-...` |
| `NOTIFICATION_EMAIL_USER` | Gmail 알림 계정 | `ecoguide.ai@gmail.com` |
| `NOTIFICATION_EMAIL_PASSWORD` | Gmail 앱 비밀번호 | `xxxx xxxx xxxx xxxx` |
| `VWORLD_API_KEY` | VWorld API 키 | `906B...` |

### 선택사항 변수

| 변수명 | 설명 |
|--------|------|
| `GOOGLE_CSE_API_KEY` | Google 검색 API (선택) |
| `GOOGLE_CSE_SEARCH_ENGINE_ID` | Google 검색 엔진 ID (선택) |

### 로컬 개발 환경 설정

```bash
# .env 파일 생성 (.env.example 복사)
cp .env.example .env

# .env 파일 편집하여 실제 키 입력
nano .env

# python-dotenv가 자동으로 로드함
```

### 배포 환경 보안

**중요:** 다음을 절대 하지 마세요:

❌ `.env` 파일을 GitHub에 커밋
❌ API 키를 코드에 하드코딩
❌ 환경 변수를 로그에 출력

✅ 배포 플랫폼의 Secrets 기능 사용
✅ 환경 변수로 모든 민감 정보 관리
✅ `.env`를 `.gitignore`에 추가 (이미 설정됨)

---

## 헬스체크 및 모니터링

### 로컬 헬스체크

```bash
# 앱이 실행 중인지 확인
curl http://localhost:8080

# Streamlit 헬스체크 엔드포인트
curl http://localhost:8080/healthz  # Streamlit 기본
```

### 배포 후 점검 항목

- [ ] 앱이 정상 로드되는가?
- [ ] 이미지 업로드/캡처 가능한가?
- [ ] AI 분석 결과가 정상인가?
- [ ] 위치 정보가 정확한가?
- [ ] 메일 알림이 작동하는가?
- [ ] 배출 정보 조회가 정상인가?

### 로그 모니터링

**Streamlit Cloud:**
```
앱 대시보드 → 로그 탭
```

**Docker:**
```bash
docker-compose logs -f ecoguide
```

**Heroku:**
```bash
heroku logs --tail
```

**Google Cloud Run:**
```bash
gcloud run logs read ecoguide --limit 50
```

---

## 🆘 배포 문제 해결

### 1. "Connection refused" 오류

**원인:** 포트 설정 충돌
**해결:** `.streamlit/config.toml`에서 `port` 설정 제거

```bash
# config.toml 확인
grep "port" .streamlit/config.toml
# 결과: # port = 8080  (주석 처리되어야 함)
```

### 2. API 키 오류

**원인:** 환경 변수 미설정
**해결:** 배포 플랫폼의 Secrets/환경 변수 설정 확인

```bash
# Streamlit Cloud: 앱 설정 → Secrets
# Docker: docker-compose.yml의 environment 확인
# Heroku: heroku config 확인
```

### 3. 이미지 업로드 실패

**원인:** 스토리지 권한 부족
**해결:**
- Docker: volumes 설정 확인
- Cloud Run: 임시 디렉토리 사용 (`/tmp`)
- Heroku: 임시 스토리지만 가능 (permanent storage 추천)

### 4. 느린 응답

**원인:** 리소스 부족
**해결:**
- Streamlit Cloud: 더 높은 계층으로 업그레이드
- Docker/Heroku: 메모리/CPU 할당 증가

### 5. VWorld API 키가 로컬에서는 동작하는데 Streamlit Cloud에서 동작 안함

**원인:** Streamlit Secrets 설정 오류
**증상:**
- 로컬 개발: ✅ GPS 기반 위치 조회 정상 작동
- Streamlit Cloud: ❌ "VWorld API 키 미설정" 오류

**원인 분석:**
```
로컬: .env 파일 → os.environ.get('VWORLD_API_KEY') ✅
Streamlit Cloud: .streamlit/secrets.toml → st.secrets['VWORLD_API_KEY'] ❌ (미설정시)
```

**해결 방법:**

#### Step 1: Streamlit Cloud에서 Secrets 설정 확인
```
1. https://share.streamlit.io 접속
2. 앱 선택
3. ⚙️ 설정 클릭
4. "Secrets" 탭 선택
5. 다음 내용 입력:

VWORLD_API_KEY = "906B6560-0336-38D7-8D34-F38456C46956"  # 실제 API 키로 변경
```

#### Step 2: Secrets 파일 확인
```toml
# .streamlit/secrets.toml.example 참조
OPENAI_API_KEY = "sk-proj-..."
NOTIFICATION_EMAIL_USER = "ecoguide.ai@gmail.com"
NOTIFICATION_EMAIL_PASSWORD = "..."
VWORLD_API_KEY = "906B..."  # 필수!
```

#### Step 3: 앱 재시작
```
Streamlit Cloud 대시보드에서 앱 재시작 또는 재배포
```

#### Step 4: 검증
Streamlit Cloud 앱에서:
1. "위치 선택" 탭으로 이동
2. "GPS로 위치 찾기" 클릭
3. 좌표 입력
4. "위치 조회" 버튼 클릭
5. ✅ 주소가 표시되면 정상 작동

**디버깅 로그 확인:**

```bash
# Streamlit Cloud 대시보드의 "Logs" 탭에서:
- "VWorld API 키 가용성 확인"
- "VWorld: True (키: 906B6560-...)" 메시지 확인
```

**만약 여전히 작동 안 한다면:**

1. **API 키 유효성 확인**
   - VWorld 포털에서 API 키 상태 확인
   - 키가 활성화되었는지 확인
   - 일일 요청 한도 확인

2. **Streamlit Cloud 재배포**
   ```bash
   git push  # 변경 사항 없어도 괜찮음
   # Streamlit Cloud가 자동으로 재배포
   ```

3. **테스트 API 호출**
   ```bash
   # 로컬에서 테스트
   curl "https://api.vworld.kr/req/address?service=address&request=getAddress&version=2.0&crs=epsg:4326&point=127.0366,37.5007&format=json&type=both&zipcode=true&key=YOUR_VWORLD_KEY"
   ```

**참고:**
- 로컬 개발: `.env` 파일에서 로드
- Streamlit Cloud: `.streamlit/secrets.toml`에서 로드 (자동)
- 코드는 두 가지 모두 자동으로 지원합니다 (우선순위: Secrets > 환경변수)

---

## 📚 참고 자료

- [Streamlit Cloud 공식 문서](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app)
- [Docker 공식 문서](https://docs.docker.com/)
- [Heroku 공식 문서](https://devcenter.heroku.com/)
- [Google Cloud Run 문서](https://cloud.google.com/run/docs)

---

**Last Updated:** 2025-10-28
**Python Version:** 3.12
**Streamlit Version:** >=1.33.0
