# 단계별 배포 가이드 (Vultr 서버)

이 가이드는 **실제로 명령어를 하나씩 입력하면서** 배포하는 과정입니다.

---

## 🎯 목표
- Vultr $12/월 서버에 양산외국인노동자의집 홈페이지 배포
- 나중에 2개 앱 더 추가 가능하도록 설정

---

## STEP 1: Vultr 서버 생성

### 1-1. Vultr 가입 및 서버 생성

1. https://www.vultr.com 접속 → 회원가입
2. **Deploy New Server** 클릭
3. 설정:
   - **Server Type**: Cloud Compute - Shared CPU
   - **Location**: Seoul, KR (서울) 또는 Tokyo, JP (도쿄)
   - **OS**: Ubuntu 22.04 LTS x64
   - **Plan**: High Performance - $12/mo (2 vCPU, 2GB RAM, 55GB SSD)
   - **Server Hostname**: migrant-yangsan (원하는 이름)
4. **Deploy Now** 클릭

### 1-2. 서버 정보 확인

서버 생성 후 (약 1-2분 소요):
- **IP Address**: 예) 123.45.67.89
- **Username**: root
- **Password**: 자동 생성된 비밀번호 복사

---

## STEP 2: 서버 접속

### Mac/Linux 사용자

```bash
# 터미널에서 실행
ssh root@123.45.67.89

# 비밀번호 입력 (복사한 비밀번호 붙여넣기)
# 참고: 비밀번호 입력 시 화면에 표시 안 됨
```

### Windows 사용자

**방법 1: PowerShell**
```powershell
ssh root@123.45.67.89
```

**방법 2: PuTTY**
- PuTTY 다운로드: https://www.putty.org/
- Host Name: 123.45.67.89
- Port: 22
- Connection Type: SSH
- Open 클릭 → 비밀번호 입력

---

## STEP 3: 서버 초기 설정

### 3-1. 시스템 업데이트

```bash
# 패키지 목록 업데이트
apt update

# 패키지 업그레이드 (Y 입력)
apt upgrade -y

# 완료까지 약 2-5분 소요
```

### 3-2. 필수 패키지 설치

```bash
# 한 번에 복사해서 붙여넣기
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    git \
    ufw \
    curl \
    wget \
    htop

# 설치 확인
python3 --version  # Python 3.10.x 출력되어야 함
nginx -v           # nginx version 출력되어야 함
git --version      # git version 출력되어야 함
```

### 3-3. 방화벽 설정

```bash
# SSH 허용
ufw allow OpenSSH

# HTTP/HTTPS 허용
ufw allow 'Nginx Full'

# 방화벽 활성화 (y 입력)
ufw enable

# 상태 확인
ufw status
# Status: active 출력되어야 함
```

---

## STEP 4: 프로젝트 배포

### 4-1. 프로젝트 디렉터리 생성

```bash
# /var/www 디렉터리로 이동
cd /var/www

# 프로젝트 클론
git clone https://github.com/moah0o0/withmigrant-or-kr.git migrant-yangsan

# 디렉터리 확인
ls -la
# migrant-yangsan 폴더가 보여야 함

# 프로젝트로 이동
cd migrant-yangsan
```

### 4-2. 가상환경 설정

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 프롬프트가 (venv)로 바뀌면 성공
# 예: (venv) root@migrant-yangsan:/var/www/migrant-yangsan#

# pip 업그레이드
pip install --upgrade pip

# 패키지 설치 (약 1-2분 소요)
pip install -r requirements.txt

# Gunicorn 설치
pip install gunicorn

# 설치 확인
pip list | grep -i flask
# Flask, Flask-CORS, Flask-SQLAlchemy 등이 보여야 함
```

### 4-3. 환경변수 설정

```bash
# .env 파일 생성
nano .env
```

**nano 에디터에서 다음 내용 입력** (복사해서 붙여넣기):

```bash
# 프로덕션 환경
STATIC_DOMAIN=https://migrant-yangsan.org
API_DOMAIN=https://admin.migrant-yangsan.org
STATIC_SITE_URL=https://migrant-yangsan.org

