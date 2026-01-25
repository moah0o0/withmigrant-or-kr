"""
관리자 페이지 라우트
"""
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from models import (
    db, AdminUser, Notice, ActivityPost, Newsletter,
    DonationApplication, SiteInfo, BusinessArea, VolunteerArea, DonationArea, DonationUsage,
    HistorySection, HistoryItem, ActivityPhoto, ActivityCategory, File,
    BusStop, BusRoute, OperatingHours, OfficeInfo, BuildStatus
)
from . import admin_bp
from .auth import login_required, super_admin_required, get_current_admin
import re


def normalize_upload_urls(text):
    """레거시 /static/uploads/ 경로를 /uploads/로 정규화"""
    if not text:
        return text
    return text.replace('/static/uploads/', '/uploads/')


# ==========================================
# 인증
# ==========================================
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    # 이미 로그인되어 있으면 대시보드로
    if 'admin_id' in session:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = AdminUser.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            if not admin.is_active:
                flash('계정이 비활성화되었습니다. 관리자에게 문의하세요.', 'error')
                return render_template('admin/login.html')

            # 로그인 성공
            session['admin_id'] = admin.id
            session['admin_role'] = admin.role
            session['admin_name'] = admin.name or admin.username

            # 마지막 로그인 시간 업데이트
            admin.last_login = datetime.utcnow()
            db.session.commit()

            flash(f'{admin.name or admin.username}님, 환영합니다!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'error')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """로그아웃"""
    session.clear()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('admin.login'))


# ==========================================
# 대시보드
# ==========================================
@admin_bp.route('/')
@login_required
def dashboard():
    """대시보드"""
    admin = get_current_admin()

    # 통계
    stats = {
        'notices': Notice.query.count(),
        'activities': ActivityPost.query.count(),
        'newsletters': Newsletter.query.count(),
        'donations_pending': DonationApplication.query.filter_by(is_processed=False).count()
    }

    # 최근 활동 (공지사항, 활동후기 최신 5개씩)
    recent_notices = Notice.query.order_by(Notice.created_at.desc()).limit(3).all()
    recent_activities = ActivityPost.query.order_by(ActivityPost.created_at.desc()).limit(3).all()
    recent_newsletters = Newsletter.query.order_by(Newsletter.created_at.desc()).limit(2).all()

    return render_template('admin/dashboard.html',
                           admin=admin,
                           stats=stats,
                           recent_notices=recent_notices,
                           recent_activities=recent_activities,
                           recent_newsletters=recent_newsletters)


