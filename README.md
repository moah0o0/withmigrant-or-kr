# 양산외국인노동자의집 홈페이지

Flask 기반 SSG(Static Site Generation) 하이브리드 시스템으로 구축된 비영리단체 홈페이지입니다.

## 프로젝트 개요

정적 사이트의 빠른 속도와 동적 관리의 편의성을 결합한 하이브리드 시스템입니다.
- **사용자**: 빌드된 정적 HTML 제공 (빠른 속도)
- **관리자**: Flask 기반 CMS로 콘텐츠 관리
- **자동화**: DB 변경 시 자동으로 정적 사이트 재생성

---

## 기술 스택

### 백엔드
- **Flask 3.0** - 웹 프레임워크
- **SQLAlchemy** - ORM
- **SQLite** - 데이터베이스
- **Gunicorn** - WSGI 서버

### 프론트엔드
- **Jinja2** - 템플릿 엔진
- **Tailwind CSS** - CSS 프레임워크
- **Alpine.js** - 간단한 인터랙션
- **Toast UI Editor** - WYSIWYG 에디터
- **SortableJS** - 드래그앤드롭 정렬

### 빌드 시스템
- **SSG 빌드**: Python 기반 정적 사이트 생성
- **자동 트리거**: DB 변경 감지 → 자동 빌드
- **빌드 모니터링**: 실시간 상태 확인

---

## 주요 기능

### 사용자 페이지 (정적)
- 🏠 메인 페이지
- 📢 공지사항 목록/상세
- 📸 활동후기 목록/상세 (카테고리별)
- 📰 소식지 목록/상세
- ℹ️ 소개 페이지 (연혁, 사업분야, 오시는 길)
- 💝 함께하기 (후원 신청)

### 관리자 페이지 (동적)
- 🔐 로그인 / 계정 관리
- 📊 대시보드 (빌드 상태, 통계)
- 📝 콘텐츠 관리 (공지사항, 활동후기, 소식지)
- ⚙️ 사이트 설정 (사이트 정보, 사업분야, 후원 안내)
- 📜 연혁 관리
- 🚌 오시는 길 (대중교통, 운영시간)
- 💰 후원 신청 내역 확인 및 PDF 생성
- 🏗️ 빌드 히스토리

### 자동화 기능
- ✅ DB 변경 감지 → 자동 빌드 트리거
- ✅ 백그라운드 빌드 (관리자 작업 방해 안함)
- ✅ 빌드 상태 실시간 모니터링
- ✅ 빌드 히스토리 기록 및 조회

---

## 프로젝트 구조

```
homepage/
├── app.py                    # Flask 메인 앱
├── models.py                 # 데이터베이스 모델 (21개)
├── config.py                 # 설정 파일
├── build.py                  # SSG 빌드 엔진
├── build_triggers.py         # 자동 빌드 트리거 시스템
├── background_builder.py     # 백그라운드 빌드 실행
├── run_build.py              # 독립 프로세스 빌드
├── ssg_serve.py              # 정적 파일 개발 서버
├── requirements.txt          # Python 패키지 목록
├── data.db                   # SQLite 데이터베이스
│
├── admin/                    # 관리자 모듈
│   ├── __init__.py
│   ├── routes.py             # 관리자 라우트 (60+ 엔드포인트)
│   ├── auth.py               # 인증 데코레이터
│   └── utils.py              # 파일 업로드 유틸리티
│
├── templates/                # Jinja2 템플릿
│   ├── ssg/                  # 정적 사이트 템플릿
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── intro.html
│   │   ├── notice.html
│   │   ├── activity.html
│   │   ├── newsletter.html
│   │   └── donation.html
│   └── admin/                # 관리자 페이지 템플릿
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       └── [기능별 템플릿]
│
├── static/                   # 정적 파일
│   ├── css/
│   │   ├── design-system.css
│   │   └── styles.css
│   ├── js/
│   │   └── main.js
│   └── images/
│       ├── logo.svg
│       └── logo-text.svg
│
├── dist/                     # 빌드 결과물 (정적 사이트)
│   ├── index.html
│   ├── intro.html
│   ├── notice/
│   ├── activity/
│   ├── newsletter/
│   ├── donation.html
│   ├── static/
│   └── uploads/              # 업로드 파일
│
└── logs/                     # 로그 파일
    ├── app.log               # 앱 로그
    └── build.log             # 빌드 로그
```

---

## 빠른 시작

### 1. 환경 설정

```bash
# Python 3.9+ 필요
python3 --version

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일 생성:

```bash
# 개발 환경
STATIC_DOMAIN=http://localhost:3000
API_DOMAIN=http://localhost:8000
STATIC_SITE_URL=http://localhost:3000

SECRET_KEY=your-secret-key-change-this
DONATION_EMAIL=happysoli@hanmail.net
```

### 3. 데이터베이스 초기화

```bash
# Flask shell에서 DB 생성
python3
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 4. 관리자 계정 생성

```bash
python3
>>> from app import app, db
>>> from models import AdminUser
>>> with app.app_context():
...     admin = AdminUser(
...         username='admin',
...         email='admin@example.com',
...         is_super_admin=True
...     )
...     admin.set_password('your-password')
...     db.session.add(admin)
...     db.session.commit()
>>> exit()
```

### 5. Flask 앱 실행