# 보안 키 생성 (다음 명령어 실행 후 결과 복사)
# python3 -c 'import secrets; print(secrets.token_hex(32))'
SECRET_KEY=여기에_위_명령어_결과_붙여넣기

# 후원 이메일
DONATION_EMAIL=happysoli@hanmail.net

# Flask 설정
FLASK_ENV=production
DEBUG=False
```

**nano 에디터 사용법**:
- `Ctrl + O` → Enter (저장)
- `Ctrl + X` (종료)

**SECRET_KEY 생성**:
```bash
# 비밀키 생성
python3 -c 'import secrets; print(secrets.token_hex(32))'

# 출력된 값 복사 (예: a3f2b8d9e4c1...)

# .env 파일 다시 열기
nano .env

# SECRET_KEY= 부분에 복사한 값 붙여넣기
# 저장 후 종료 (Ctrl+O, Enter, Ctrl+X)
```

### 4-4. 데이터베이스 초기화

```bash
# Python 인터프리터 실행
python3

# 다음 명령어들을 하나씩 입력
```

```python
from app import app, db
from models import AdminUser, SiteInfo

# DB 생성
with app.app_context():
    db.create_all()
    print("✓ 데이터베이스 생성 완료")

# 종료
exit()
```

**사이트 정보 및 관리자 계정 생성**:

```bash
python3
```

```python
from app import app, db
from models import AdminUser, SiteInfo

with app.app_context():
    # 사이트 정보
    site = SiteInfo(
        org_name='사단법인 함께하는세상',
        site_name='양산외국인노동자의집',
        slogan='더불어 사는 세상',
        intro_text='고향을 떠나 낯선 이국땅에서 꿈을 키우며 더불어 살아가는 이주민들과 함께 만듭니다',
        address='경상남도 양산시 북안북7길35 양산시근로자종합복지관 1층',
        tel='055-388-0988',
        fax='055-366-0988',
        email='happysoli@hanmail.net',
        facebook='https://www.facebook.com/yangsanmigrant',
        representative='김덕한',
        bank_name='농협',
        bank_account='301-0135-5765-11',
        bank_holder='(사)함께하는세상'
    )
    db.session.add(site)

    # 관리자 계정
    admin = AdminUser(
        username='admin',
        email='admin@migrant-yangsan.org',
        is_super_admin=True
    )
    admin.set_password('임시비밀번호1234!')  # 나중에 꼭 변경하세요!
    db.session.add(admin)

    db.session.commit()
    print("✓ 사이트 정보 및 관리자 계정 생성 완료")

exit()
```

### 4-5. 초기 빌드

```bash
# 정적 사이트 빌드
python3 build.py

# 다음과 같은 출력이 나와야 함:
# ==================================================
# SSG 빌드 시작
# ==================================================
# [1/3] 정적 파일 복사
# ...
# ✓ 빌드 완료!
```

### 4-6. 권한 설정

```bash
# www-data 사용자에게 소유권 부여
chown -R www-data:www-data /var/www/migrant-yangsan

# 권한 설정
chmod -R 755 /var/www/migrant-yangsan
chmod -R 775 /var/www/migrant-yangsan/dist/uploads
chmod 664 /var/www/migrant-yangsan/data.db
chmod 775 /var/www/migrant-yangsan/logs

# 로그 디렉터리 생성
mkdir -p /var/www/migrant-yangsan/logs
chown -R www-data:www-data /var/www/migrant-yangsan/logs
```

---

## STEP 5: Gunicorn 설정

### 5-1. Gunicorn 설정 파일 생성

```bash
nano /var/www/migrant-yangsan/gunicorn.conf.py
```

**다음 내용 붙여넣기**:

```python
"""
Gunicorn 설정 파일
"""
import multiprocessing

