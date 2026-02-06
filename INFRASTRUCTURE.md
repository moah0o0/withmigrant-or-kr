# 인프라 구성 및 마이그레이션 기록

## 현재 아키텍처 (2026-02-06 기준)

```
[관리자] admin.withmigrant.or.kr
   └─ Vultr VPS + Coolify (Docker)
      └─ Flask Admin API + SSG 빌드 시스템
         ├─ 콘텐츠 CRUD → SQLite DB
         ├─ 파일 업로드 → Cloudflare R2
         └─ 빌드 완료 시 → wrangler로 Cloudflare Pages 배포

[정적 사이트] withmigrant.or.kr
   └─ Cloudflare Pages (Direct Upload)
      └─ build.py가 생성한 HTML/CSS/JS

[파일 저장소] uploads.withmigrant.or.kr
   └─ Cloudflare R2 (S3 호환)
      └─ 버킷: withmigrant-uploads
```

### 데이터 흐름

1. 관리자가 `admin.withmigrant.or.kr`에서 콘텐츠 수정
2. 파일 업로드 시 → R2에 직접 저장 (boto3)
3. 콘텐츠 저장 시 → `build_triggers.py`가 자동 빌드 트리거
4. `build.py` 실행 → DB에서 데이터 조회 → HTML 생성 → `dist/` 폴더에 출력
5. `run_build.py`가 `wrangler pages deploy dist/`로 Cloudflare Pages에 배포
6. 정적 사이트의 이미지 URL은 `https://uploads.withmigrant.or.kr/파일명`으로 자동 변환

---

## 서비스 구성

### Vultr VPS (Coolify)

- **admin 컨테이너**: Flask + Gunicorn + Wrangler CLI
- **Traefik**: 리버스 프록시 (admin.withmigrant.or.kr → admin:8000)
- **데이터**: `/root/withmigrant-yangsan-data/` (data.db, dist/, logs/)

### Cloudflare

| 서비스 | 용도 | 도메인 |
|--------|------|--------|
| DNS | 도메인 관리 | withmigrant.or.kr |
| Pages | 정적 사이트 호스팅 | withmigrant.or.kr |
| R2 | 파일 저장소 | uploads.withmigrant.or.kr |
| SSL | Full 모드 | - |

### 환경변수 (Coolify)

| 변수 | 용도 |
|------|------|
| `SECRET_KEY` | Flask 세션 비밀키 |
| `STATIC_DOMAIN` | 정적 사이트 도메인 |
| `API_DOMAIN` | Admin API 도메인 |
| `CLOUDFLARE_API_TOKEN` | Wrangler CLI 인증 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 계정 ID |
| `R2_ACCESS_KEY_ID` | R2 API 접근 키 |
| `R2_SECRET_ACCESS_KEY` | R2 API 시크릿 키 |
| `R2_BUCKET_NAME` | R2 버킷명 (withmigrant-uploads) |
| `R2_PUBLIC_URL` | R2 공개 URL (https://uploads.withmigrant.or.kr) |

---

## 마이그레이션 기록

### 2026-02-06: 사이트 다운타임 대응 + Cloudflare 마이그레이션

#### 1. 사이트 다운타임 원인 분석

- **증상**: withmigrant.or.kr 접속 불가 (타임아웃)
- **원인**: Traefik 프록시의 SSL 설정 문제
  - `/data/coolify/proxy/dynamic/withmigrant.yml`에 불완전한 TLS 인증서 설정이 있었음
  - 수동으로 SSL 인증서를 넣고 Traefik을 재시작했으나, 라우터 설정 없이 인증서만 정의
- **해결**:
  - 수동 SSL 파일 삭제 (`withmigrant.pem`, `withmigrant.key`, `withmigrant.yml`)
  - Cloudflare SSL 모드를 "Full"로 변경
  - Traefik 프록시 재시작

#### 2. Cloudflare Pages 마이그레이션

기존 Nginx 컨테이너(web)를 제거하고 Cloudflare Pages로 정적 사이트 이전.

**변경 파일:**
- `Dockerfile` - Node.js + Wrangler CLI 추가
- `docker-compose.yml` - web 서비스 제거, CF 환경변수 추가
- `run_build.py` - 빌드 후 `deploy_to_cloudflare()` 함수 추가
- `build.py` - `_headers` 파일 생성 (Cloudflare Pages 캐싱 설정)

**Cloudflare Pages 설정:**
- 프로젝트명: `withmigrant`
- 배포 방식: Direct Upload (wrangler CLI)
- 커스텀 도메인: `withmigrant.or.kr`

#### 3. Cloudflare R2 마이그레이션

파일 업로드 저장소를 로컬 `dist/uploads/`에서 Cloudflare R2로 이전.

**변경 파일:**
- `r2_storage.py` - R2 업로드/삭제/URL 헬퍼 (신규)
- `config.py` - R2 설정 추가
- `app.py` - 업로드→R2, 서빙→R2 리다이렉트
- `admin/utils.py` - 파일 저장/삭제→R2
- `build.py` - HTML 내 `/uploads/` 경로를 R2 URL로 자동 변환
- `docker-compose.yml` - R2 환경변수 추가
- `requirements.txt` - boto3 추가
- `migrate_to_r2.py` - 기존 파일 마이그레이션 스크립트 (신규)

**URL 변환 처리:**
- DB에 저장된 HTML 내 `/uploads/파일명` 또는 `/static/uploads/파일명` 경로는:
  - Admin 페이지: Flask `serve_upload()` 라우트가 R2 URL로 302 리다이렉트
  - 정적 사이트: `build.py`의 `save_html()`에서 R2 공개 URL로 일괄 치환
- DB 데이터 수정 없이 모든 기존 경로가 R2로 연결됨

**R2 설정:**
- 버킷: `withmigrant-uploads` (APAC)
- 커스텀 도메인: `uploads.withmigrant.or.kr`
- API 토큰: Object Read & Write 권한

---

## 운영 명령어

```bash
# 컨테이너 확인
docker ps --filter "name=admin" --format "{{.Names}}"

# 수동 빌드 + 배포
docker exec -it <컨테이너이름> python3 run_build.py auto manual

# R2 마이그레이션 (최초 1회)
docker exec -it <컨테이너이름> python3 migrate_to_r2.py

# 빌드 로그 확인
docker exec -it <컨테이너이름> tail -f logs/build.log

# 앱 로그 확인
docker exec -it <컨테이너이름> tail -f logs/app.log
```

## 검증 체크리스트

- [ ] `curl -I https://withmigrant.or.kr` → 200 OK, `server: cloudflare`
- [ ] `curl -I https://uploads.withmigrant.or.kr/<파일명>` → 200 OK
- [ ] Admin에서 이미지 업로드 → R2 대시보드에서 파일 확인
- [ ] Admin에서 콘텐츠 수정 → 자동 빌드 → Pages 배포 확인
- [ ] 정적 사이트에서 이미지 로드 확인 (R2 URL)
