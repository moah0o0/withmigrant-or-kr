from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)

# dist 폴더 경로
DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')


@app.route('/')
def index():
    """메인 페이지"""
    return send_from_directory(DIST_DIR, 'index.html')


@app.route('/<path:filename>')
def serve_file(filename):
    """모든 파일 서빙"""
    file_path = os.path.join(DIST_DIR, filename)
    print(file_path)

    # 파일이 존재하면 서빙
    if os.path.isfile(file_path):
        return send_from_directory(DIST_DIR, filename)

    # 디렉토리면 index.html 찾기
    if os.path.isdir(file_path):
        index_file = os.path.join(filename, 'index.html')
        if os.path.isfile(os.path.join(DIST_DIR, index_file)):
            return send_from_directory(DIST_DIR, index_file)

    # .html 확장자 추가 시도
    html_file = filename if filename.endswith('.html') else f'{filename}.html'
    if os.path.isfile(os.path.join(DIST_DIR, html_file)):
        return send_from_directory(DIST_DIR, html_file)

    abort(404)


@app.errorhandler(404)
def not_found(e):
    """404 에러 핸들러"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>404 Not Found</title>
        <style>
            body {{ font-family: sans-serif; text-align: center; padding: 50px; }}
            h1 {{ color: #666; }}
        </style>
    </head>
    <body>
        <h1>404 - 페이지를 찾을 수 없습니다</h1>
        <p><a href="/">홈으로 돌아가기</a></p>
    </body>
    </html>
    """, 404


if __name__ == '__main__':
    print("=" * 60)
    print("SSG 정적 파일 서버")
    print("=" * 60)
    print(f"서빙 디렉토리: {os.path.abspath(DIST_DIR)}")
    print("서버 주소: http://localhost:3000")
    print("종료: Ctrl+C")
    print("=" * 60)

    app.run(debug=True, port=3000, host='0.0.0.0')
