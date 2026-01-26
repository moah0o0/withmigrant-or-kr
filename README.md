# 양산외국인노동자의집 홈페이지

Flask 기반 SSG(Static Site Generation) 하이브리드 시스템으로 구축된 비영리단체 홈페이지

## 프로젝트 개요

**목적**: (사)함께하는세상 양산외국인노동자의집 공식 홈페이지
**특징**: 정적 사이트의 빠른 속도 + Flask 기반 동적 관리 시스템

- **사용자**: 빌드된 정적 HTML 제공 (빠른 로딩)
- **관리자**: Flask CMS로 콘텐츠 관리
- **자동화**: DB 변경 시 자동으로 정적 사이트 재생성

---

## 도메인 정보

### 프로덕션
- **정적 사이트**: https://withmigrant.or.kr
- **관리자 페이지**: https://admin.withmigrant.or.kr

### 개발 환경
- **정적 사이트**: http://localhost:3000
- **Flask 앱**: http://localhost:8000

---

## 서버 환경

### 서버 구성
```
/var/www/migrant-yangsan/           # 프로젝트 루트
├── venv/                           # Python 가상환경
├── dist/                           # 빌드된 정적 사이트
│   ├── index.html
│   ├── intro.html
│   ├── notice/
│   ├── activity/
│   ├── newsletter/
│   ├── donation.html
│   ├── static/
│   └── uploads/                    # 업로드 파일 (16MB 제한)
├── data.db                         # SQLite 데이터베이스
└── logs/
    ├── app.log
    └── build.log
```

### 웹 서버 스택
- **Nginx**: 정적 파일 서빙 + 리버스 프록시
- **Gunicorn**: WSGI 서버 (Flask 앱 실행)
- **Systemd**: 서비스 관리 (`migrant-yangsan.service`)
- **파일 권한**: `www-data:www-data` (755 for files, 775 for uploads)

---

## 기술 스택

### 백엔드
- **Flask 3.0** - 웹 프레임워크
- **SQLAlchemy** - ORM
- **SQLite** - 데이터베이스
- **Gunicorn** - WSGI 서버

### 프론트엔드
- **Jinja2** - 템플릿 엔진
- **Tailwind CSS** - 스타일링
- **Alpine.js** - 인터랙션
- **Toast UI Editor** - WYSIWYG 에디터
- **SortableJS** - 드래그앤드롭

### 빌드 시스템
- **SSG 빌드**: Python 기반 정적 사이트 생성 (`build.py`)
- **자동 트리거**: DB 변경 감지 → 자동 빌드 (`build_triggers.py`)
- **백그라운드 실행**: 비동기 빌드로 관리자 작업 방해 안 함

---

## 자동 배포 (GitHub Actions)

**트리거**: `main` 브랜치에 push 시 자동 배포

### 배포 프로세스
1. GitHub Actions에서 SSH로 서버 접속
2. `git reset --hard origin/main` (서버 변경사항 무시)
3. `pip install -r requirements.txt` (패키지 업데이트)
4. `python file_manager.py all` (파일 관리: DB 동기화 + 고아 파일 확인)
5. `python build.py` (정적 사이트 빌드)
6. 파일 권한 설정 (`chown`, `chmod`)
7. `systemctl restart migrant-yangsan` (서비스 재시작)

### 필요한 GitHub Secrets
- `SSH_HOST`: 서버 IP 주소
- `SSH_USER`: SSH 사용자명 (root 권장)
- `SSH_PRIVATE_KEY`: SSH 개인키 (ed25519)

상세 설정 가이드: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)

---

## 로컬 개발 환경 설정

### 1. 환경 설정
```bash
# Python 3.9+ 필요
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경변수 설정 (.env)
```bash
# 개발 환경
STATIC_DOMAIN=http://localhost:3000
API_DOMAIN=http://localhost:8000

SECRET_KEY=your-secret-key-change-this
DONATION_EMAIL=happysoli@hanmail.net
FLASK_DEBUG=True
```

### 3. 데이터베이스 초기화
```bash
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
# 관리자: http://localhost:8000/login
```

### 6. 정적 사이트 빌드 및 서빙
```bash
# 빌드
python3 build.py

