# 1) 가벼운 공식 이미지(슬림)
FROM python:3.11-slim

# 2) (선택) 빌드시 필요한 도구 - 과학/빌드 패키지 쓰면 유지, 아니면 지워도 됨
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3) 작업 디렉터리
WORKDIR /app

# 4) 의존성 먼저 복사(캐시 최적화)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# 5) 앱 소스를 선택적으로 복사하여 캐시 효율성 증대
COPY app_new.py /app/
COPY src/ /app/src/
COPY pages/ /app/pages/
COPY models/ /app/models/

# 6) Cloud Run은 $PORT를 할당함
ENV PORT=8080

# 7) Streamlit이 외부에서 접속 가능하도록 0.0.0.0 바인딩 & $PORT 사용
CMD ["bash", "-lc", "streamlit run app_new.py --server.port=$PORT --server.address=0.0.0.0"]