# 서버 소켓
bind = "127.0.0.1:8001"
backlog = 2048

# 워커 프로세스
workers = 3  # 2 vCPU → 3 workers 권장
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# 프로세스 이름
proc_name = "migrant-yangsan"

# 로깅
accesslog = "/var/www/migrant-yangsan/logs/gunicorn-access.log"
errorlog = "/var/www/migrant-yangsan/logs/gunicorn-error.log"
loglevel = "info"

# 프리로드 (메모리 절약)
preload_app = True

# 데몬 모드
daemon = False

# 워커 재시작 설정
graceful_timeout = 30
```

저장: `Ctrl + O`, Enter, `Ctrl + X`

### 5-2. Gunicorn 테스트

```bash
# 가상환경 활성화 확인
source /var/www/migrant-yangsan/venv/bin/activate

# Gunicorn 실행 테스트
cd /var/www/migrant-yangsan
gunicorn -c gunicorn.conf.py app:app

# 다음과 같은 출력이 나오면 성공:
# [INFO] Starting gunicorn 21.2.0
# [INFO] Listening at: http://127.0.0.1:8001
# [INFO] Using worker: sync
# [INFO] Booting worker with pid: ...

# Ctrl + C 로 종료
```

### 5-3. Systemd 서비스 생성

```bash
nano /etc/systemd/system/migrant-yangsan.service
```

**다음 내용 붙여넣기**:

```ini
[Unit]
Description=양산외국인노동자의집 Flask App
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/migrant-yangsan
Environment="PATH=/var/www/migrant-yangsan/venv/bin"
EnvironmentFile=/var/www/migrant-yangsan/.env
ExecStart=/var/www/migrant-yangsan/venv/bin/gunicorn \
    -c /var/www/migrant-yangsan/gunicorn.conf.py \
    app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

저장: `Ctrl + O`, Enter, `Ctrl + X`

### 5-4. 서비스 시작

```bash
# systemd 데몬 재로드
systemctl daemon-reload

# 서비스 시작
systemctl start migrant-yangsan

# 서비스 상태 확인
systemctl status migrant-yangsan

# 다음과 같이 표시되어야 함:
# ● migrant-yangsan.service - 양산외국인노동자의집 Flask App
#    Loaded: loaded
#    Active: active (running)

# 부팅 시 자동 시작 설정
systemctl enable migrant-yangsan

# q 키를 눌러 종료
```

**문제 발생 시**:
```bash
# 로그 확인
journalctl -u migrant-yangsan -n 50

# 또는
tail -50 /var/www/migrant-yangsan/logs/gunicorn-error.log
```

---

## STEP 6: Nginx 설정

### 6-1. Nginx 설정 파일 생성

```bash
nano /etc/nginx/sites-available/migrant-yangsan
```

**다음 내용 붙여넣기** (도메인은 나중에 변경):

```nginx
# 정적 사이트 (migrant-yangsan.org)
server {
    listen 80;
    server_name migrant-yangsan.org www.migrant-yangsan.org 123.45.67.89;

    # 정적 파일 제공
    root /var/www/migrant-yangsan/dist;
    index index.html;

    # 로그
    access_log /var/log/nginx/migrant-yangsan-access.log;
    error_log /var/log/nginx/migrant-yangsan-error.log;

    # Gzip 압축
    gzip on;
    gzip_types text/html text/css application/javascript image/svg+xml;
    gzip_min_length 1000;

    # 정적 파일
    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    # 정적 리소스 (CSS, JS, 이미지)
    location /static/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 업로드 파일 (관리자 서버에서 프록시)
    location /uploads/ {
        proxy_pass http://127.0.0.1:8001/uploads/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 후원 신청
    location /donation/apply {
        proxy_pass http://127.0.0.1:8001/donation/apply;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # 파일 업로드 크기 제한
    client_max_body_size 10M;
}

# 관리자 서버 (admin.migrant-yangsan.org)
server {
    listen 80;
    server_name admin.migrant-yangsan.org;

    # 로그
    access_log /var/log/nginx/migrant-yangsan-admin-access.log;
    error_log /var/log/nginx/migrant-yangsan-admin-error.log;

    # Gunicorn으로 프록시
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 업로드 파일 직접 제공
    location /uploads/ {
        alias /var/www/migrant-yangsan/dist/uploads/;
        expires 7d;
    }

    # 파일 업로드 크기 제한
    client_max_body_size 50M;
}
```

