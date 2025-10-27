# EcoGuide.v1 설치 및 구성 가이드

## 📋 목차
1. [기본 설치](#기본-설치)
2. [Cloudflared 터널 설정](#cloudflared-터널-설정)
3. [환경 변수 구성](#환경-변수-구성)
4. [애플리케이션 실행](#애플리케이션-실행)
5. [문제 해결](#문제-해결)

---

## 기본 설치

### 1. 프로젝트 클론 및 디렉토리 이동
```bash
git clone <repository-url>
cd ecoguide.v1
```

### 2. 가상환경 생성
```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 필수 패키지 설치
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Cloudflared 터널 설정

EcoGuide.v1은 **외부 공유 URL** 기능을 위해 Cloudflared 터널을 지원합니다.

### 자동 설치 (권장)

`requirements.txt`에 `pycloudflared`가 포함되어 있으므로, 위의 "필수 패키지 설치" 단계를 완료하면 자동으로 설치됩니다.

```bash
# requirements.txt 설치 시 자동으로 pycloudflared 포함
pip install -r requirements.txt
```

**pycloudflared의 작동 원리:**
- `pip install pycloudflared` 실행 시 자동으로 cloudflared 바이너리 다운로드
- 플랫폼별(Windows, Linux, macOS) 호환성 자동 처리
- 설치 후 즉시 사용 가능

### 수동 설치 (선택사항)

플랫폼별로 cloudflared를 수동으로 설치하고 싶은 경우:

#### Linux (Ubuntu/Debian)
```bash
# 공식 apt 저장소 추가
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/linux $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-main.list

# 설치
sudo apt-get update
sudo apt-get install cloudflared
```

#### macOS (Homebrew)
```bash
brew install cloudflare/cloudflare/cloudflared
```

#### Windows (Chocolatey)
```bash
choco install cloudflared
```

#### Windows (수동)
1. [Cloudflare 다운로드 페이지](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/local/as-a-service/windows/)에서 `cloudflared.exe` 다운로드
2. PATH에 추가하거나 프로젝트 폴더에 저장

### 설치 확인
```bash
# cloudflared 버전 확인
cloudflared --version

# 또는 Python에서 확인
python -c "import pycloudflared; print('pycloudflared 설치됨')"
```

---

## 환경 변수 구성

프로젝트 루트에 `.env` 파일을 생성하고 다음 항목들을 설정하세요:

### 필수 설정
```bash
# .env

# OpenAI API 설정
OPENAI_API_KEY=sk-your-api-key-here

# 기타 선택사항 설정
# VWORLD_API_KEY=your-vworld-key
# NOTIFICATION_EMAIL_USER=your-email@example.com
# NOTIFICATION_EMAIL_PASSWORD=your-password
```

### Streamlit 클라우드 배포 (선택사항)
`.streamlit/secrets.toml` 파일을 생성:
```toml
[general]
OPENAI_API_KEY = "sk-your-api-key-here"
```

---

## 애플리케이션 실행

### Streamlit으로 실행
```bash
# 기본 실행
streamlit run app.py

# 디버그 모드
streamlit run app.py --logger.level=debug

# 특정 포트에서 실행
streamlit run app.py --server.port 8501
```

### 터널을 통한 외부 공유
1. **관리자 페이지 접속** (`admin.py` 또는 사이드바의 관리자 메뉴)
2. **🌐 외부 공유 URL (Cloudflare Tunnel)** 섹션에서:
   - 로컬 포트 설정 (기본값: 8501)
   - **▶️ 터널 시작** 버튼 클릭
   - 생성된 공개 URL 확인

### 실행 스크립트
```bash
# Linux/macOS
bash run.sh

# Windows
run.bat
```

---

## 문제 해결

### 1. "cloudflared 실행 파일을 찾을 수 없습니다" 오류

**원인:**
- cloudflared가 설치되지 않음
- pycloudflared가 설치되지 않음

**해결 방법:**
```bash
# 방법 1: 전체 의존성 재설치
pip install --upgrade -r requirements.txt

# 방법 2: pycloudflared만 설치
pip install pycloudflared

# 방법 3: 시스템 패키지 관리자로 설치
# Linux
sudo apt-get install cloudflared

# macOS
brew install cloudflare/cloudflare/cloudflared
```

### 2. pycloudflared 설치 중 오류

**ARM64 Mac (Apple Silicon) 사용자:**
```bash
# Rosetta 2 에뮬레이션이 필요할 수 있음
# 또는 시스템 cloudflared 설치 권장
brew install cloudflare/cloudflare/cloudflared
```

### 3. 터널 시작 후 URL이 나타나지 않음

**확인 사항:**
1. 포트 번호가 올바른지 확인 (기본값: 8501)
2. Streamlit이 실제로 해당 포트에서 실행 중인지 확인:
   ```bash
   lsof -i :8501  # Linux/macOS
   netstat -ano | findstr :8501  # Windows
   ```
3. 방화벽 설정 확인
4. 로그 파일 확인: `logs/cloudflared_tunnel.log`

### 4. 터널 연결 실패

**확인 방법:**
```bash
# 수동으로 cloudflared 테스트
cloudflared tunnel --url http://localhost:8501

# 또는
cloudflared tunnel --url http://localhost:8501 --loglevel debug
```

### 5. 개발 환경에서만 터널 필요 없음

**기능 비활성화 방법:**
- `src/app/core/feature_registry.py`에서 `tunnel_enabled` flag 확인
- 필요시 requirements.txt에서 `pycloudflared` 주석 처리
  ```bash
  # pycloudflared>=0.2.0
  ```

---

## 참고 자료

### Cloudflare Tunnel
- [공식 문서](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [cloudflared CLI 참고](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/local/)

### EcoGuide 개발 가이드
- [개발 가이드](./development_guidelines.md)
- [아키텍처 가이드](./architecture_development_guidelines.md)

### 환경 변수 및 설정
- [CONFIG 가이드](../src/app/core/config.py)
- [CONFIG 검증](../src/app/core/config_validator.py)

---

## 도움말 및 지원

문제가 해결되지 않으면:

1. **로그 확인**
   ```bash
   # Streamlit 로그
   streamlit run app.py --logger.level=debug

   # 터널 로그
   tail -f logs/cloudflared_tunnel.log
   ```

2. **문제 보고**
   - GitHub Issues: [프로젝트 이슈 페이지]
   - 로그 정보 함께 제공

3. **기타 리소스**
   - [Cloudflare 커뮤니티 포럼](https://community.cloudflare.com/)
   - [Streamlit 문서](https://docs.streamlit.io/)
