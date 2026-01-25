from flask import Flask, render_template, jsonify, request, redirect, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import Config
from models import db, File, SiteInfo, ActivityPhoto, BusinessArea, SponsorshipInfo
from models import HistorySection, HistoryItem, Notice, ActivityPost, Newsletter, DonationApplication, ActivityCategory
from models import AdminUser, BuildStatus
import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# ==========================================
# 로깅 설정
# ==========================================
if not app.debug:
    # 프로덕션 환경에서만 파일 로깅
    os.makedirs('logs', exist_ok=True)
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')
else:
    # 개발 환경에서도 간단한 로깅
    os.makedirs('logs', exist_ok=True)
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10240000,
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.DEBUG)

# 세션 비밀키 (반드시 변경해주세요)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

db.init_app(app)

# CORS 설정 (정적 사이트에서 API 호출 허용)
# 개발 환경에서는 모든 origin 허용
if app.config.get('DEBUG', True):
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
else:
    # 프로덕션에서는 특정 origin만 허용
    CORS(app, resources={
        r"/api/*": {
            "origins": Config.ALLOWED_ORIGINS,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        },
        r"/donation/*": {
            "origins": Config.ALLOWED_ORIGINS,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })

# 관리자 Blueprint 등록
from admin import admin_bp
app.register_blueprint(admin_bp)

# 업로드 폴더 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 빌드 트리거 시스템 활성화
from build_triggers import setup_build_triggers
setup_build_triggers(app)


# ==========================================
# 템플릿 필터
# ==========================================
@app.template_filter('fix_upload_urls')
def fix_upload_urls(content):
    """레거시 /static/uploads/ 경로를 /uploads/로 변환"""
    if not content:
        return content
    return content.replace('/static/uploads/', '/uploads/')


# ==========================================
# 컨텍스트 프로세서 (Admin 템플릿용)
# ==========================================
@app.context_processor
def inject_site_info():
    """사이트 정보를 모든 템플릿에 주입 (Admin 페이지용)"""
    site_info = SiteInfo.query.first()
    if site_info:
        site = site_info.to_dict()
    else:
        site = {}

    return {
        'site': site,
        'STATIC_SITE_URL': Config.STATIC_DOMAIN
    }


def allowed_file(filename):
    """허용된 파일 확장자인지 확인"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# ==========================================
# 파일 라우트 (dist/uploads 기준)
# ==========================================
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """업로드 파일 서빙 (dist/uploads에서)"""
    uploads_dir = os.path.join(app.root_path, 'dist', 'uploads')
    return send_from_directory(uploads_dir, filename)


@app.route('/download/<int:file_id>')
def download_file(file_id):
    """파일 다운로드 - Content-Disposition 헤더 설정"""
    file_record = File.query.get_or_404(file_id)
    uploads_dir = os.path.join(app.root_path, 'dist', 'uploads')
    return send_from_directory(
        uploads_dir,
        file_record.filename,
        as_attachment=True,
        download_name=file_record.original_filename
    )


# ==========================================
# 후원 신청 라우트 (동적 - POST만 유지)
# ==========================================
@app.route('/donation/apply', methods=['POST'])
def donation_apply():
    """후원 신청 처리"""
    # 금액 처리 (직접기입인 경우 custom 값 사용)
    amount_value = request.form.get('amount')
    if amount_value == 'other':
        amount = request.form.get('amount-custom', type=int) or 0
    else:
        amount = int(amount_value) if amount_value else 0

    try:
        application = DonationApplication(
            # 기본 정보
            name=request.form.get('name'),
            birth_year=request.form.get('birth_year', type=int),
            birth_month=request.form.get('birth_month', type=int),
            birth_day=request.form.get('birth_day', type=int),
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            occupation=request.form.get('occupation'),
            # 출금 정보
            account_number=request.form.get('account_number'),
            bank_name=request.form.get('bank_name'),
            resident_number=request.form.get('resident_number'),
            # 후원 정보
            amount=amount,
            withdrawal_date=request.form.get('withdrawal_date', type=int),
            # 동의 및 서명
            privacy_consent=(request.form.get('privacy_consent') == 'agree'),
            signature=request.form.get('signature')
        )
        db.session.add(application)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '후원 신청이 완료되었습니다.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'후원 신청 중 오류가 발생했습니다: {str(e)}'
        }), 500


# ==========================================
# API 라우트 (CMS용)
# ==========================================
@app.route('/api/notices')
def api_notices():
    """공지사항 API"""
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notices])


@app.route('/api/activities')
def api_activities():
    """활동후기 API"""
    posts = ActivityPost.query.order_by(ActivityPost.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts])


@app.route('/api/newsletters')
def api_newsletters():
    """소식지 API"""
    newsletters = Newsletter.query.order_by(Newsletter.published_at.desc()).all()
    return jsonify([n.to_dict() for n in newsletters])


@app.route('/api/business-areas')
def api_business_areas():
    """사업분야 API"""
    areas = BusinessArea.query.order_by(BusinessArea.display_order).all()
    return jsonify([a.to_dict() for a in areas])


@app.route('/api/history')
def api_history():
    """연혁 API"""
    sections = HistorySection.query.order_by(HistorySection.display_order).all()
    return jsonify([s.to_dict() for s in sections])


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """이미지 업로드 API"""
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다'}), 400

    if file and allowed_file(file.filename):
        # 고유한 파일명 생성
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        filename = secure_filename(filename)

        # 파일 저장 (uploads 폴더 바로 아래)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # URL 반환 (dist/uploads 기준)
        url = f'/uploads/{filename}'
        return jsonify({'url': url, 'filename': filename})

    return jsonify({'error': '허용되지 않는 파일 형식입니다'}), 400


@app.route('/api/notices/<int:id>', methods=['PUT'])
def api_update_notice(id):
    """공지사항 수정 API"""
    notice = Notice.query.get_or_404(id)
    data = request.get_json()

    if 'title' in data:
        notice.title = data['title']
    if 'content' in data:
        notice.content = data['content']
    if 'is_pinned' in data:
        notice.is_pinned = data['is_pinned']

    db.session.commit()
    return jsonify(notice.to_dict())


@app.route('/api/notices', methods=['POST'])
def api_create_notice():
    """공지사항 생성 API"""
    data = request.get_json()

    notice = Notice(
        title=data.get('title', ''),
        content=data.get('content', ''),
        is_pinned=data.get('is_pinned', False)
    )
    db.session.add(notice)
    db.session.commit()
    return jsonify(notice.to_dict()), 201


@app.route('/api/activities/<int:id>', methods=['PUT'])
def api_update_activity(id):
    """활동후기 수정 API"""
    post = ActivityPost.query.get_or_404(id)
    data = request.get_json()

    if 'title' in data:
        post.title = data['title']
    if 'content' in data:
        post.content = data['content']
    if 'category' in data:
        post.category = data['category']
    if 'thumbnail' in data:
        post.thumbnail = data['thumbnail']

    db.session.commit()
    return jsonify(post.to_dict())


@app.route('/api/activities', methods=['POST'])
def api_create_activity():
    """활동후기 생성 API"""
    data = request.get_json()

    post = ActivityPost(
        title=data.get('title', ''),
        content=data.get('content', ''),
        category=data.get('category'),
        thumbnail=data.get('thumbnail')
    )
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_dict()), 201


@app.route('/api/notices/<int:id>', methods=['DELETE'])
def api_delete_notice(id):
    """공지사항 삭제 API"""
    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/activities/<int:id>', methods=['DELETE'])
def api_delete_activity(id):
    """활동후기 삭제 API"""
    post = ActivityPost.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'success': True})


# 카테고리 API
@app.route('/api/categories')
def api_categories():
    """카테고리 목록 API"""
    categories = ActivityCategory.query.filter_by(is_active=True)\
        .order_by(ActivityCategory.display_order).all()
    return jsonify([c.to_dict() for c in categories])


@app.route('/api/categories', methods=['POST'])
def api_create_category():
    """카테고리 생성 API"""
    data = request.get_json()

    # 중복 체크
    existing = ActivityCategory.query.filter_by(name=data.get('name')).first()
    if existing:
        return jsonify({'error': '이미 존재하는 카테고리입니다'}), 400

    # 순서 자동 설정
    max_order = db.session.query(db.func.max(ActivityCategory.display_order)).scalar() or 0

    category = ActivityCategory(
        name=data.get('name', ''),
        color=data.get('color', '#6d28d9'),
        display_order=max_order + 1
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@app.route('/api/categories/<int:id>', methods=['PUT'])
def api_update_category(id):
    """카테고리 수정 API"""
    category = ActivityCategory.query.get_or_404(id)
    data = request.get_json()

    if 'name' in data:
        category.name = data['name']
    if 'color' in data:
        category.color = data['color']
    if 'display_order' in data:
        category.display_order = data['display_order']
    if 'is_active' in data:
        category.is_active = data['is_active']

    db.session.commit()
    return jsonify(category.to_dict())


@app.route('/api/categories/<int:id>', methods=['DELETE'])
def api_delete_category(id):
    """카테고리 삭제 API"""
    category = ActivityCategory.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'success': True})


# 사이트 정보 API
@app.route('/api/site-info')
def api_site_info():
    """사이트 정보 조회 API"""
    site_info = SiteInfo.query.first()
    if not site_info:
        return jsonify({})
    return jsonify(site_info.to_dict())


@app.route('/api/site-info', methods=['PUT'])
def api_update_site_info():
    """사이트 정보 수정 API"""
    data = request.get_json()

    site_info = SiteInfo.query.first()
    if not site_info:
        site_info = SiteInfo()
        db.session.add(site_info)

    # 각 필드 업데이트
    if 'org_name' in data:
        site_info.org_name = data['org_name']
    if 'site_name' in data:
        site_info.site_name = data['site_name']
    if 'slogan' in data:
        site_info.slogan = data['slogan']
    if 'intro_text' in data:
        site_info.intro_text = data['intro_text']
    if 'address' in data:
        site_info.address = data['address']
    if 'tel' in data:
        site_info.tel = data['tel']
    if 'fax' in data:
        site_info.fax = data['fax']
    if 'email' in data:
        site_info.email = data['email']
    if 'facebook' in data:
        site_info.facebook = data['facebook']
    if 'instagram' in data:
        site_info.instagram = data['instagram']
    if 'youtube' in data:
        site_info.youtube = data['youtube']
    if 'representative' in data:
        site_info.representative = data['representative']
    if 'registration_number' in data:
        site_info.registration_number = data['registration_number']
    if 'bank_name' in data:
        site_info.bank_name = data['bank_name']
    if 'bank_account' in data:
        site_info.bank_account = data['bank_account']
    if 'bank_holder' in data:
        site_info.bank_holder = data['bank_holder']

    db.session.commit()
    return jsonify({'success': True})


# 후원안내 API
@app.route('/api/sponsorship')
def api_sponsorship():
    """후원안내 조회 API"""
    sponsorship = SponsorshipInfo.query.first()
    if not sponsorship:
        return jsonify(None)
    return jsonify({
        'appeal_text': sponsorship.appeal_text,
        'volunteer_summary': sponsorship.volunteer_summary,
        'volunteer_details': sponsorship.volunteer_details or [],
        'donation_summary': sponsorship.donation_summary,
        'donation_details': sponsorship.donation_details or []
    })


@app.route('/api/sponsorship', methods=['PUT'])
def api_update_sponsorship():
    """후원안내 수정 API"""
    data = request.get_json()
    sponsorship = SponsorshipInfo.query.first()

    if not sponsorship:
        sponsorship = SponsorshipInfo()
        db.session.add(sponsorship)

    sponsorship.appeal_text = data.get('appeal_text', '')
    sponsorship.volunteer_summary = data.get('volunteer_summary', '')
    sponsorship.volunteer_details = data.get('volunteer_details', [])
    sponsorship.donation_summary = data.get('donation_summary', '')
    sponsorship.donation_details = data.get('donation_details', [])

    db.session.commit()
    return jsonify({'success': True})


# 연혁 API (CRUD)
@app.route('/api/history-sections', methods=['POST'])
def api_create_history_section():
    """연혁 섹션 생성 API"""
    data = request.get_json()

    max_order = db.session.query(db.func.max(HistorySection.display_order)).scalar() or 0

    section = HistorySection(
        subtitle=data.get('subtitle', ''),
        summary=data.get('summary', ''),
        summary_title=data.get('summary_title', ''),
        display_order=max_order + 1
    )
    db.session.add(section)
    db.session.commit()
    return jsonify(section.to_dict()), 201


@app.route('/api/history-sections/<int:id>', methods=['PUT'])
def api_update_history_section(id):
    """연혁 섹션 수정 API"""
    section = HistorySection.query.get_or_404(id)
    data = request.get_json()

    if 'subtitle' in data:
        section.subtitle = data['subtitle']
    if 'summary' in data:
        section.summary = data['summary']
    if 'summary_title' in data:
        section.summary_title = data['summary_title']
    if 'display_order' in data:
        section.display_order = data['display_order']

    db.session.commit()
    return jsonify(section.to_dict())


@app.route('/api/history-sections/<int:id>', methods=['DELETE'])
def api_delete_history_section(id):
    """연혁 섹션 삭제 API"""
    # 마지막 하나는 삭제 불가
    count = HistorySection.query.count()
    if count <= 1:
        return jsonify({'error': '최소 1개의 연혁 섹션이 필요합니다.'}), 400

    section = HistorySection.query.get_or_404(id)
    # 섹션의 모든 항목도 삭제
    HistoryItem.query.filter_by(section_id=id).delete()
    db.session.delete(section)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/history-items', methods=['POST'])
def api_create_history_item():
    """연혁 항목 생성 API"""
    data = request.get_json()

    # 해당 섹션의 최대 순서 가져오기
    section_id = data.get('section_id')
    max_order = db.session.query(db.func.max(HistoryItem.display_order))\
        .filter(HistoryItem.section_id == section_id).scalar() or 0

    item = HistoryItem(
        section_id=section_id,
        year=data.get('year'),
        content=data.get('content', ''),
        display_order=max_order + 1
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.route('/api/history-items/<int:id>', methods=['PUT'])
def api_update_history_item(id):
    """연혁 항목 수정 API"""
    item = HistoryItem.query.get_or_404(id)
    data = request.get_json()

    if 'year' in data:
        item.year = data['year']
    if 'content' in data:
        item.content = data['content']
    if 'display_order' in data:
        item.display_order = data['display_order']

    db.session.commit()
    return jsonify(item.to_dict())


@app.route('/api/history-items/<int:id>', methods=['DELETE'])
def api_delete_history_item(id):
    """연혁 항목 삭제 API"""
    item = HistoryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


# 사업분야 API (CRUD)
@app.route('/api/business-areas', methods=['POST'])
def api_create_business_area():
    """사업분야 생성 API"""
    data = request.get_json()

    max_order = db.session.query(db.func.max(BusinessArea.display_order)).scalar() or 0

    area = BusinessArea(
        name=data.get('name', ''),
        description=data.get('description', ''),
        details=data.get('details', []),
        photo_url=data.get('photo_url', ''),
        display_order=max_order + 1
    )
    db.session.add(area)
    db.session.commit()
    return jsonify(area.to_dict()), 201


@app.route('/api/business-areas/<int:id>', methods=['PUT'])
def api_update_business_area(id):
    """사업분야 수정 API"""
    area = BusinessArea.query.get_or_404(id)
    data = request.get_json()

    if 'name' in data:
        area.name = data['name']
    if 'description' in data:
        area.description = data['description']
    if 'details' in data:
        area.details = data['details']
    if 'photo_url' in data:
        area.photo_url = data['photo_url']
    if 'display_order' in data:
        area.display_order = data['display_order']
    if 'is_active' in data:
        area.is_active = data['is_active']

    db.session.commit()
    return jsonify(area.to_dict())


@app.route('/api/business-areas/<int:id>', methods=['DELETE'])
def api_delete_business_area(id):
    """사업분야 삭제 API"""
    # 마지막 하나는 삭제 불가
    count = BusinessArea.query.count()
    if count <= 1:
        return jsonify({'error': '최소 1개의 사업분야가 필요합니다.'}), 400

    area = BusinessArea.query.get_or_404(id)
    db.session.delete(area)
    db.session.commit()
    return jsonify({'success': True})


# 주요 활동사진 API (CRUD)
@app.route('/api/activity-photos')
def api_activity_photos():
    """주요 활동사진 목록 API"""
    photos = ActivityPhoto.query.order_by(ActivityPhoto.display_order).all()
    result = []
    for photo in photos:
        data = {
            'id': photo.id,
            'description': photo.description,
            'taken_at': photo.taken_at.isoformat() if photo.taken_at else None,
            'display_order': photo.display_order,
            'is_active': photo.is_active,
            'image_url': photo.image_url if hasattr(photo, 'image_url') else None
        }
        if photo.file:
            data['image_url'] = f'/uploads/{photo.file.filename}'
        result.append(data)
    return jsonify(result)


@app.route('/api/activity-photos', methods=['POST'])
def api_create_activity_photo():
    """주요 활동사진 생성 API"""
    data = request.get_json()

    max_order = db.session.query(db.func.max(ActivityPhoto.display_order)).scalar() or 0

    photo = ActivityPhoto(
        description=data.get('description', ''),
        taken_at=datetime.strptime(data['taken_at'], '%Y-%m-%d').date() if data.get('taken_at') else None,
        display_order=max_order + 1,
        is_active=data.get('is_active', True)
    )

    # 이미지 URL로부터 file_id 연결 (선택적)
    image_url = data.get('image_url', '')
    if image_url:
        # URL에서 파일명 추출하여 저장
        photo.image_url = image_url

    db.session.add(photo)
    db.session.commit()

    return jsonify({
        'id': photo.id,
        'description': photo.description,
        'taken_at': photo.taken_at.isoformat() if photo.taken_at else None,
        'display_order': photo.display_order,
        'is_active': photo.is_active,
        'image_url': getattr(photo, 'image_url', None)
    }), 201


@app.route('/api/activity-photos/<int:id>', methods=['PUT'])
def api_update_activity_photo(id):
    """주요 활동사진 수정 API"""
    photo = ActivityPhoto.query.get_or_404(id)
    data = request.get_json()

    if 'description' in data:
        photo.description = data['description']
    if 'taken_at' in data:
        photo.taken_at = datetime.strptime(data['taken_at'], '%Y-%m-%d').date() if data['taken_at'] else None
    if 'display_order' in data:
        photo.display_order = data['display_order']
    if 'is_active' in data:
        photo.is_active = data['is_active']
    if 'image_url' in data:
        photo.image_url = data['image_url']

    db.session.commit()

    return jsonify({
        'id': photo.id,
        'description': photo.description,
        'taken_at': photo.taken_at.isoformat() if photo.taken_at else None,
        'display_order': photo.display_order,
        'is_active': photo.is_active,
        'image_url': getattr(photo, 'image_url', None)
    })


@app.route('/api/activity-photos/<int:id>', methods=['DELETE'])
def api_delete_activity_photo(id):
    """주요 활동사진 삭제 API"""
    # 마지막 하나는 삭제 불가
    count = ActivityPhoto.query.count()
    if count <= 1:
        return jsonify({'error': '최소 1개의 활동사진이 필요합니다.'}), 400

    photo = ActivityPhoto.query.get_or_404(id)
    db.session.delete(photo)
    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# CLI 명령어
# ==========================================
@app.cli.command('init-db')
def init_db():
    """데이터베이스 초기화"""
    db.create_all()
    print('Database initialized.')


@app.cli.command('create-admin')
def create_admin():
    """슈퍼관리자 계정 생성"""
    import getpass

    username = input('아이디: ').strip()
    if not username:
        print('아이디를 입력해주세요.')
        return

    if AdminUser.query.filter_by(username=username).first():
        print('이미 존재하는 아이디입니다.')
        return

    password = getpass.getpass('비밀번호: ')
    if not password:
        print('비밀번호를 입력해주세요.')
        return

    name = input('이름 (선택): ').strip() or username

    admin = AdminUser(
        username=username,
        name=name,
        role='super_admin'
    )
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    print(f'슈퍼관리자 계정이 생성되었습니다: {username}')


# @app.cli.command('seed-db')
# def seed_db():
#     """샘플 데이터 삽입"""
#     # 사이트 정보
#     site_info = SiteInfo.query.first()
#     if not site_info:
#         site_info = SiteInfo(
#             org_name='사단법인 함께하는세상',
#             site_name='양산외국인노동자의집',
#             slogan='더불어 사는 세상',
#             intro_text='고향을 떠나 낯선 이국땅에서 꿈을 키우며 더불어 살아가는 이주민들과 함께 만듭니다',
#             address='경상남도 양산시 북안북7길35 양산시근로자종합복지관 1층',
#             tel='055-388-0988',
#             fax='055-366-0988',
#             email='happysoli@hanmail.net',
#             facebook='https://www.facebook.com/yangsanmigrant',
#             representative='김덕한',
#             bank_name='농협',
#             bank_account='301-0135-5765-11',
#             bank_holder='(사)함께하는세상',
#         )
#         db.session.add(site_info)

#     # 주요 사업분야
#     areas = [
#         BusinessArea(
#             name='인권상담',
#             description='이주민들이 일터와 일상에서 겪게 되는 인권 침해를 예방하고 해결을 지원합니다.',
#             details=[
#                 '상담 내용: 임금 체불, 퇴직금, 산재, 사고, 폭행, 출입국 관련, 사망 등',
#                 '상담 방법: 전화, 방문, 온라인 상담 가능',
#                 '법률 지원: 노무사, 변호사 연계를 통한 전문적인 법률 상담 및 소송 지원',
#                 '통역 서비스: 다양한 언어로 상담 가능 (베트남어, 태국어, 캄보디아어 등)'
#             ],
#             display_order=1
#         ),
#         BusinessArea(
#             name='쉼터',
#             description='인권 침해를 당한 이주민들이 안전하게 지내며 문제를 해결할 수 있도록 쉼터를 운영합니다.',
#             details=[
#                 '긴급 쉼터: 사업장 이탈, 폭행 피해 등 긴급한 상황의 이주민 보호',
#                 '숙식 제공: 안전한 주거 공간과 식사 제공',
#                 '심리 상담: 트라우마 치료 및 심리적 안정 지원',
#                 '문제 해결: 법률 상담 및 재취업 지원을 통한 근본적 문제 해결'
#             ],
#             display_order=2
#         ),
#         BusinessArea(
#             name='교육',
#             description='이주민들의 욕구에 맞는 교육 프로그램을 운영하여 한국생활 적응과 권리 찾기를 지원합니다.',
#             details=[
#                 '한국어 교육: 초급부터 고급까지 수준별 한국어 수업',
#                 '인권 교육: 노동권, 체류권 등 이주민 권리에 대한 교육',
#                 '문화 체험: 한국 문화 이해 및 다문화 교류 프로그램',
#                 '직업 교육: 기술 교육 및 취업 지원 프로그램'
#             ],
#             display_order=3
#         ),
#     ]
#     for a in areas:
#         existing = BusinessArea.query.filter_by(name=a.name).first()
#         if not existing:
#             db.session.add(a)

#     # 후원 안내
#     sponsorship = SponsorshipInfo.query.first()
#     if not sponsorship:
#         sponsorship = SponsorshipInfo(
#             appeal_text='(사)함께하는세상 양산외국인노동자의집은 여러분의 후원금과 자원활동으로 이뤄지고 있습니다. 이주민들과 함께 하고, 이주민 인권과 다문화 사회를 만들어 가는 데에 관심있는 분들을 기다립니다.',
#             volunteer_summary='이주민 인권과 다문화 사회를 만들어 가는데 관심을 가지고 이 활동에 함께 할 자원 활동가를 기다리고 있습니다.',
#             volunteer_details=['교육활동지원', '의료보조', '행사진행보조', '홍보활동지원'],
#             donation_summary='이주민들과 함께 하고자 하는 여러분의 관심과 지원의 손길을 기다리고 있습니다.',
#             donation_details=['일반후원: 정기후원회원으로 사무실 운영 지원']
#         )
#         db.session.add(sponsorship)

#     # 연혁
#     if not HistorySection.query.first():
#         section1 = HistorySection(
#             subtitle='시작',
#             summary='1997년 양산 지역 이주민 지원 활동 시작',
#             summary_title='함께의 시작',
#             display_order=1
#         )
#         db.session.add(section1)
#         db.session.flush()

#         items = [
#             HistoryItem(section_id=section1.id, year=1997, content='양산 지역 이주민 지원 활동 시작', display_order=1),
#             HistoryItem(section_id=section1.id, year=2000, content='사단법인 함께하는세상 설립', display_order=2),
#             HistoryItem(section_id=section1.id, year=2005, content='양산외국인노동자의집 개소', display_order=3),
#         ]
#         for item in items:
#             db.session.add(item)

#     db.session.commit()
#     print('Sample data seeded.')


if __name__ == '__main__':
    app.run(debug=True, port=8000)