**중요**: `123.45.67.89`를 실제 서버 IP로 변경하세요!

저장: `Ctrl + O`, Enter, `Ctrl + X`

### 6-2. Nginx 설정 활성화

```bash
# 심볼릭 링크 생성
ln -s /etc/nginx/sites-available/migrant-yangsan /etc/nginx/sites-enabled/

# 기본 사이트 비활성화
rm /etc/nginx/sites-enabled/default

# 설정 테스트
nginx -t

# 다음과 같이 표시되어야 함:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Nginx 재시작
systemctl restart nginx

# Nginx 상태 확인
systemctl status nginx
# Active: active (running) 이어야 함
```

---

## STEP 7: 테스트

### 7-1. IP로 접속 테스트

**브라우저에서**:
- 정적 사이트: `http://123.45.67.89` (실제 IP 입력)
- 관리자: `http://123.45.67.89:80` (Nginx를 통해)

**서버에서 테스트**:
```bash
# 정적 사이트
curl http://localhost

# 관리자 서버
curl http://localhost:8001/login

# 응답이 HTML로 오면 성공
```

### 7-2. 관리자 로그인 테스트

브라우저에서:
1. `http://123.45.67.89` 접속 (도메인 없으면 IP)
2. 관리자 페이지는 현재 IP로는 접근 불가 (도메인 설정 필요)

---

## STEP 8: 도메인 연결 (선택)

### 8-1. DNS 설정

도메인이 있다면:

```
A 레코드:
  migrant-yangsan.org           → 123.45.67.89
  www.migrant-yangsan.org       → 123.45.67.89
  admin.migrant-yangsan.org     → 123.45.67.89
```

### 8-2. SSL 인증서 (Let's Encrypt)

```bash
# Certbot 설치
apt install -y certbot python3-certbot-nginx

# 인증서 발급
certbot --nginx \
    -d migrant-yangsan.org \
    -d www.migrant-yangsan.org \
    -d admin.migrant-yangsan.org

# 이메일 입력
# 약관 동의: Y
# HTTP → HTTPS 리다이렉트: 2 선택
```

---

## 🎉 완료!

배포가 완료되었습니다!

### 접속 주소
- **정적 사이트**: http://123.45.67.89 (또는 도메인)
- **관리자**: http://123.45.67.89 (또는 admin.도메인)

### 관리자 계정
- **ID**: admin
- **비밀번호**: 임시비밀번호1234!

⚠️ **중요**: 관리자 비밀번호를 즉시 변경하세요!

---

## 유용한 명령어

```bash
# 서비스 재시작
systemctl restart migrant-yangsan
systemctl restart nginx

# 로그 확인
tail -f /var/www/migrant-yangsan/logs/gunicorn-error.log
tail -f /var/log/nginx/error.log

# 시스템 리소스 확인
htop
free -h
df -h

# 서비스 상태
systemctl status migrant-yangsan
systemctl status nginx
```

---

## 문제 발생 시

### Gunicorn이 시작 안 됨
```bash
journalctl -u migrant-yangsan -n 50
```

### Nginx 502 오류
```bash
systemctl status migrant-yangsan
tail -50 /var/www/migrant-yangsan/logs/gunicorn-error.log
```

### 포트 확인
```bash
netstat -tlnp | grep 8001
```

---

**다음 단계**: 추가 앱 2개 배포 (MIGRATION_GUIDE.md 참고)
