import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """통합 설정 클래스 - Flask 앱 및 SSG 빌드 설정"""

    # ============================================
    # Flask 기본 설정
    # ============================================
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ============================================
    # 도메인 설정 (개발/배포 환경)
    # ============================================
    # 정적 사이트가 배포될 도메인 (프로덕션 기본값)
    STATIC_DOMAIN = os.environ.get('STATIC_DOMAIN', 'https://withmigrant.or.kr')

    # 동적 API/Admin이 배포될 도메인 (프로덕션 기본값)
    API_DOMAIN = os.environ.get('API_DOMAIN', 'https://admin.withmigrant.or.kr')

    # CORS 허용 도메인 (프로덕션)
    ALLOWED_ORIGINS = [
        'https://withmigrant.or.kr',
        'https://www.withmigrant.or.kr',
    ]

    # ============================================
    # 파일 업로드 설정
    # ============================================
    UPLOAD_FOLDER = os.path.join(basedir, 'dist', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    MAX_TOTAL_STORAGE = 10 * 1024 * 1024 * 1024  # 10GB 전체 업로드 용량 제한
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

    # ============================================
    # Cloudflare R2 설정
    # ============================================
    R2_ACCOUNT_ID = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '')
    R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID', '')
    R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'withmigrant-uploads')
    R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', 'https://uploads.withmigrant.or.kr')

    # ============================================
    # 이메일 설정
    # ============================================
    DONATION_EMAIL = os.environ.get('DONATION_EMAIL') or 'happysoli@hanmail.net'

    # ============================================
    # 로고 텍스트 색상 설정
    # ============================================
    # 'black', '#3a1671'(보라), 또는 아무 CSS 색상값
    LOGO_TEXT_COLOR = '#3a1671'

    # ============================================
    # SSG 빌드 설정
    # ============================================
    BASE_DIR = basedir
    DIST_DIR = os.path.join(basedir, 'dist')

    # SEO 기본 설정
    SEO_DEFAULTS = {
        'site_name': '양산외국인노동자의집',
        'description': '(사)함께하는세상 양산외국인노동자의집',
        'keywords': '양산, 외국인노동자, 이주민, 인권상담, 쉼터',
        'og_image': '/static/images/og-image.png',
        'twitter_card': 'summary_large_image',
    }

    # 페이지별 SEO 설정
    SEO_PAGES = {
        'index': {
            'title': '양산외국인노동자의집',
            'description': '(사)함께하는세상 양산외국인노동자의집 공식 홈페이지',
        },
        'intro': {
            'title': '소개',
            'description': '양산외국인노동자의집 소개 - 연혁, 주요 사업분야, 찾아오시는 길 안내',
        },
        'notice_list': {
            'title': '공지사항',
            'description': '양산외국인노동자의집 공지사항 및 소식',
        },
        'activity_list': {
            'title': '활동후기',
            'description': '양산외국인노동자의집 활동 후기 및 사진',
        },
        'newsletter_list': {
            'title': '소식지',
            'description': '양산외국인노동자의집 정기 소식지',
        },
        'donation': {
            'title': '함께하기',
            'description': '양산외국인노동자의집 후원 및 자원활동 안내',
        },
    }

    # 페이지네이션 설정
    PAGINATION = {
        'notice': 10,
        'activity': 12,
        'newsletter': 12,
    }

    # 빌드 제외 파일 패턴
    EXCLUDE_PATTERNS = [
        '*.pyc',
        '__pycache__',
        '.DS_Store',
        '.git',
        'uploads/*',
    ]

    # 정적 파일 복사 설정
    STATIC_COPY = {
        'css': True,
        'js': True,
        'images': True,
        'uploads': False,
    }
