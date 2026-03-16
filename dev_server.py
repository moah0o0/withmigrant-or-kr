#!/usr/bin/env python3
"""
개발용 라이브 서버
- templates/, static/ 파일 변경 감지 → 자동 SSG 빌드 → dist/ 서빙
- 사용법: python dev_server.py
"""

import os
import sys
import time
import threading
import subprocess
from flask import Flask, send_from_directory, abort, Response
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')

WATCH_DIRS = [
    os.path.join(BASE_DIR, 'templates'),
    os.path.join(BASE_DIR, 'static'),
]

# SSE 클라이언트 목록 (브라우저 자동 리로드용)
sse_clients = []

# ==========================================
# 빌드
# ==========================================

_build_lock = threading.Lock()
_build_scheduled = False


def run_build():
    """SSG 빌드 실행"""
    global _build_scheduled
    with _build_lock:
        _build_scheduled = False
    print("\n🔨 빌드 시작...")
    start = time.time()
    result = subprocess.run(
        [sys.executable, 'build.py'],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    elapsed = time.time() - start
    if result.returncode == 0:
        print(f"✅ 빌드 완료 ({elapsed:.1f}s)")
    else:
        print(f"❌ 빌드 실패 ({elapsed:.1f}s)")
        if result.stderr:
            print(result.stderr[:500])
    # 브라우저 리로드 알림
    notify_reload()


def schedule_build():
    """디바운스: 0.5초 내 중복 변경 무시"""
    global _build_scheduled
    with _build_lock:
        if _build_scheduled:
            return
        _build_scheduled = True

    def _delayed():
        time.sleep(0.5)
        run_build()

    threading.Thread(target=_delayed, daemon=True).start()


# ==========================================
# 파일 감시
# ==========================================

class RebuildHandler(FileSystemEventHandler):
    EXTENSIONS = {'.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}

    def on_any_event(self, event):
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in self.EXTENSIONS:
            relpath = os.path.relpath(event.src_path, BASE_DIR)
            print(f"📝 변경 감지: {relpath}")
            schedule_build()


# ==========================================
# SSE (브라우저 자동 리로드)
# ==========================================

def notify_reload():
    """모든 연결된 브라우저에 리로드 신호 전송"""
    dead = []
    for client in sse_clients:
        try:
            client.put('reload')
        except Exception:
            dead.append(client)
    for c in dead:
        sse_clients.remove(c)


# ==========================================
# Flask 서버
# ==========================================

app = Flask(__name__)

# 리로드 스크립트 (HTML 응답에 주입)
RELOAD_SCRIPT = """
<script>
(function() {
  var es = new EventSource('/__dev_reload');
  es.onmessage = function(e) {
    if (e.data === 'reload') location.reload();
  };
  es.onerror = function() {
    setTimeout(function() { location.reload(); }, 2000);
  };
})();
</script>
"""


@app.route('/__dev_reload')
def dev_reload_sse():
    """SSE 엔드포인트 - 브라우저 자동 리로드"""
    import queue
    q = queue.Queue()
    sse_clients.append(q)

    def stream():
        try:
            while True:
                msg = q.get(timeout=30)
                yield f"data: {msg}\n\n"
        except queue.Empty:
            yield "data: ping\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in sse_clients:
                sse_clients.remove(q)

    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/')
def index():
    return _serve_html('index.html')


@app.route('/<path:filename>')
def serve_file(filename):
    file_path = os.path.join(DIST_DIR, filename)

    if os.path.isfile(file_path):
        if file_path.endswith('.html'):
            return _serve_html(filename)
        return send_from_directory(DIST_DIR, filename)

    if os.path.isdir(file_path):
        index_file = os.path.join(filename, 'index.html')
        if os.path.isfile(os.path.join(DIST_DIR, index_file)):
            return _serve_html(index_file)

    html_file = filename if filename.endswith('.html') else f'{filename}.html'
    if os.path.isfile(os.path.join(DIST_DIR, html_file)):
        return _serve_html(html_file)

    abort(404)


def _serve_html(filename):
    """HTML 파일 서빙 + 리로드 스크립트 주입"""
    filepath = os.path.join(DIST_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # </body> 앞에 리로드 스크립트 삽입
    content = content.replace('</body>', RELOAD_SCRIPT + '</body>')
    return Response(content, mimetype='text/html')


@app.errorhandler(404)
def not_found(e):
    return '<h1>404 - 페이지를 찾을 수 없습니다</h1><p><a href="/">홈으로</a></p>', 404


# ==========================================
# 메인
# ==========================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 개발 서버 (라이브 리로드)")
    print("=" * 60)

    # 초기 빌드
    run_build()

    # 파일 감시 시작
    handler = RebuildHandler()
    observer = Observer()
    for d in WATCH_DIRS:
        if os.path.exists(d):
            observer.schedule(handler, d, recursive=True)
            print(f"👀 감시 중: {os.path.relpath(d, BASE_DIR)}/")
    observer.start()

    print(f"\n🌐 http://localhost:3000")
    print("   종료: Ctrl+C\n")

    try:
        app.run(debug=False, port=3000, host='0.0.0.0', threaded=True)
    finally:
        observer.stop()
        observer.join()
