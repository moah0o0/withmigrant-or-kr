"""
양산외국인노동자의집 데이터 모델
"""
from datetime import datetime
import re

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ============================================================================
# Mixins - 공통 필드/메서드
# ============================================================================

class TimestampMixin:
    """생성/수정 시간 자동 관리"""
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DisplayOrderMixin:
    """정렬 순서 + 활성화 상태"""
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


# ============================================================================
# 0. 관리자 계정
# ============================================================================

class AdminUser(db.Model):
    """관리자 계정"""
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='admin')  # super_admin / admin
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AdminUser {self.username}>'

    def set_password(self, password):
        """비밀번호 해싱 저장"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """비밀번호 확인"""
        return check_password_hash(self.password_hash, password)

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================================
# 1. 파일 관리
# ============================================================================

class File(db.Model):
    """업로드 파일 관리"""
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)      # 저장된 파일명 (UUID 등)
    original_filename = db.Column(db.String(255), nullable=False)  # 원본 파일명
    mimetype = db.Column(db.String(100))
    size = db.Column(db.Integer)  # bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<File {self.original_filename}>'

    @property
    def url(self):
        """파일 URL (dist/uploads 경로)"""
        return f'/uploads/{self.filename}'

    @property
    def is_image(self):
        """이미지 파일 여부"""
        return self.mimetype and self.mimetype.startswith('image/')

    def is_used(self):
        """파일이 게시물이나 다른 곳에서 사용 중인지 확인"""
        # notice_attachments 연결 테이블 확인
        notice_attachment = db.session.execute(
            db.text("SELECT 1 FROM notice_attachments WHERE file_id = :file_id LIMIT 1"),
            {'file_id': self.id}
        ).first()
        if notice_attachment:
            return True

        # activity_attachments 연결 테이블 확인
        activity_attachment = db.session.execute(
            db.text("SELECT 1 FROM activity_attachments WHERE file_id = :file_id LIMIT 1"),
            {'file_id': self.id}
        ).first()
        if activity_attachment:
            return True

        # ActivityPhoto에서 사용 확인
        activity_photo = db.session.execute(
            db.text("SELECT 1 FROM activity_photos WHERE file_id = :file_id LIMIT 1"),
            {'file_id': self.id}
        ).first()
        if activity_photo:
            return True

        # ActivityPost 썸네일 확인
        activity_post = db.session.execute(
            db.text("SELECT 1 FROM activity_posts WHERE thumbnail_file_id = :file_id LIMIT 1"),
            {'file_id': self.id}
        ).first()
        if activity_post:
            return True

        # BusinessArea 사진 확인
        business_area = db.session.execute(
            db.text("SELECT 1 FROM business_areas WHERE photo_file_id = :file_id LIMIT 1"),
            {'file_id': self.id}
        ).first()
        if business_area:
            return True

        # Newsletter PDF 확인
        newsletter = db.session.execute(
            db.text("SELECT 1 FROM newsletters WHERE pdf_file_id = :file_id LIMIT 1"),
            {'file_id': self.id}
        ).first()
        if newsletter:
            return True

        return False

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'mimetype': self.mimetype,
            'size': self.size,
            'url': self.url
        }


# ============================================================================
# 2. 사이트 기본 정보
# ============================================================================

class SiteInfo(db.Model):
    """사이트 기본 정보 (단일 레코드)"""
    __tablename__ = 'site_info'

    id = db.Column(db.Integer, primary_key=True)

    # 단체 정보
    org_name = db.Column(db.String(100))      # 사단법인 함께하는세상
    site_name = db.Column(db.String(100))     # 양산외국인노동자의집
    slogan = db.Column(db.String(255))        # 슬로건
    intro_text = db.Column(db.Text)           # 소개 문구

    # 연락처
    address = db.Column(db.Text)
    tel = db.Column(db.String(50))
    fax = db.Column(db.String(50))
    email = db.Column(db.String(255))

    # SNS
    facebook = db.Column(db.String(500))
    instagram = db.Column(db.String(500))
    youtube = db.Column(db.String(500))

    # 법인 정보
    representative = db.Column(db.String(100))      # 대표자명
    registration_number = db.Column(db.String(100)) # 사업자등록번호

    # 후원 계좌
    bank_name = db.Column(db.String(50))
    bank_account = db.Column(db.String(100))
    bank_holder = db.Column(db.String(100))

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SiteInfo {self.site_name}>'

    def to_dict(self):
        """템플릿에서 site.xxx 형태로 접근"""
        return {
            'org_name': self.org_name,
            'site_name': self.site_name,
            'slogan': self.slogan,
            'intro_text': self.intro_text,
            'address': self.address,
            'tel': self.tel,
            'fax': self.fax,
            'email': self.email,
            'facebook': self.facebook,
            'instagram': self.instagram,
            'youtube': self.youtube,
            'representative': self.representative,
            'registration_number': self.registration_number,
            'bank_name': self.bank_name,
            'bank_account': self.bank_account,
            'bank_holder': self.bank_holder,
        }


# ============================================================================
# 3. 콘텐츠 - 고정적 자료 (소개 페이지용)
# ============================================================================

class ActivityPhoto(db.Model, DisplayOrderMixin):
    """메인/소개 페이지 활동사진"""
    __tablename__ = 'activity_photos'

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'))
    image_url = db.Column(db.String(500))  # 외부 URL 직접 저장
    description = db.Column(db.Text)
    taken_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    file = db.relationship('File', backref='activity_photos')

    def __repr__(self):
        return f'<ActivityPhoto {self.id}>'

    @property
    def url(self):
        """이미지 URL (파일 또는 외부 URL)"""
        if self.image_url:
            # 레거시 /static/uploads/ 경로 제거
            url = self.image_url
            if url.startswith('/static/uploads/'):
                url = url.replace('/static/uploads/', '/uploads/')
            return url
        if self.file:
            return self.file.url
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'description': self.description,
            'taken_at': self.taken_at.isoformat() if self.taken_at else None,
            'display_order': self.display_order,
            'is_active': self.is_active
        }


class BusinessArea(db.Model, DisplayOrderMixin):
    """주요 사업분야"""
    __tablename__ = 'business_areas'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))  # 한 줄 소개
    details = db.Column(db.JSON)             # ["상세내용1", "상세내용2", ...]
    photo_file_id = db.Column(db.Integer, db.ForeignKey('files.id'))
    photo_url = db.Column(db.String(500))    # 외부 URL 직접 저장

    photo = db.relationship('File', backref='business_areas')

    def __repr__(self):
        return f'<BusinessArea {self.name}>'

    @property
    def image_url(self):
        """사진 URL"""
        if self.photo_url:
            # 레거시 /static/uploads/ 경로 제거
            url = self.photo_url
            if url.startswith('/static/uploads/'):
                url = url.replace('/static/uploads/', '/uploads/')
            return url
        if self.photo:
            return self.photo.url
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'details': self.details or [],
            'image_url': self.image_url,
            'display_order': self.display_order,
            'is_active': self.is_active
        }


class VolunteerArea(db.Model, DisplayOrderMixin):
    """자원활동 분야"""
    __tablename__ = 'volunteer_areas'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))               # 아이콘 이름
    color = db.Column(db.String(20), default='#6d28d9')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<VolunteerArea {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'display_order': self.display_order,
            'is_active': self.is_active
        }


class DonationArea(db.Model, DisplayOrderMixin):
    """후원 분야"""
    __tablename__ = 'donation_areas'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    color = db.Column(db.String(20), default='#6d28d9')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DonationArea {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'display_order': self.display_order,
            'is_active': self.is_active
        }


class DonationUsage(db.Model, DisplayOrderMixin):
    """후원금 사용용도"""
    __tablename__ = 'donation_usages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DonationUsage {self.name}>'


class SponsorshipInfo(db.Model):
    """후원안내 페이지 콘텐츠 (단일 레코드)"""
    __tablename__ = 'sponsorship_info'

    id = db.Column(db.Integer, primary_key=True)
    appeal_text = db.Column(db.Text)         # 후원 호소문
    volunteer_summary = db.Column(db.Text)   # 자원활동 요약
    donation_summary = db.Column(db.Text)    # 후원활동 요약
    donation_details = db.Column(db.JSON)    # 후원 분야별 상세 안내
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return '<SponsorshipInfo>'


class HistorySection(db.Model):
    """걸어온 길 - 시대별 섹션"""
    __tablename__ = 'history_sections'

    id = db.Column(db.Integer, primary_key=True)
    subtitle = db.Column(db.String(100))       # 소제목 (예: "창립기")
    summary = db.Column(db.Text)               # 연혁 총평
    summary_title = db.Column(db.String(100))  # 요약 제목
    display_order = db.Column(db.Integer, default=0)

    items = db.relationship(
        'HistoryItem',
        backref='section',
        lazy='dynamic',
        order_by='HistoryItem.display_order'
    )

    def __repr__(self):
        return f'<HistorySection {self.subtitle}>'

    def to_dict(self):
        return {
            'id': self.id,
            'subtitle': self.subtitle,
            'summary': self.summary,
            'summary_title': self.summary_title,
            'display_order': self.display_order,
            'items': [item.to_dict() for item in self.items]
        }


class HistoryItem(db.Model):
    """걸어온 길 - 개별 연혁 항목"""
    __tablename__ = 'history_items'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('history_sections.id'), nullable=False)
    year = db.Column(db.Integer)  # nullable - 연도 없는 항목 가능
    content = db.Column(db.Text, nullable=False)
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<HistoryItem {self.year}: {self.content[:20]}>'

    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'content': self.content,
            'display_order': self.display_order
        }


# ============================================================================
# 4. 콘텐츠 - 가변적 자료 (게시판)
# ============================================================================

# 첨부파일 연결 테이블 (M:N)
notice_attachments = db.Table(
    'notice_attachments',
    db.Column('notice_id', db.Integer, db.ForeignKey('notices.id'), primary_key=True),
    db.Column('file_id', db.Integer, db.ForeignKey('files.id'), primary_key=True)
)

activity_attachments = db.Table(
    'activity_attachments',
    db.Column('activity_id', db.Integer, db.ForeignKey('activity_posts.id'), primary_key=True),
    db.Column('file_id', db.Integer, db.ForeignKey('files.id'), primary_key=True)
)


class ActivityCategory(db.Model, DisplayOrderMixin):
    """활동후기 카테고리"""
    __tablename__ = 'activity_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(20), default='#6d28d9')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ActivityCategory {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'display_order': self.display_order,
            'is_active': self.is_active
        }


class Notice(db.Model, TimestampMixin):
    """공지사항"""
    __tablename__ = 'notices'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    is_pinned = db.Column(db.Boolean, default=False)

    attachments = db.relationship('File', secondary=notice_attachments, backref='notices')

    def __repr__(self):
        return f'<Notice {self.title[:30]}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'is_pinned': self.is_pinned,
            'attachments': [f.to_dict() for f in self.attachments],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ActivityPost(db.Model, TimestampMixin):
    """활동후기"""
    __tablename__ = 'activity_posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    category = db.Column(db.String(50))  # ActivityCategory.name 참조
    thumbnail_file_id = db.Column(db.Integer, db.ForeignKey('files.id'))
    thumbnail_url = db.Column(db.String(500))  # 외부 URL 직접 저장

    thumbnail = db.relationship('File', backref='activity_posts')
    attachments = db.relationship('File', secondary=activity_attachments, backref='activity_posts_attached')

    def __repr__(self):
        return f'<ActivityPost {self.title[:30]}>'

    @property
    def image_url(self):
        """
        썸네일 URL 반환 (우선순위)
        1. 직접 지정된 썸네일 URL
        2. 업로드된 썸네일 파일
        3. 콘텐츠 내 첫 번째 이미지
        """
        if self.thumbnail_url:
            # 레거시 /static/uploads/ 경로 제거
            url = self.thumbnail_url
            if url.startswith('/static/uploads/'):
                url = url.replace('/static/uploads/', '/uploads/')
            return url
        if self.thumbnail:
            return self.thumbnail.url
        if self.content:
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', self.content)
            if match:
                url = match.group(1)
                # 레거시 /static/uploads/ 경로 제거
                if url.startswith('/static/uploads/'):
                    url = url.replace('/static/uploads/', '/uploads/')
                return url
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'image_url': self.image_url,
            'attachments': [f.to_dict() for f in self.attachments],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Newsletter(db.Model):
    """소식지"""
    __tablename__ = 'newsletters'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    issue_number = db.Column(db.Integer)           # 호수
    description = db.Column(db.Text)               # 소식지 설명/요약
    content_type = db.Column(db.String(10), default='pdf')  # 'pdf' 또는 'html'

    # PDF 파일
    pdf_file_id = db.Column(db.Integer, db.ForeignKey('files.id'))
    pdf_url = db.Column(db.String(500))            # 외부 PDF URL

    # 웹 콘텐츠
    external_url = db.Column(db.String(500))       # 온라인 뷰어 URL (Stibee 등)
    html_content = db.Column(db.Text)              # 크롤링된 HTML

    published_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pdf_file = db.relationship('File', foreign_keys=[pdf_file_id])

    def __repr__(self):
        return f'<Newsletter #{self.issue_number}: {self.title[:20]}>'

    @property
    def file_url(self):
        """PDF 파일 URL"""
        if self.pdf_url:
            # 레거시 /static/uploads/ 경로 제거
            url = self.pdf_url
            if url.startswith('/static/uploads/'):
                url = url.replace('/static/uploads/', '/uploads/')
            return url
        if self.pdf_file:
            return self.pdf_file.url
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'issue_number': self.issue_number,
            'description': self.description,
            'content_type': self.content_type,
            'file_url': self.file_url,
            'external_url': self.external_url,
            'html_content': self.html_content,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================================
# 5. 후원 신청
# ============================================================================

class DonationApplication(db.Model):
    """후원 신청서"""
    __tablename__ = 'donation_applications'

    id = db.Column(db.Integer, primary_key=True)

    # 신청자 기본 정보
    name = db.Column(db.String(100), nullable=False)
    birth_year = db.Column(db.Integer)
    birth_month = db.Column(db.Integer)
    birth_day = db.Column(db.Integer)
    address = db.Column(db.String(500))
    phone = db.Column(db.String(20))
    occupation = db.Column(db.String(100))

    # 출금 정보
    account_number = db.Column(db.String(50))
    bank_name = db.Column(db.String(50))
    resident_number = db.Column(db.String(20))  # 암호화 저장 권장

    # 후원 정보
    amount = db.Column(db.Integer)               # 월 후원 금액
    withdrawal_date = db.Column(db.Integer)      # 출금일 (7, 16, 26)

    # 동의 및 서명
    privacy_consent = db.Column(db.Boolean, default=False)
    signature = db.Column(db.Text)               # Base64 서명 이미지

    # 처리 상태
    is_processed = db.Column(db.Boolean, default=False)
    processed_at = db.Column(db.DateTime)
    admin_note = db.Column(db.Text)              # 관리자 메모

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 이전 버전 호환 필드 (deprecated)
    email = db.Column(db.String(255))
    donation_type = db.Column(db.String(20), default='monthly')
    payment_method = db.Column(db.String(50))
    message = db.Column(db.Text)

    def __repr__(self):
        return f'<DonationApplication {self.name}>'

    @property
    def birth_date_display(self):
        """생년월일 표시"""
        if self.birth_year and self.birth_month and self.birth_day:
            return f"{self.birth_year}.{self.birth_month:02d}.{self.birth_day:02d}"
        return None

    @property
    def amount_display(self):
        """금액 표시 (천 단위 쉼표)"""
        if self.amount:
            return f"{self.amount:,}원"
        return None

    @property
    def withdrawal_date_display(self):
        """출금일 표시"""
        if self.withdrawal_date:
            return f"매월 {self.withdrawal_date}일"
        return None

    def mark_processed(self, note=None):
        """처리 완료 표시"""
        self.is_processed = True
        self.processed_at = datetime.utcnow()
        if note:
            self.admin_note = note

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'birth_date': self.birth_date_display,
            'address': self.address,
            'phone': self.phone,
            'occupation': self.occupation,
            'account_number': self.account_number,
            'bank_name': self.bank_name,
            'amount': self.amount,
            'amount_display': self.amount_display,
            'withdrawal_date': self.withdrawal_date,
            'withdrawal_date_display': self.withdrawal_date_display,
            'privacy_consent': self.privacy_consent,
            'is_processed': self.is_processed,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================================
# 대중교통 정보
# ============================================================================

class BusStop(db.Model, DisplayOrderMixin):
    """주변 정류장"""
    __tablename__ = 'bus_stops'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<BusStop {self.name}>'


class BusRoute(db.Model, DisplayOrderMixin):
    """주변 버스 노선"""
    __tablename__ = 'bus_routes'

    TYPES = ['일반', '좌석', '마을']

    id = db.Column(db.Integer, primary_key=True)
    route_type = db.Column(db.String(20), nullable=False, default='일반')  # 일반, 좌석, 마을
    name = db.Column(db.String(100), nullable=False)  # 버스 번호/이름

    def __repr__(self):
        return f'<BusRoute {self.route_type} {self.name}>'


class OperatingHours(db.Model, DisplayOrderMixin):
    """운영시간 정보"""
    __tablename__ = 'operating_hours'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 예: 이주민 인권 상담, 한글교실
    schedule = db.Column(db.Text)  # 운영시간 설명 (여러 줄 가능)

    def __repr__(self):
        return f'<OperatingHours {self.name}>'


class OfficeInfo(db.Model):
    """사무실 정보 (싱글톤)"""
    __tablename__ = 'office_info'

    id = db.Column(db.Integer, primary_key=True)
    office_hours = db.Column(db.Text)  # 사무실 근무시간
    closed_days = db.Column(db.String(255))  # 휴무일

    @classmethod
    def get(cls):
        """싱글톤 인스턴스 반환"""
        instance = cls.query.first()
        if not instance:
            instance = cls()
            db.session.add(instance)
            db.session.commit()
        return instance


# ============================================================================
# 15. SSG 빌드 상태
# ============================================================================

class BuildStatus(db.Model):
    """SSG 빌드 상태 관리"""
    __tablename__ = 'build_status'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='idle')  # idle, building, success, failed
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    triggered_by = db.Column(db.String(100))  # 빌드를 트리거한 작업 (예: 'notice_created')

    @classmethod
    def get_current(cls):
        """현재 빌드 상태 반환"""
        status = cls.query.order_by(cls.id.desc()).first()
        if not status:
            status = cls(status='idle')
            db.session.add(status)
            db.session.commit()
        return status

    @classmethod
    def start_build(cls, triggered_by='manual'):
        """빌드 시작"""
        status = cls(
            status='building',
            started_at=datetime.utcnow(),
            triggered_by=triggered_by
        )
        db.session.add(status)
        db.session.commit()
        return status

    def complete(self, success=True, error_message=None):
        """빌드 완료"""
        self.status = 'success' if success else 'failed'
        self.completed_at = datetime.utcnow()
        if error_message:
            self.error_message = error_message
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'triggered_by': self.triggered_by,
            'duration': (self.completed_at - self.started_at).total_seconds() if self.completed_at and self.started_at else None
        }