# ==========================================
# 공지사항 관리
# ==========================================
@admin_bp.route('/notices')
@login_required
def notices_list():
    """공지사항 목록"""
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')

    query = Notice.query

    if q:
        query = query.filter(Notice.title.contains(q))

    # 고정 공지 먼저, 그 다음 최신순
    query = query.order_by(Notice.is_pinned.desc(), Notice.created_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    return render_template('admin/notices/list.html',
                           pagination=pagination,
                           q=q)


@admin_bp.route('/notices/new', methods=['GET', 'POST'])
@login_required
def notices_new():
    """공지사항 작성"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = normalize_upload_urls(request.form.get('content', ''))
        is_pinned = request.form.get('is_pinned') == 'on'
        created_at_str = request.form.get('created_at', '')

        if not title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('admin/notices/form.html', notice=None)

        notice = Notice(
            title=title,
            content=content,
            is_pinned=is_pinned
        )

        # 작성일 처리
        if created_at_str:
            try:
                notice.created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        db.session.add(notice)
        db.session.flush()

        # 첨부파일 처리
        if 'attachments' in request.files:
            from .utils import save_uploaded_file
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    file_record = save_uploaded_file(file)
                    if file_record:
                        notice.attachments.append(file_record)

        db.session.commit()

        flash('공지사항이 등록되었습니다.', 'success')
        return redirect(url_for('admin.notices_list'))

    return render_template('admin/notices/form.html', notice=None)


@admin_bp.route('/notices/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def notices_edit(id):
    """공지사항 수정"""
    notice = Notice.query.get_or_404(id)

    if request.method == 'POST':
        # 이전 콘텐츠 저장 (이미지 정리용)
        old_content = notice.content or ''

        notice.title = request.form.get('title', '').strip()
        notice.content = normalize_upload_urls(request.form.get('content', ''))
        notice.is_pinned = request.form.get('is_pinned') == 'on'
        created_at_str = request.form.get('created_at', '')

        if not notice.title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('admin/notices/form.html', notice=notice)

        # 작성일 처리
        if created_at_str:
            try:
                notice.created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        # 새 첨부파일 처리
        if 'attachments' in request.files:
            from .utils import save_uploaded_file
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    file_record = save_uploaded_file(file)
                    if file_record:
                        notice.attachments.append(file_record)

        db.session.commit()

        # 삭제된 이미지 정리
        from .utils import cleanup_orphaned_images
        cleanup_orphaned_images(old_content, notice.content or '')

        flash('공지사항이 수정되었습니다.', 'success')
        return redirect(url_for('admin.notices_list'))

    return render_template('admin/notices/form.html', notice=notice)


@admin_bp.route('/notices/<int:id>/attachments/<int:file_id>/delete', methods=['POST'])
@login_required
def notices_attachment_delete(id, file_id):
    """공지사항 첨부파일 삭제"""
    notice = Notice.query.get_or_404(id)
    file_record = File.query.get_or_404(file_id)

    if file_record in notice.attachments:
        # 1. 관계 끊기
        notice.attachments.remove(file_record)

        # 2. 실제 파일 삭제
        import os
        from config import Config
        filepath = os.path.join(Config.DIST_DIR, 'uploads', file_record.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

        # 3. File 레코드 삭제
        db.session.delete(file_record)
        db.session.commit()

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.notices_edit', id=id))


@admin_bp.route('/notices/<int:id>/delete', methods=['POST'])
@login_required
def notices_delete(id):
    """공지사항 삭제"""
    notice = Notice.query.get_or_404(id)

    # 1. 첨부파일 삭제 (관계 끊고 파일 삭제)
    import os
    from config import Config
    attachments_to_delete = list(notice.attachments)  # 복사
    notice.attachments.clear()  # 관계 먼저 끊기

    for attachment in attachments_to_delete:
        # 실제 파일 삭제
        filepath = os.path.join(Config.DIST_DIR, 'uploads', attachment.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        # File 레코드 삭제
        db.session.delete(attachment)

    # 2. 본문 내 이미지 삭제
    from .utils import cleanup_all_content_images
    cleanup_all_content_images(notice.content)

    # 3. dist 폴더의 HTML 파일 삭제
    html_path = os.path.join(Config.DIST_DIR, 'notice', f'{id}.html')
    if os.path.exists(html_path):
        os.remove(html_path)

    # 4. DB에서 게시물 삭제
    db.session.delete(notice)
    db.session.commit()

    flash('공지사항이 삭제되었습니다.', 'success')

    # HTMX 요청이면 빈 응답
    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.notices_list'))


@admin_bp.route('/notices/<int:id>/toggle-pin', methods=['POST'])
@login_required
def notices_toggle_pin(id):
    """공지사항 고정 토글"""
    notice = Notice.query.get_or_404(id)
    notice.is_pinned = not notice.is_pinned
    db.session.commit()

    if request.headers.get('HX-Request'):
        return jsonify({'is_pinned': notice.is_pinned})

    return redirect(url_for('admin.notices_list'))


# ==========================================
# 활동후기 관리
# ==========================================
@admin_bp.route('/activities')
@login_required
def activities_list():
    """활동후기 목록"""
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    category = request.args.get('category', '')

    query = ActivityPost.query

    if q:
        query = query.filter(ActivityPost.title.contains(q))
    if category:
        if category == '__none__':
            query = query.filter((ActivityPost.category == None) | (ActivityPost.category == ''))
        else:
            query = query.filter(ActivityPost.category == category)

    query = query.order_by(ActivityPost.created_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    # 필터 드롭다운용 활성 카테고리
    active_categories = ActivityCategory.query.filter_by(is_active=True).order_by(ActivityCategory.display_order).all()
    # 색상 표시용 모든 카테고리
    all_categories = ActivityCategory.query.order_by(ActivityCategory.display_order).all()

    return render_template('admin/activities/list.html',
                           pagination=pagination,
                           categories=active_categories,
                           all_categories=all_categories,
                           q=q,
                           current_category=category)


@admin_bp.route('/activities/new', methods=['GET', 'POST'])
@login_required
def activities_new():
    """활동후기 작성"""
    categories = ActivityCategory.query.filter_by(is_active=True).order_by(ActivityCategory.display_order).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        category = request.form.get('category', '')
        thumbnail_url = request.form.get('thumbnail_url', '')
        created_at_str = request.form.get('created_at', '')

        if not title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('admin/activities/form.html', activity=None, categories=categories)

        # URL 정규화
        content = normalize_upload_urls(content)
        thumbnail_url = normalize_upload_urls(thumbnail_url) if thumbnail_url else None

        activity = ActivityPost(
            title=title,
            content=content,
            category=category,
            thumbnail_url=thumbnail_url
        )

        # 작성일 처리
        if created_at_str:
            try:
                activity.created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        # 썸네일 파일 업로드 처리
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename:
                from .utils import save_uploaded_file
                file_record = save_uploaded_file(file)
                if file_record:
                    activity.thumbnail_file_id = file_record.id

        db.session.add(activity)
        db.session.flush()

        # 첨부파일 처리
        if 'attachments' in request.files:
            from .utils import save_uploaded_file
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    file_record = save_uploaded_file(file)
                    if file_record:
                        activity.attachments.append(file_record)

        db.session.commit()

        flash('활동후기가 등록되었습니다.', 'success')
        return redirect(url_for('admin.activities_list'))

    return render_template('admin/activities/form.html', activity=None, categories=categories)


@admin_bp.route('/activities/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def activities_edit(id):
    """활동후기 수정"""
    activity = ActivityPost.query.get_or_404(id)
    categories = ActivityCategory.query.filter_by(is_active=True).order_by(ActivityCategory.display_order).all()

    if request.method == 'POST':
        # 이전 콘텐츠 저장 (이미지 정리용)
        old_content = activity.content or ''

        activity.title = request.form.get('title', '').strip()
        activity.content = normalize_upload_urls(request.form.get('content', ''))
        activity.category = request.form.get('category', '')
        created_at_str = request.form.get('created_at', '')

        thumbnail_url = request.form.get('thumbnail_url', '')
        if thumbnail_url:
            activity.thumbnail_url = normalize_upload_urls(thumbnail_url)

        if not activity.title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('admin/activities/form.html', activity=activity, categories=categories)

        # 작성일 처리
        if created_at_str:
            try:
                activity.created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        # 썸네일 파일 업로드 처리
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename:
                from .utils import save_uploaded_file
                file_record = save_uploaded_file(file)
                if file_record:
                    activity.thumbnail_file_id = file_record.id
                    activity.thumbnail_url = None  # 파일 업로드 시 URL 초기화

        # 새 첨부파일 처리
        if 'attachments' in request.files:
            from .utils import save_uploaded_file
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    file_record = save_uploaded_file(file)
                    if file_record:
                        activity.attachments.append(file_record)

        db.session.commit()

        # 삭제된 이미지 정리
        from .utils import cleanup_orphaned_images
        cleanup_orphaned_images(old_content, activity.content or '')

        flash('활동후기가 수정되었습니다.', 'success')
        return redirect(url_for('admin.activities_list'))

    return render_template('admin/activities/form.html', activity=activity, categories=categories)


@admin_bp.route('/activities/<int:id>/delete', methods=['POST'])
@login_required
def activities_delete(id):
    """활동후기 삭제"""
    activity = ActivityPost.query.get_or_404(id)

    import os
    from config import Config

    # 1. 첨부파일 삭제 (관계 끊고 파일 삭제)
    attachments_to_delete = list(activity.attachments)  # 복사
    activity.attachments.clear()  # 관계 먼저 끊기

    for attachment in attachments_to_delete:
        # 실제 파일 삭제
        filepath = os.path.join(Config.DIST_DIR, 'uploads', attachment.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        # File 레코드 삭제
        db.session.delete(attachment)

    # 2. 썸네일 파일 삭제
    if activity.thumbnail:
        filepath = os.path.join(Config.DIST_DIR, 'uploads', activity.thumbnail.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(activity.thumbnail)

    # 3. 본문 내 이미지 삭제
    from .utils import cleanup_all_content_images
    cleanup_all_content_images(activity.content)

    # 4. dist 폴더의 HTML 파일 삭제
    html_path = os.path.join(Config.DIST_DIR, 'activity', f'{id}.html')
    if os.path.exists(html_path):
        os.remove(html_path)

    # 5. DB에서 게시물 삭제
    db.session.delete(activity)
    db.session.commit()

    flash('활동후기가 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.activities_list'))


@admin_bp.route('/activities/<int:id>/attachments/<int:file_id>/delete', methods=['POST'])
@login_required
def activities_attachment_delete(id, file_id):
    """활동후기 첨부파일 삭제"""
    activity = ActivityPost.query.get_or_404(id)
    file_record = File.query.get_or_404(file_id)

    if file_record in activity.attachments:
        # 1. 관계 끊기
        activity.attachments.remove(file_record)

        # 2. 실제 파일 삭제
        import os
        from config import Config
        filepath = os.path.join(Config.DIST_DIR, 'uploads', file_record.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

        # 3. File 레코드 삭제
        db.session.delete(file_record)
        db.session.commit()

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.activities_edit', id=id))


# ==========================================
# 소식지 관리
# ==========================================
@admin_bp.route('/newsletters')
@login_required
def newsletters_list():
    """소식지 목록"""
    page = request.args.get('page', 1, type=int)

    query = Newsletter.query.order_by(Newsletter.published_at.desc().nullslast(), Newsletter.created_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    return render_template('admin/newsletters/list.html', pagination=pagination)


@admin_bp.route('/newsletters/new', methods=['GET', 'POST'])
@login_required
def newsletters_new():
    """소식지 등록"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        issue_number = request.form.get('issue_number', type=int)
        description = request.form.get('description', '')
        external_url = request.form.get('external_url', '')
        html_content = request.form.get('html_content', '')
        published_at_str = request.form.get('published_at', '')

        if not title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('admin/newsletters/form.html', newsletter=None)

        published_at = None
        if published_at_str:
            from datetime import datetime
            try:
                published_at = datetime.strptime(published_at_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        newsletter = Newsletter(
            title=title,
            issue_number=issue_number,
            description=description,
            external_url=external_url,
            html_content=html_content,
            content_type='html' if html_content else 'pdf',
            published_at=published_at
        )
        db.session.add(newsletter)
        db.session.commit()

        flash('소식지가 등록되었습니다.', 'success')
        return redirect(url_for('admin.newsletters_list'))

    return render_template('admin/newsletters/form.html', newsletter=None)


@admin_bp.route('/newsletters/crawl', methods=['POST'])
@login_required
def newsletters_crawl():
    """Stibee URL에서 콘텐츠 크롤링 (AJAX)"""
    url = request.json.get('url', '')

    if not url:
        return jsonify({'error': 'URL을 입력해주세요.'}), 400

    from .utils import crawl_stibee_content
    result = crawl_stibee_content(url)

    if result.get('error'):
        return jsonify({'error': result['error']}), 400

    return jsonify(result)


@admin_bp.route('/newsletters/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def newsletters_edit(id):
    """소식지 수정"""
    newsletter = Newsletter.query.get_or_404(id)

    if request.method == 'POST':
        # 이전 콘텐츠 저장 (이미지 정리용)
        old_content = newsletter.html_content or ''

        newsletter.title = request.form.get('title', '').strip()
        newsletter.issue_number = request.form.get('issue_number', type=int)
        newsletter.description = request.form.get('description', '')
        newsletter.external_url = request.form.get('external_url', '')
        newsletter.html_content = request.form.get('html_content', '')

        published_at_str = request.form.get('published_at', '')
        if published_at_str:
            from datetime import datetime
            try:
                newsletter.published_at = datetime.strptime(published_at_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if not newsletter.title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('admin/newsletters/form.html', newsletter=newsletter)

        db.session.commit()

        # 삭제된 이미지 정리
        from .utils import cleanup_orphaned_images
        cleanup_orphaned_images(old_content, newsletter.html_content or '')

        flash('소식지가 수정되었습니다.', 'success')
        return redirect(url_for('admin.newsletters_list'))

    return render_template('admin/newsletters/form.html', newsletter=newsletter)


@admin_bp.route('/newsletters/<int:id>/delete', methods=['POST'])
@login_required
def newsletters_delete(id):
    """소식지 삭제"""
    newsletter = Newsletter.query.get_or_404(id)

    # 1. 본문 내 이미지 삭제
    from .utils import cleanup_all_content_images
    cleanup_all_content_images(newsletter.html_content)

    # 2. dist 폴더의 HTML 파일 삭제
    import os
    from config import Config
    html_path = os.path.join(Config.DIST_DIR, 'newsletter', f'{id}.html')
    if os.path.exists(html_path):
        os.remove(html_path)

    # 3. DB에서 게시물 삭제
    db.session.delete(newsletter)
    db.session.commit()

    flash('소식지가 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.newsletters_list'))


# ==========================================
# 사이트 정보
# ==========================================
@admin_bp.route('/site-info', methods=['GET', 'POST'])
@login_required
def site_info():
    """사이트 정보 관리"""
    info = SiteInfo.query.first()

    if request.method == 'POST':
        if not info:
            info = SiteInfo()
            db.session.add(info)

        # 기본 정보
        info.org_name = request.form.get('org_name', '')
        info.site_name = request.form.get('site_name', '')
        info.slogan = request.form.get('slogan', '')
        info.intro_text = request.form.get('intro_text', '')

        # 연락처
        info.representative = request.form.get('representative', '')
        info.tel = request.form.get('tel', '')
        info.fax = request.form.get('fax', '')
        info.email = request.form.get('email', '')
        info.address = request.form.get('address', '')

        # 후원 계좌
        info.bank_name = request.form.get('bank_name', '')
        info.bank_account = request.form.get('bank_account', '')
        info.bank_holder = request.form.get('bank_holder', '')

        # SNS
        info.facebook = request.form.get('facebook', '')
        info.instagram = request.form.get('instagram', '')
        info.youtube = request.form.get('youtube', '')

        db.session.commit()
        flash('사이트 정보가 저장되었습니다.', 'success')

    return render_template('admin/site_info.html', info=info)


# ==========================================
# 후원신청 관리
# ==========================================
@admin_bp.route('/donations')
@login_required
def donations_list():
    """후원신청 목록"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')

    query = DonationApplication.query

    if status == 'pending':
        query = query.filter_by(is_processed=False)
    elif status == 'processed':
        query = query.filter_by(is_processed=True)

    query = query.order_by(DonationApplication.created_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    pending_count = DonationApplication.query.filter_by(is_processed=False).count()

    return render_template('admin/donations.html',
                           pagination=pagination,
                           status=status,
                           pending_count=pending_count)


@admin_bp.route('/donations/<int:id>/toggle-processed', methods=['POST'])
@login_required
def donations_toggle_processed(id):
    """후원신청 처리완료 토글"""
    donation = DonationApplication.query.get_or_404(id)
    donation.is_processed = not donation.is_processed
    db.session.commit()

    if request.headers.get('HX-Request'):
        return jsonify({'is_processed': donation.is_processed})

    return redirect(url_for('admin.donations_list'))


@admin_bp.route('/donations/<int:id>/delete', methods=['POST'])
@login_required
def donations_delete(id):
    """후원신청 삭제"""
    donation = DonationApplication.query.get_or_404(id)
    db.session.delete(donation)
    db.session.commit()

    if request.headers.get('HX-Request'):
        return '', 204

    flash('후원신청이 삭제되었습니다.', 'success')
    return redirect(url_for('admin.donations_list'))


@admin_bp.route('/donations/<int:id>/pdf')
@login_required
def donation_pdf(id):
    """후원신청서 인쇄/PDF 저장 (브라우저 인쇄 기능 사용)"""
    donation = DonationApplication.query.get_or_404(id)
    site = SiteInfo.query.first()

    # 브라우저 인쇄 모드로 렌더링
    return render_template('admin/donation_pdf.html', donation=donation, site=site, print_mode=True)


# ==========================================
# 관리자 계정 관리 (슈퍼관리자만)
# ==========================================
@admin_bp.route('/users')
@super_admin_required
def users_list():
    """관리자 계정 목록"""
    users = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return render_template('admin/users/list.html', users=users)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@super_admin_required
def users_new():
    """관리자 계정 추가"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'admin')

        if not username or not password:
            flash('아이디와 비밀번호를 입력해주세요.', 'error')
            return render_template('admin/users/form.html', user=None)

        if AdminUser.query.filter_by(username=username).first():
            flash('이미 존재하는 아이디입니다.', 'error')
            return render_template('admin/users/form.html', user=None)

        user = AdminUser(
            username=username,
            name=name,
            role=role
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('관리자 계정이 추가되었습니다.', 'success')
        return redirect(url_for('admin.users_list'))

    return render_template('admin/users/form.html', user=None)


@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@super_admin_required
def users_edit(id):
    """관리자 계정 수정"""
    user = AdminUser.query.get_or_404(id)

    if request.method == 'POST':
        user.name = request.form.get('name', '').strip()
        user.role = request.form.get('role', 'admin')
        user.is_active = request.form.get('is_active') == 'on'

        # 비밀번호 변경 (입력된 경우에만)
        new_password = request.form.get('password', '')
        if new_password:
            user.set_password(new_password)

        db.session.commit()

        flash('관리자 계정이 수정되었습니다.', 'success')
        return redirect(url_for('admin.users_list'))

    return render_template('admin/users/form.html', user=user)


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@super_admin_required
def users_delete(id):
    """관리자 계정 삭제"""
    user = AdminUser.query.get_or_404(id)

    # 자기 자신은 삭제 불가
    if user.id == session.get('admin_id'):
        flash('자기 자신은 삭제할 수 없습니다.', 'error')
        return redirect(url_for('admin.users_list'))

    db.session.delete(user)
    db.session.commit()

    flash('관리자 계정이 삭제되었습니다.', 'success')
    return redirect(url_for('admin.users_list'))


# ==========================================
# 에디터 이미지 업로드 API
# ==========================================
@admin_bp.route('/upload/image', methods=['POST'])
@login_required
def upload_image():
    """에디터에서 이미지 업로드 (붙여넣기, 드래그앤드롭)"""
    from .utils import save_uploaded_file, save_base64_image, ALLOWED_IMAGE_EXTENSIONS
    import base64
    import json

    # 파일 업로드 방식
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            file_record = save_uploaded_file(file, ALLOWED_IMAGE_EXTENSIONS)
            if file_record:
                db.session.commit()
                return jsonify({
                    'success': True,
                    'url': file_record.url,
                    'filename': file_record.original_filename
                })
            return jsonify({'success': False, 'error': '이미지 저장 실패'}), 400

    # Base64 방식 (붙여넣기)
    data = request.get_json()
    if data and 'image' in data:
        base64_data = data['image']
        file_record = save_base64_image(base64_data)
        if file_record:
            db.session.commit()
            return jsonify({
                'success': True,
                'url': file_record.url,
                'filename': file_record.original_filename
            })
        return jsonify({'success': False, 'error': 'Base64 이미지 저장 실패'}), 400

    return jsonify({'success': False, 'error': '이미지가 없습니다'}), 400


# ==========================================
# 사업분야 관리
# ==========================================
@admin_bp.route('/business-areas')
@login_required
def business_areas_list():
    """사업분야 목록"""
    areas = BusinessArea.query.order_by(BusinessArea.display_order, BusinessArea.id).all()
    return render_template('admin/business_areas/list.html', areas=areas)


@admin_bp.route('/business-areas/new', methods=['GET', 'POST'])
@login_required
def business_areas_new():
    """사업분야 추가"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '')
        details_text = request.form.get('details', '')
        photo_url = normalize_upload_urls(request.form.get('photo_url', ''))

        if not name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/business_areas/form.html', area=None)

        # 상세내용 파싱 (줄바꿈으로 구분)
        details = [line.strip() for line in details_text.split('\n') if line.strip()]

        area = BusinessArea(
            name=name,
            description=description,
            details=details,
            photo_url=photo_url if photo_url else None,
            display_order=BusinessArea.query.count()
        )

        # 이미지 파일 업로드 처리
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                from .utils import save_uploaded_file
                file_record = save_uploaded_file(file)
                if file_record:
                    area.photo_file_id = file_record.id
                    area.photo_url = None

        db.session.add(area)
        db.session.commit()

        flash('사업분야가 추가되었습니다.', 'success')
        return redirect(url_for('admin.business_areas_list'))

    return render_template('admin/business_areas/form.html', area=None)


@admin_bp.route('/business-areas/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def business_areas_edit(id):
    """사업분야 수정"""
    area = BusinessArea.query.get_or_404(id)

    if request.method == 'POST':
        area.name = request.form.get('name', '').strip()
        area.description = request.form.get('description', '')
        details_text = request.form.get('details', '')
        photo_url = normalize_upload_urls(request.form.get('photo_url', ''))

        if not area.name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/business_areas/form.html', area=area)

        area.details = [line.strip() for line in details_text.split('\n') if line.strip()]

        if photo_url:
            area.photo_url = photo_url

        # 이미지 파일 업로드 처리
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                from .utils import save_uploaded_file
                file_record = save_uploaded_file(file)
                if file_record:
                    area.photo_file_id = file_record.id
                    area.photo_url = None

        db.session.commit()

        flash('사업분야가 수정되었습니다.', 'success')
        return redirect(url_for('admin.business_areas_list'))

    return render_template('admin/business_areas/form.html', area=area)


@admin_bp.route('/business-areas/<int:id>/delete', methods=['POST'])
@login_required
def business_areas_delete(id):
    """사업분야 삭제"""
    area = BusinessArea.query.get_or_404(id)
    db.session.delete(area)
    db.session.commit()

    flash('사업분야가 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.business_areas_list'))


@admin_bp.route('/business-areas/reorder', methods=['POST'])
@login_required
def business_areas_reorder():
    """사업분야 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, area_id in enumerate(order):
        area = BusinessArea.query.get(area_id)
        if area:
            area.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# 히어로 사진 관리
# ==========================================
@admin_bp.route('/hero-photos')
@login_required
def hero_photos_list():
    """히어로 사진 목록"""
    photos = ActivityPhoto.query.order_by(ActivityPhoto.display_order, ActivityPhoto.id).all()
    return render_template('admin/hero_photos/list.html', photos=photos)


@admin_bp.route('/hero-photos/new', methods=['GET', 'POST'])
@login_required
def hero_photos_new():
    """히어로 사진 추가"""
    if request.method == 'POST':
        description = request.form.get('description', '')
        image_url = request.form.get('image_url', '')
        taken_at_str = request.form.get('taken_at', '')

        taken_at = None
        if taken_at_str:
            try:
                taken_at = datetime.strptime(taken_at_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        photo = ActivityPhoto(
            description=description,
            image_url=image_url if image_url else None,
            taken_at=taken_at,
            display_order=ActivityPhoto.query.count()
        )

        # 이미지 파일 업로드 처리
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                from .utils import save_uploaded_file
                file_record = save_uploaded_file(file)
                if file_record:
                    photo.file_id = file_record.id
                    photo.image_url = None

        db.session.add(photo)
        db.session.commit()

        flash('사진이 추가되었습니다.', 'success')
        return redirect(url_for('admin.hero_photos_list'))

    return render_template('admin/hero_photos/form.html', photo=None)


@admin_bp.route('/hero-photos/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def hero_photos_edit(id):
    """히어로 사진 수정"""
    photo = ActivityPhoto.query.get_or_404(id)

    if request.method == 'POST':
        photo.description = request.form.get('description', '')
        image_url = request.form.get('image_url', '')
        taken_at_str = request.form.get('taken_at', '')

        if image_url:
            photo.image_url = image_url

        if taken_at_str:
            try:
                photo.taken_at = datetime.strptime(taken_at_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # 이미지 파일 업로드 처리
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                from .utils import save_uploaded_file
                file_record = save_uploaded_file(file)
                if file_record:
                    photo.file_id = file_record.id
                    photo.image_url = None

        db.session.commit()

        flash('사진이 수정되었습니다.', 'success')
        return redirect(url_for('admin.hero_photos_list'))

    return render_template('admin/hero_photos/form.html', photo=photo)


@admin_bp.route('/hero-photos/<int:id>/delete', methods=['POST'])
@login_required
def hero_photos_delete(id):
    """히어로 사진 삭제"""
    photo = ActivityPhoto.query.get_or_404(id)
    db.session.delete(photo)
    db.session.commit()

    flash('사진이 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.hero_photos_list'))


@admin_bp.route('/hero-photos/<int:id>/toggle-active', methods=['POST'])
@login_required
def hero_photos_toggle_active(id):
    """히어로 사진 활성화 토글"""
    photo = ActivityPhoto.query.get_or_404(id)
    photo.is_active = not photo.is_active
    db.session.commit()

    if request.headers.get('HX-Request'):
        return jsonify({'is_active': photo.is_active})

    return redirect(url_for('admin.hero_photos_list'))


@admin_bp.route('/hero-photos/reorder', methods=['POST'])
@login_required
def hero_photos_reorder():
    """히어로 사진 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, photo_id in enumerate(order):
        photo = ActivityPhoto.query.get(photo_id)
        if photo:
            photo.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# 연혁 관리
# ==========================================
@admin_bp.route('/history')
@login_required
def history_list():
    """연혁 목록"""
    sections = HistorySection.query.order_by(HistorySection.display_order, HistorySection.id).all()
    return render_template('admin/history/list.html', sections=sections)


@admin_bp.route('/history/sections/new', methods=['GET', 'POST'])
@login_required
def history_section_new():
    """연혁 섹션 추가"""
    if request.method == 'POST':
        subtitle = request.form.get('subtitle', '').strip()
        summary = request.form.get('summary', '')
        summary_title = request.form.get('summary_title', '')

        if not subtitle:
            flash('소제목을 입력해주세요.', 'error')
            return render_template('admin/history/section_form.html', section=None)

        section = HistorySection(
            subtitle=subtitle,
            summary=summary,
            summary_title=summary_title,
            display_order=HistorySection.query.count()
        )

        db.session.add(section)
        db.session.commit()

        flash('섹션이 추가되었습니다.', 'success')
        return redirect(url_for('admin.history_list'))

    return render_template('admin/history/section_form.html', section=None)


@admin_bp.route('/history/sections/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def history_section_edit(id):
    """연혁 섹션 수정"""
    section = HistorySection.query.get_or_404(id)

    if request.method == 'POST':
        section.subtitle = request.form.get('subtitle', '').strip()
        section.summary = request.form.get('summary', '')
        section.summary_title = request.form.get('summary_title', '')

        if not section.subtitle:
            flash('소제목을 입력해주세요.', 'error')
            return render_template('admin/history/section_form.html', section=section)

        db.session.commit()

        flash('섹션이 수정되었습니다.', 'success')
        return redirect(url_for('admin.history_list'))

    return render_template('admin/history/section_form.html', section=section)


@admin_bp.route('/history/sections/<int:id>/delete', methods=['POST'])
@login_required
def history_section_delete(id):
    """연혁 섹션 삭제"""
    section = HistorySection.query.get_or_404(id)

    # 섹션 내 모든 항목도 삭제
    HistoryItem.query.filter_by(section_id=id).delete()

    db.session.delete(section)
    db.session.commit()

    flash('섹션이 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.history_list'))


@admin_bp.route('/history/sections/<int:section_id>/items/new', methods=['GET', 'POST'])
@login_required
def history_item_new(section_id):
    """연혁 항목 추가"""
    section = HistorySection.query.get_or_404(section_id)

    if request.method == 'POST':
        year = request.form.get('year', type=int)
        content = request.form.get('content', '').strip()

        if not content:
            flash('내용을 입력해주세요.', 'error')
            return render_template('admin/history/item_form.html', section=section, item=None)

        item = HistoryItem(
            section_id=section_id,
            year=year,
            content=content,
            display_order=HistoryItem.query.filter_by(section_id=section_id).count()
        )

        db.session.add(item)
        db.session.commit()

        flash('항목이 추가되었습니다.', 'success')
        return redirect(url_for('admin.history_list'))

    return render_template('admin/history/item_form.html', section=section, item=None)


@admin_bp.route('/history/items/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def history_item_edit(id):
    """연혁 항목 수정"""
    item = HistoryItem.query.get_or_404(id)
    section = item.section

    if request.method == 'POST':
        item.year = request.form.get('year', type=int)
        item.content = request.form.get('content', '').strip()

        if not item.content:
            flash('내용을 입력해주세요.', 'error')
            return render_template('admin/history/item_form.html', section=section, item=item)

        db.session.commit()

        flash('항목이 수정되었습니다.', 'success')
        return redirect(url_for('admin.history_list'))

    return render_template('admin/history/item_form.html', section=section, item=item)


@admin_bp.route('/history/items/<int:id>/delete', methods=['POST'])
@login_required
def history_item_delete(id):
    """연혁 항목 삭제"""
    item = HistoryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()

    flash('항목이 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.history_list'))


@admin_bp.route('/history/items/reorder', methods=['POST'])
@login_required
def history_items_reorder():
    """연혁 항목 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for i, item_id in enumerate(order):
        item = HistoryItem.query.get(int(item_id))
        if item:
            item.display_order = i

    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# 카테고리 관리
# ==========================================
@admin_bp.route('/categories')
@login_required
def categories_list():
    """카테고리 목록"""
    categories = ActivityCategory.query.order_by(ActivityCategory.display_order, ActivityCategory.id).all()

    # 각 카테고리별 게시물 수 계산
    post_counts = {}
    for cat in categories:
        post_counts[cat.id] = ActivityPost.query.filter_by(category=cat.name).count()

    return render_template('admin/categories/list.html', categories=categories, post_counts=post_counts)


@admin_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def categories_new():
    """카테고리 추가"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        color = request.form.get('color', '#6d28d9')

        if not name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/categories/form.html', category=None)

        if ActivityCategory.query.filter_by(name=name).first():
            flash('이미 존재하는 카테고리입니다.', 'error')
            return render_template('admin/categories/form.html', category=None)

        category = ActivityCategory(
            name=name,
            color=color,
            display_order=ActivityCategory.query.count()
        )

        db.session.add(category)
        db.session.commit()

        flash('카테고리가 추가되었습니다.', 'success')
        return redirect(url_for('admin.categories_list'))

    return render_template('admin/categories/form.html', category=None)


@admin_bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def categories_edit(id):
    """카테고리 수정"""
    category = ActivityCategory.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category.color = request.form.get('color', '#6d28d9')
        category.is_active = request.form.get('is_active') == 'on'

        if not name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/categories/form.html', category=category)

        # 이름 중복 체크 (자기 자신 제외)
        existing = ActivityCategory.query.filter(
            ActivityCategory.name == name,
            ActivityCategory.id != id
        ).first()
        if existing:
            flash('이미 존재하는 카테고리입니다.', 'error')
            return render_template('admin/categories/form.html', category=category)

        # 기존 이름 저장
        old_name = category.name
        category.name = name

        # 관련 게시물 카테고리명도 업데이트
        if old_name != name:
            ActivityPost.query.filter_by(category=old_name).update({'category': name})

        db.session.commit()

        flash('카테고리가 수정되었습니다.', 'success')
        return redirect(url_for('admin.categories_list'))

    return render_template('admin/categories/form.html', category=category)


@admin_bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def categories_delete(id):
    """카테고리 삭제"""
    category = ActivityCategory.query.get_or_404(id)

    # 해당 카테고리를 가진 게시물들의 카테고리를 null로 설정
    affected = ActivityPost.query.filter_by(category=category.name).update({'category': None})

    db.session.delete(category)
    db.session.commit()

    if affected > 0:
        flash(f'카테고리가 삭제되었습니다. {affected}개의 게시물이 미분류로 변경되었습니다.', 'success')
    else:
        flash('카테고리가 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.categories_list'))


@admin_bp.route('/categories/merge', methods=['POST'])
@login_required
def categories_merge():
    """카테고리 병합 - source 카테고리의 게시물을 target 카테고리로 이동 후 source 삭제"""
    data = request.get_json()
    source_id = data.get('source_id')
    target_id = data.get('target_id')

    if not source_id or not target_id:
        return jsonify({'success': False, 'error': '카테고리를 선택해주세요.'}), 400

    if source_id == target_id:
        return jsonify({'success': False, 'error': '같은 카테고리끼리는 병합할 수 없습니다.'}), 400

    source = ActivityCategory.query.get_or_404(source_id)
    target = ActivityCategory.query.get_or_404(target_id)

    # source 카테고리의 게시물들을 target 카테고리로 이동
    affected = ActivityPost.query.filter_by(category=source.name).update({'category': target.name})

    # source 카테고리 삭제
    db.session.delete(source)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'"{source.name}" 카테고리가 "{target.name}"(으)로 병합되었습니다. ({affected}개 게시물 이동)'
    })


@admin_bp.route('/categories/reorder', methods=['POST'])
@login_required
def categories_reorder():
    """카테고리 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, cat_id in enumerate(order):
        category = ActivityCategory.query.get(cat_id)
        if category:
            category.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# 자원활동 분야 관리
# ==========================================
@admin_bp.route('/volunteer-areas')
@login_required
def volunteer_areas_list():
    """자원활동 분야 목록"""
    areas = VolunteerArea.query.order_by(VolunteerArea.display_order, VolunteerArea.id).all()
    return render_template('admin/volunteer_areas/list.html', areas=areas)


@admin_bp.route('/volunteer-areas/new', methods=['GET', 'POST'])
@login_required
def volunteer_areas_new():
    """자원활동 분야 추가"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '')
        icon = request.form.get('icon', '')
        color = request.form.get('color', '#6d28d9')

        if not name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/volunteer_areas/form.html', area=None)

        area = VolunteerArea(
            name=name,
            description=description,
            icon=icon,
            color=color,
            display_order=VolunteerArea.query.count()
        )

        db.session.add(area)
        db.session.commit()

        flash('자원활동 분야가 추가되었습니다.', 'success')
        return redirect(url_for('admin.volunteer_areas_list'))

    return render_template('admin/volunteer_areas/form.html', area=None)


@admin_bp.route('/volunteer-areas/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def volunteer_areas_edit(id):
    """자원활동 분야 수정"""
    area = VolunteerArea.query.get_or_404(id)

    if request.method == 'POST':
        area.name = request.form.get('name', '').strip()
        area.description = request.form.get('description', '')
        area.icon = request.form.get('icon', '')
        area.color = request.form.get('color', '#6d28d9')
        area.is_active = request.form.get('is_active') == 'on'

        if not area.name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/volunteer_areas/form.html', area=area)

        db.session.commit()

        flash('자원활동 분야가 수정되었습니다.', 'success')
        return redirect(url_for('admin.volunteer_areas_list'))

    return render_template('admin/volunteer_areas/form.html', area=area)


@admin_bp.route('/volunteer-areas/<int:id>/delete', methods=['POST'])
@login_required
def volunteer_areas_delete(id):
    """자원활동 분야 삭제"""
    area = VolunteerArea.query.get_or_404(id)
    db.session.delete(area)
    db.session.commit()

    flash('자원활동 분야가 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.volunteer_areas_list'))


@admin_bp.route('/volunteer-areas/reorder', methods=['POST'])
@login_required
def volunteer_areas_reorder():
    """자원활동 분야 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, area_id in enumerate(order):
        area = VolunteerArea.query.get(area_id)
        if area:
            area.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# 후원분야 관리
# ==========================================
@admin_bp.route('/donation-areas')
@login_required
def donation_areas_list():
    """후원분야 목록"""
    areas = DonationArea.query.order_by(DonationArea.display_order, DonationArea.id).all()
    return render_template('admin/donation_areas/list.html', areas=areas)


@admin_bp.route('/donation-areas/new', methods=['GET', 'POST'])
@login_required
def donation_areas_new():
    """후원분야 추가"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '')
        icon = request.form.get('icon', '')
        color = request.form.get('color', '#6d28d9')

        if not name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/donation_areas/form.html', area=None)

        area = DonationArea(
            name=name,
            description=description,
            icon=icon,
            color=color,
            display_order=DonationArea.query.count()
        )

        db.session.add(area)
        db.session.commit()

        flash('후원분야가 추가되었습니다.', 'success')
        return redirect(url_for('admin.donation_areas_list'))

    return render_template('admin/donation_areas/form.html', area=None)


@admin_bp.route('/donation-areas/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def donation_areas_edit(id):
    """후원분야 수정"""
    area = DonationArea.query.get_or_404(id)

    if request.method == 'POST':
        area.name = request.form.get('name', '').strip()
        area.description = request.form.get('description', '')
        area.icon = request.form.get('icon', '')
        area.color = request.form.get('color', '#6d28d9')
        area.is_active = request.form.get('is_active') == 'on'

        if not area.name:
            flash('이름을 입력해주세요.', 'error')
            return render_template('admin/donation_areas/form.html', area=area)

        db.session.commit()

        flash('후원분야가 수정되었습니다.', 'success')
        return redirect(url_for('admin.donation_areas_list'))

    return render_template('admin/donation_areas/form.html', area=area)


@admin_bp.route('/donation-areas/<int:id>/delete', methods=['POST'])
@login_required
def donation_areas_delete(id):
    """후원분야 삭제"""
    area = DonationArea.query.get_or_404(id)
    db.session.delete(area)
    db.session.commit()

    flash('후원분야가 삭제되었습니다.', 'success')

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.donation_areas_list'))


@admin_bp.route('/donation-areas/reorder', methods=['POST'])
@login_required
def donation_areas_reorder():
    """후원분야 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, area_id in enumerate(order):
        area = DonationArea.query.get(area_id)
        if area:
            area.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# 후원금 사용용도 관리
# ==========================================
@admin_bp.route('/donation-usages')
@login_required
def donation_usages_list():
    """후원금 사용용도 목록"""
    usages = DonationUsage.query.order_by(DonationUsage.display_order, DonationUsage.id).all()
    return render_template('admin/donation_usages/list.html', usages=usages)


@admin_bp.route('/donation-usages/add', methods=['POST'])
@login_required
def donation_usages_add():
    """후원금 사용용도 추가"""
    name = request.form.get('name', '').strip()

    if name:
        usage = DonationUsage(
            name=name,
            display_order=DonationUsage.query.count()
        )
        db.session.add(usage)
        db.session.commit()
        flash('사용용도가 추가되었습니다.', 'success')

    return redirect(url_for('admin.donation_usages_list'))


@admin_bp.route('/donation-usages/<int:id>/edit', methods=['POST'])
@login_required
def donation_usages_edit(id):
    """후원금 사용용도 수정"""
    usage = DonationUsage.query.get_or_404(id)
    usage.name = request.form.get('name', '').strip()

    if not usage.name:
        flash('내용을 입력해주세요.', 'error')
    else:
        db.session.commit()
        flash('사용용도가 수정되었습니다.', 'success')

    return redirect(url_for('admin.donation_usages_list'))


@admin_bp.route('/donation-usages/<int:id>/delete', methods=['POST'])
@login_required
def donation_usages_delete(id):
    """후원금 사용용도 삭제"""
    usage = DonationUsage.query.get_or_404(id)
    db.session.delete(usage)
    db.session.commit()

    if request.headers.get('HX-Request'):
        return '', 200

    return redirect(url_for('admin.donation_usages_list'))


@admin_bp.route('/donation-usages/reorder', methods=['POST'])
@login_required
def donation_usages_reorder():
    """후원금 사용용도 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, usage_id in enumerate(order):
        usage = DonationUsage.query.get(usage_id)
        if usage:
            usage.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


# ==========================================
# 대중교통 관리
# ==========================================
@admin_bp.route('/transportation')
@login_required
def transportation():
    """대중교통 정보 관리"""
    bus_stops = BusStop.query.order_by(BusStop.display_order, BusStop.id).all()
    bus_routes = BusRoute.query.order_by(BusRoute.route_type, BusRoute.display_order, BusRoute.id).all()

    # 버스 타입별로 그룹화
    routes_by_type = {'일반': [], '좌석': [], '마을': []}
    for route in bus_routes:
        if route.route_type in routes_by_type:
            routes_by_type[route.route_type].append(route)

    return render_template('admin/transportation/index.html',
                           bus_stops=bus_stops,
                           routes_by_type=routes_by_type)


@admin_bp.route('/transportation/stops/add', methods=['POST'])
@login_required
def transportation_add_stop():
    """정류장 추가"""
    name = request.form.get('name', '').strip()
    if name:
        stop = BusStop(name=name, display_order=BusStop.query.count())
        db.session.add(stop)
        db.session.commit()
        flash('정류장이 추가되었습니다.', 'success')
    return redirect(url_for('admin.transportation'))


@admin_bp.route('/transportation/stops/<int:id>/delete', methods=['POST'])
@login_required
def transportation_delete_stop(id):
    """정류장 삭제"""
    stop = BusStop.query.get_or_404(id)
    db.session.delete(stop)
    db.session.commit()

    if request.headers.get('HX-Request'):
        return '', 200

    flash('정류장이 삭제되었습니다.', 'success')
    return redirect(url_for('admin.transportation'))


@admin_bp.route('/transportation/stops/reorder', methods=['POST'])
@login_required
def transportation_reorder_stops():
    """정류장 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, stop_id in enumerate(order):
        stop = BusStop.query.get(stop_id)
        if stop:
            stop.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/transportation/routes/add', methods=['POST'])
@login_required
def transportation_add_route():
    """버스 노선 추가"""
    route_type = request.form.get('route_type', '일반')
    name = request.form.get('name', '').strip()

    if name and route_type in BusRoute.TYPES:
        route = BusRoute(
            route_type=route_type,
            name=name,
            display_order=BusRoute.query.filter_by(route_type=route_type).count()
        )
        db.session.add(route)
        db.session.commit()
        flash('버스 노선이 추가되었습니다.', 'success')

    return redirect(url_for('admin.transportation'))


@admin_bp.route('/transportation/routes/<int:id>/delete', methods=['POST'])
@login_required
def transportation_delete_route(id):
    """버스 노선 삭제"""
    route = BusRoute.query.get_or_404(id)
    db.session.delete(route)
    db.session.commit()

    if request.headers.get('HX-Request'):
        return '', 200

    flash('버스 노선이 삭제되었습니다.', 'success')
    return redirect(url_for('admin.transportation'))


# ==========================================
# 운영시간 관리
# ==========================================
@admin_bp.route('/operating-hours')
@login_required
def operating_hours():
    """운영시간 관리"""
    programs = OperatingHours.query.filter_by(is_active=True).order_by(OperatingHours.display_order).all()
    office = OfficeInfo.get()
    return render_template('admin/operating_hours/index.html', programs=programs, office=office)


@admin_bp.route('/operating-hours/add', methods=['POST'])
@login_required
def operating_hours_add():
    """운영시간 항목 추가"""
    name = request.form.get('name', '').strip()
    schedule = request.form.get('schedule', '').strip()

    if name:
        program = OperatingHours(
            name=name,
            schedule=schedule,
            display_order=OperatingHours.query.count()
        )
        db.session.add(program)
        db.session.commit()
        flash('운영시간이 추가되었습니다.', 'success')

    return redirect(url_for('admin.operating_hours'))


@admin_bp.route('/operating-hours/<int:id>/edit', methods=['POST'])
@login_required
def operating_hours_edit(id):
    """운영시간 항목 수정"""
    program = OperatingHours.query.get_or_404(id)
    program.name = request.form.get('name', '').strip()
    program.schedule = request.form.get('schedule', '').strip()
    db.session.commit()

    flash('운영시간이 수정되었습니다.', 'success')
    return redirect(url_for('admin.operating_hours'))


@admin_bp.route('/operating-hours/<int:id>/delete', methods=['POST'])
@login_required
def operating_hours_delete(id):
    """운영시간 항목 삭제"""
    program = OperatingHours.query.get_or_404(id)
    db.session.delete(program)
    db.session.commit()

    if request.headers.get('HX-Request'):
        return '', 200

    flash('운영시간이 삭제되었습니다.', 'success')
    return redirect(url_for('admin.operating_hours'))


@admin_bp.route('/operating-hours/reorder', methods=['POST'])
@login_required
def operating_hours_reorder():
    """운영시간 순서 변경"""
    data = request.get_json()
    order = data.get('order', [])

    for idx, item_id in enumerate(order):
        program = OperatingHours.query.get(item_id)
        if program:
            program.display_order = idx

    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/operating-hours/office', methods=['POST'])
@login_required
def operating_hours_office():
    """사무실 정보 수정"""
    office = OfficeInfo.get()
    office.office_hours = request.form.get('office_hours', '').strip()
    office.closed_days = request.form.get('closed_days', '').strip()
    db.session.commit()

    flash('사무실 정보가 수정되었습니다.', 'success')
    return redirect(url_for('admin.operating_hours'))


# ==========================================
# SSG 빌드 관리
# ==========================================
@admin_bp.route('/build/status')
@login_required
def build_status():
    """현재 빌드 상태 조회 (AJAX)"""
    status = BuildStatus.get_current()
    return jsonify(status.to_dict())


@admin_bp.route('/build/trigger', methods=['POST'])
@login_required
def build_trigger():
    """수동 빌드 트리거"""
    from background_builder import trigger_build

    success = trigger_build(triggered_by='manual')

    if success:
        return jsonify({
            'success': True,
            'message': '빌드가 시작되었습니다. 잠시 후 새로고침하시면 결과를 확인할 수 있습니다.'
        })
    else:
        return jsonify({
            'success': False,
            'message': '빌드 시작에 실패했습니다. 이미 빌드가 진행 중일 수 있습니다.'
        }), 400


@admin_bp.route('/build/history')
@login_required
def build_history():
    """빌드 히스토리 페이지"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 최근 빌드 내역 조회
    pagination = BuildStatus.query.order_by(BuildStatus.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('admin/build_history.html',
                         builds=pagination.items,
                         pagination=pagination)
