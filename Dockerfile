FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    nodejs \
    npm \
    && npm install -g wrangler \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# entrypoint 스크립트 실행 권한
RUN chmod +x /app/entrypoint.sh

# 필요한 디렉토리 생성
RUN mkdir -p /app/logs /app/dist/uploads /app/data

# 환경변수 설정
ENV FLASK_DEBUG=False
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/login || exit 1

# entrypoint 스크립트 실행
CMD ["/app/entrypoint.sh"]
