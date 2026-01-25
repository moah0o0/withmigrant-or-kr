# GitHub Actions 자동 배포 설정 가이드

GitHub에 push하면 자동으로 서버에 배포되도록 설정합니다.

## 1. 서버에서 SSH 키 생성

서버에 SSH로 접속해서 배포용 SSH 키를 생성합니다:

```bash
# 서버에 접속
ssh root@158.247.227.233

# SSH 키 생성 (비밀번호 없이 엔터 3번)
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions

# 공개키를 authorized_keys에 추가
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# 개인키 내용 출력 (복사해두기)
cat ~/.ssh/github_actions
```

**중요**: `cat ~/.ssh/github_actions` 명령으로 출력된 개인키 전체를 복사해둡니다.
- `-----BEGIN OPENSSH PRIVATE KEY-----`로 시작
- `-----END OPENSSH PRIVATE KEY-----`로 끝남
- 중간의 모든 내용 포함

## 2. GitHub Secrets 설정

GitHub 저장소에 SSH 정보를 등록합니다:

1. GitHub 저장소로 이동: https://github.com/moah0o0/withmigrant-or-kr
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 버튼 클릭

다음 3개의 Secret을 추가:

### Secret 1: SSH_HOST
- **Name**: `SSH_HOST`
- **Value**: `158.247.227.233`

### Secret 2: SSH_USER
- **Name**: `SSH_USER`
- **Value**: `root`

### Secret 3: SSH_PRIVATE_KEY
- **Name**: `SSH_PRIVATE_KEY`
- **Value**: 위에서 복사한 개인키 전체 내용
  ```
  -----BEGIN OPENSSH PRIVATE KEY-----
  b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
  ... (중간 내용 전체) ...
  -----END OPENSSH PRIVATE KEY-----
  ```

## 3. GitHub Actions 워크플로우 확인

`.github/workflows/deploy.yml` 파일이 생성되어 있습니다.

이 파일은 다음 작업을 자동으로 수행합니다:
1. ✅ Git pull (서버 변경사항 무시, GitHub 코드 우선)
2. ✅ Python 패키지 업데이트
3. ✅ 정적 사이트 빌드
4. ✅ 파일 권한 설정
5. ✅ 서비스 재시작

## 4. 테스트

설정이 완료되면 테스트해봅니다:

```bash
# 로컬에서
git add .
git commit -m "Test: GitHub Actions deployment"
git push origin main
```

GitHub Actions 실행 확인:
1. GitHub 저장소 → **Actions** 탭
2. 방금 push한 커밋의 workflow 확인
3. 초록색 체크 표시가 나오면 성공!

## 5. 배포 로그 확인

GitHub Actions에서 실패 시:
1. GitHub → Actions → 실패한 workflow 클릭
2. "Deploy to server" 단계 클릭
3. 에러 메시지 확인

서버에서 직접 확인:
```bash
ssh root@158.247.227.233
systemctl status migrant-yangsan
journalctl -u migrant-yangsan -n 50
```

## 6. 보안 권장사항

### 배포 전용 계정 만들기 (선택사항)

더 안전하게 하려면 root 대신 배포 전용 계정을 만드는 것이 좋습니다:

```bash
# 서버에서
useradd -m -s /bin/bash deploy
usermod -aG sudo deploy

# deploy 사용자로 전환
su - deploy

# deploy 사용자의 SSH 키 생성
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# 프로젝트 소유권 변경
chown -R deploy:deploy /var/www/migrant-yangsan

# sudoers 설정 (비밀번호 없이 systemctl 실행)
visudo
# 다음 줄 추가:
# deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart migrant-yangsan, /bin/systemctl status migrant-yangsan
```

그 후 GitHub Secrets의 `SSH_USER`를 `deploy`로 변경합니다.

## 트러블슈팅

### 권한 에러
```bash
# 서버에서
chown -R www-data:www-data /var/www/migrant-yangsan/dist
chmod -R 755 /var/www/migrant-yangsan/dist
chmod -R 775 /var/www/migrant-yangsan/dist/uploads
```

### Git pull 충돌
워크플로우는 `git reset --hard origin/main`을 사용하므로 서버의 로컬 변경사항은 자동으로 삭제됩니다. 이것이 의도된 동작입니다.

### 서비스 재시작 실패
```bash
# 서버에서 수동으로
systemctl restart migrant-yangsan
systemctl status migrant-yangsan
journalctl -u migrant-yangsan -n 100
```

## 이제 사용 방법

모든 설정이 완료되면:

```bash
# 로컬에서 코드 수정
git add .
git commit -m "수정 내용"
git push origin main

# GitHub Actions가 자동으로:
# 1. 서버에 SSH 접속
# 2. 최신 코드 pull
# 3. 빌드 실행
# 4. 서비스 재시작
```

**완전 자동화!** 🎉