```bash
python3 app.py
# http://localhost:8000 에서 접속
# 관리자 로그인: http://localhost:8000/login
```

### 6. SSG 빌드 및 서빙

```bash
# 정적 사이트 빌드
python3 build.py

# 개발 서버로 정적 사이트 확인
python3 ssg_serve.py
# http://localhost:3000 에서 접속
```

---

## 개발 가이드

### 디자인 원칙

- **노션 스타일**: 깔끔한 카드 UI
- **심플함**: 과한 장식 지양
- **반응형**: 모바일 우선
- **한글**: UI와 주석 모두 한글

### 색상 팔레트

```css
--primary: #3B82F6      /* 파란색 */
--dark-800: #1e293b     /* 진한 회색 */
--dark-600: #475569     /* 중간 회색 */
```

### 모델 추가하기

```python
# models.py
class NewModel(db.Model, DisplayOrderMixin):
    """새 모델 설명"""
    __tablename__ = 'new_model'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

### 관리자 CRUD 라우트 패턴

```python
# admin/routes.py
@admin_bp.route('/items')
@login_required
def list_items():
    """목록"""
    items = NewModel.query.all()
    return render_template('admin/items/list.html', items=items)

@admin_bp.route('/items/add', methods=['GET', 'POST'])
@login_required
def add_item():
    """추가"""
    if request.method == 'POST':
        item = NewModel(name=request.form['name'])
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('admin.list_items'))
    return render_template('admin/items/form.html')

@admin_bp.route('/items/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    """수정"""
    item = NewModel.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form['name']
        db.session.commit()
        return redirect(url_for('admin.list_items'))
    return render_template('admin/items/form.html', item=item)

@admin_bp.route('/items/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    """삭제"""
    item = NewModel.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('admin.list_items'))
```

### 자동 빌드 트리거 추가

```python
# build_triggers.py
# 자동 빌드가 필요한 모델에 이벤트 리스너 추가

@event.listens_for(NewModel, 'after_insert')
@event.listens_for(NewModel, 'after_update')
@event.listens_for(NewModel, 'after_delete')
def trigger_build_on_new_model_change(mapper, connection, target):
    """NewModel 변경 시 빌드 트리거"""
    trigger_build(triggered_by=f'NewModel #{target.id}')
```

---

## 자동 빌드 시스템

### 작동 원리

```
DB 변경 발생
    ↓
build_triggers.py (이벤트 감지)
    ↓
background_builder.py (비동기 실행)
    ↓
run_build.py (독립 프로세스)
    ↓
build.py (실제 빌드)
    ↓
dist/ 폴더에 정적 사이트 생성
```

### 자동 빌드 대상 모델

- **콘텐츠**: Notice, ActivityPost, Newsletter, ActivityCategory
- **사이트 정보**: SiteInfo, BusinessArea, SponsorshipInfo
- **후원**: VolunteerArea, DonationArea, DonationUsage
- **연혁**: HistorySection, HistoryItem
- **활동**: ActivityPhoto
- **교통**: BusStop, BusRoute, OperatingHours, OfficeInfo

### 빌드 상태 확인

- **대시보드**: `/dashboard` - 실시간 빌드 상태
- **빌드 히스토리**: `/build/history` - 전체 빌드 내역
- **API**: `/build/status` - JSON 형식 상태

### 수동 빌드

```bash
# 커맨드라인
python3 build.py

# 또는 관리자 페이지에서
# "빌드 히스토리" 페이지 → "수동 빌드" 버튼
```

---

## 리소스 사용량

### 단일 앱 기준

- **메모리**: 50-75 MB per worker
- **디스크**: ~145 MB (업로드 파일 포함)
- **CPU**: < 5% (평소), 30-50% (빌드 시)

### 3개 앱 동시 운영 시 (Vultr $12/월 기준)

```yaml
서버 사양:
  CPU: 2 vCPU
  RAM: 2 GB
  Disk: 55 GB SSD
  트래픽: 2 TB/월

Gunicorn 워커:
  앱당 워커: 3개
  총 워커: 9개
  메모리 사용: ~675 MB

예상 성능:
  동시 접속: 50-100명
  응답 시간: < 300ms
  월간 방문자: 앱당 5,000명
```
---

## 배포

상세한 배포 가이드는 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)를 참조하세요.

---

## 로그 확인

```bash
# 앱 로그 (실시간)
tail -f logs/app.log

# 빌드 로그 (실시간)
tail -f logs/build.log

# 최근 50줄
tail -50 logs/app.log
```

---

## 트러블슈팅

### 빌드가 시작되지 않음

```bash
# 로그 확인
tail -f logs/app.log

# 빌드 프로세스 확인
ps aux | grep run_build.py
```

### 이미지가 표시되지 않음

- `dist/uploads/` 폴더 확인
- 파일 권한 확인 (755)
- Nginx 설정 확인 (`/uploads/` 경로)

### 후원 신청이 제출되지 않음

- 브라우저 콘솔 확인 (F12 → Network)
- API_DOMAIN 환경변수 확인
- CORS 설정 확인 (app.py)

---

## 라이선스

이 프로젝트는 비영리단체 홈페이지 CMS로 개발되었습니다.

---

## 문의

- 이메일: happysoli@hanmail.net
- 주소: 경상남도 양산시 북안북7길35 양산시근로자종합복지관 1층
- 전화: 055-388-0988
