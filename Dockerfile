FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 필요한 디렉토리 생성
RUN mkdir -p logs dist/uploads

# 환경변수 설정
ENV FLASK_DEBUG=False
ENV PYTHONUNBUFFERED=1

# 포트 노출
EXPOSE 8000

# Gunicorn으로 앱 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "app:app"]
