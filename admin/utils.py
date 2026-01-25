"""
관리자 페이지 유틸리티
"""
import os
import uuid
import re
import requests
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from flask import current_app
from models import db, File

# 허용 파일 확장자
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'hwp', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip'}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename, allowed=None):
    """파일 확장자 확인"""
    if allowed is None:
        allowed = ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def save_uploaded_file(file, allowed=None):
    """
    업로드된 파일 저장 및 File 레코드 생성
    Returns: File 객체 또는 None
    """
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename, allowed):
        return None

    # 파일 크기 확인
    file.seek(0, 2)  # 파일 끝으로 이동
    size = file.tell()
    file.seek(0)  # 파일 시작으로 복귀

    if size > MAX_FILE_SIZE:
        return None

    # 원본 파일명 보존 (한글 등 유니코드 지원)
    original_filename = file.filename

    # 확장자 추출
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

    # 저장용 고유 파일명 (UUID 기반)
    unique_filename = f"{uuid.uuid4().hex}.{ext}"

    # 저장 경로 (dist/uploads)
    upload_folder = os.path.join(current_app.root_path, 'dist', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, unique_filename)
    file.save(filepath)

    # File 레코드 생성
    file_record = File(
        filename=unique_filename,
        original_filename=original_filename,
        mimetype=file.content_type,
        size=size
    )
    db.session.add(file_record)
    db.session.flush()

    return file_record


def save_base64_image(base64_data):
    """
    Base64 이미지를 파일로 저장
    Args:
        base64_data: data:image/png;base64,... 형태의 문자열
    Returns: File 객체 또는 None
    """
    import base64

    try:
        # data:image/png;base64,... 형식 파싱
        if ',' in base64_data:
            header, data = base64_data.split(',', 1)
            # MIME 타입 추출
            mime_match = re.search(r'data:([^;]+);', header)
            mimetype = mime_match.group(1) if mime_match else 'image/png'
        else:
            data = base64_data
            mimetype = 'image/png'

        # 확장자 결정
        ext_map = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp'
        }
        ext = ext_map.get(mimetype, 'png')

        # 디코딩
        image_data = base64.b64decode(data)
        size = len(image_data)

        if size > MAX_FILE_SIZE:
            return None

        # 파일명 생성
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        original_filename = f"pasted_image.{ext}"

        # 저장 경로 (dist/uploads)
        upload_folder = os.path.join(current_app.root_path, 'dist', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)
        with open(filepath, 'wb') as f:
            f.write(image_data)

        # File 레코드 생성
        file_record = File(
            filename=unique_filename,
            original_filename=original_filename,
            mimetype=mimetype,
            size=size
        )
        db.session.add(file_record)
        db.session.flush()

        return file_record

    except Exception as e:
        print(f"Base64 이미지 저장 오류: {e}")
        return None


def extract_image_urls(html_content):
    """
    HTML 콘텐츠에서 이미지 URL 추출
    Returns: set of image URLs
    """
    if not html_content:
        return set()

    urls = set()
    # /uploads/ 경로의 이미지만 추출 (dist/uploads 기준)
    pattern = r'/uploads/[a-f0-9_]+\.(png|jpg|jpeg|gif|webp)'
    matches = re.findall(pattern, html_content, re.IGNORECASE)

    # 전체 URL 추출
    full_pattern = r'(/uploads/[a-f0-9_]+\.(?:png|jpg|jpeg|gif|webp))'
    full_matches = re.findall(full_pattern, html_content, re.IGNORECASE)

    return set(full_matches)


def cleanup_orphaned_images(old_content, new_content):
    """
    이전 콘텐츠에는 있지만 새 콘텐츠에는 없는 이미지 삭제
    Returns: 삭제된 파일 수
    """
    old_urls = extract_image_urls(old_content)
    new_urls = extract_image_urls(new_content)

    orphaned_urls = old_urls - new_urls
    deleted_count = 0

    for url in orphaned_urls:
        # URL에서 파일명 추출 (예: /uploads/abc123.jpg -> abc123.jpg)
        filename = url.replace('/uploads/', '')

        # 파일 경로 (dist/uploads 기준)
        filepath = os.path.join(current_app.root_path, 'dist', 'uploads', filename)

        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted_count += 1

                # File 레코드도 삭제
                file_record = File.query.filter_by(filename=filename).first()
                if file_record:
                    db.session.delete(file_record)
        except Exception as e:
            print(f"이미지 삭제 실패: {filepath} - {e}")

    return deleted_count


def crawl_stibee_content(url):
    """
    Stibee 뉴스레터 URL에서 콘텐츠 크롤링
    Returns: dict with title, html_content, or error
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 제목 추출
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()

        # Stibee 뉴스레터 본문 추출
        html_content = None

        # stib.ee 페이지 구조에서 본문 찾기
        inner = soup.select_one('.public-email .inner')
        if inner:
            html_content = str(inner)
        else:
            # 대안: body 전체
            body = soup.find('body')
            if body:
                # 불필요한 스크립트/스타일 제거
                for tag in body.find_all(['script', 'style', 'nav', 'footer']):
                    tag.decompose()
                html_content = str(body)

        # 제목에서 호수 추출 시도
        issue_number = None
        if title:
            match = re.search(r'제?(\d+)호', title)
            if match:
                issue_number = int(match.group(1))

        return {
            'title': title,
            'html_content': html_content,
            'issue_number': issue_number,
            'external_url': url
        }

    except requests.RequestException as e:
        return {'error': f'크롤링 실패: {str(e)}'}
    except Exception as e:
        return {'error': f'오류 발생: {str(e)}'}