# 개발 서버로 확인
python3 ssg_serve.py
# http://localhost:3000 에서 접속
```

---

## 주요 기능

### 사용자 페이지 (정적)
- 메인 페이지
- 공지사항 목록/상세
- 활동후기 목록/상세 (카테고리별)
- 소식지 목록/상세
- 소개 (연혁, 사업분야, 오시는 길)
- 함께하기 (후원 신청)

### 관리자 페이지 (동적)
- 로그인 / 계정 관리
- 대시보드 (빌드 상태, 통계)
- 콘텐츠 관리 (공지사항, 활동후기, 소식지)
- 사이트 설정 (사이트 정보, 사업분야, 후원 안내)
- 연혁 관리
- 오시는 길 (대중교통, 운영시간)
- 후원 신청 내역 확인 및 PDF 생성
- 빌드 히스토리

### 자동화 시스템
- DB 변경 감지 → 자동 빌드 트리거
- 백그라운드 빌드 (관리자 작업 방해 안함)
- 빌드 상태 실시간 모니터링
- 빌드 히스토리 기록 및 조회

---

## 프로젝트 구조

```
homepage/
├── app.py                    # Flask 메인 앱
├── models.py                 # 데이터베이스 모델 (21개)
├── config.py                 # 설정 파일
├── build.py                  # SSG 빌드 엔진
├── build_triggers.py         # 자동 빌드 트리거
├── background_builder.py     # 백그라운드 빌드 실행
├── run_build.py              # 독립 프로세스 빌드
├── file_manager.py           # 파일 관리 (DB 동기화, 고아 파일 정리)
├── ssg_serve.py              # 정적 파일 개발 서버
├── requirements.txt          # Python 패키지 목록
├── data.db                   # SQLite 데이터베이스
│
├── .github/workflows/
│   └── deploy.yml            # GitHub Actions 배포 워크플로우
│
├── admin/                    # 관리자 모듈
│   ├── routes.py             # 관리자 라우트 (60+ 엔드포인트)
│   ├── auth.py               # 인증 데코레이터
│   └── utils.py              # 파일 업로드/삭제 유틸리티
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
│
├── static/                   # 정적 파일
│   ├── css/
│   ├── js/
│   └── images/
│
└── dist/                     # 빌드 결과물 (정적 사이트)
    ├── index.html
    ├── notice/
    ├── activity/
    ├── newsletter/
    ├── donation.html
    ├── static/
    └── uploads/              # 업로드 파일 (Git 제외)
```

---

## 파일 관리 시스템

업로드된 파일과 DB 레코드의 동기화를 관리하는 통합 도구입니다.

### 기능
- **DB 동기화**: `dist/uploads`에 있지만 DB에 없는 파일을 자동 등록
- **고아 파일 확인**: 어디서도 사용되지 않는 파일 목록 출력
- **고아 파일 제거**: 사용하지 않는 파일 삭제 (확인 후)

### 사용법

#### 대화형 모드
```bash
python3 file_manager.py
# 메뉴에서 1-4 선택
```

#### 명령행 옵션 (서버 자동화)
```bash
# DB 동기화
python3 file_manager.py sync

# 고아 파일 확인
python3 file_manager.py check

# 고아 파일 제거 (확인 필요)
python3 file_manager.py remove

# 전체 실행 (동기화 + 확인)
python3 file_manager.py all
```

### 자동 실행
- **GitHub Actions**: Push 시 자동으로 `file_manager.py all` 실행
- **정기 점검**: Cron으로 월 1회 실행 권장
```bash
# 예: 매월 1일 자정에 확인
0 0 1 * * cd /var/www/migrant-yangsan && python3 file_manager.py check >> /var/log/file_check.log 2>&1
```

---

## 서버 관리 명령어

### 로그 확인
```bash
# 앱 로그 (실시간)
tail -f /var/www/migrant-yangsan/logs/app.log

# 빌드 로그 (실시간)
tail -f /var/www/migrant-yangsan/logs/build.log

# 최근 50줄
tail -50 /var/www/migrant-yangsan/logs/app.log
```

### 서비스 관리
```bash
# 서비스 상태 확인
systemctl status migrant-yangsan

# 서비스 재시작
systemctl restart migrant-yangsan

# 서비스 로그 확인
journalctl -u migrant-yangsan -f
```

### 수동 빌드
```bash
cd /var/www/migrant-yangsan
source venv/bin/activate
python build.py
```

### 권한 수정 (업로드 파일 문제 시)
```bash
chown -R www-data:www-data /var/www/migrant-yangsan/dist
chmod -R 755 /var/www/migrant-yangsan/dist
chmod -R 775 /var/www/migrant-yangsan/dist/uploads
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
- 파일 권한 확인 (755 또는 775)
- Nginx 설정 확인 (`/uploads/` 경로)

### 후원 신청이 제출되지 않음
- 브라우저 콘솔 확인 (F12 → Network)
- `API_DOMAIN` 환경변수 확인
- CORS 설정 확인 ([config.py](config.py#L28-L31))

### GitHub Actions 배포 실패
- GitHub Secrets 확인 (SSH_HOST, SSH_USER, SSH_PRIVATE_KEY)
- 서버 SSH 접속 테스트
- Actions 탭에서 로그 확인

---

## 리소스 사용량

### 단일 앱 기준
- **메모리**: 50-75 MB per worker (Gunicorn)
- **디스크**: ~145 MB (업로드 파일 별도)
- **CPU**: < 5% (평소), 30-50% (빌드 시)

### 예상 성능 (Vultr $12/월)
- **동시 접속**: 50-100명
- **응답 시간**: < 300ms
- **월간 방문자**: ~5,000명

---

## 라이선스

이 프로젝트는 (사)함께하는세상 양산외국인노동자의집을 위해 개발되었습니다.
