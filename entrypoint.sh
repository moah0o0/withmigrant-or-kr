#!/bin/bash
set -e

echo "=== Starting Admin Server ==="

# dist 폴더가 비어있으면 초기 빌드 실행
if [ ! -f "/app/dist/index.html" ]; then
    echo "Building static site..."
    python build.py
    echo "Build complete!"
fi

# static 폴더 복사 (CSS, JS, images)
if [ -d "/app/static" ] && [ ! -d "/app/dist/static" ]; then
    echo "Copying static files..."
    cp -r /app/static /app/dist/
fi

mkdir -p /app/logs

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --capture-output \
    --log-level info \
    app:app
