"""
독립 프로세스로 SSG 빌드 실행
"""
import sys
import subprocess
import logging
from datetime import datetime
from app import app
from models import db, BuildStatus

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def deploy_to_cloudflare():
    """빌드된 dist/ 폴더를 Cloudflare Pages에 배포"""
    try:
        result = subprocess.run(
            ['wrangler', 'pages', 'deploy', 'dist/',
             '--project-name', 'withmigrant',
             '--branch', 'main'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            logger.info("Cloudflare Pages 배포 성공")
            logger.info(f"배포 출력:\n{result.stdout}")
            return True
        else:
            logger.error(f"Cloudflare Pages 배포 실패:\n{result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Cloudflare Pages 배포 타임아웃 (5분 초과)")
        return False
    except FileNotFoundError:
        logger.error("wrangler CLI를 찾을 수 없습니다. Node.js/wrangler가 설치되어 있는지 확인하세요.")
        return False
    except Exception as e:
        logger.error(f"Cloudflare Pages 배포 오류: {str(e)}")
        return False


def run_build(build_id, triggered_by='auto'):
    """
    SSG 빌드 실행

    Args:
        build_id: BuildStatus 레코드 ID 또는 'auto'
        triggered_by: 빌드를 트리거한 작업
    """
    with app.app_context():
        try:
            # build_id가 'auto'인 경우 새로운 빌드 상태 생성
            if build_id == 'auto':
                # 현재 빌드 중인지 확인
                current = BuildStatus.get_current()
                if current.status == 'building':
                    logger.warning("빌드가 이미 진행 중입니다. 종료합니다.")
                    return

                # 새로운 빌드 상태 생성
                build_status = BuildStatus.start_build(triggered_by=triggered_by)
                logger.info(f"새 빌드 상태 생성 (ID: {build_status.id}, triggered_by: {triggered_by})")
            else:
                build_status = BuildStatus.query.get(int(build_id))
                if not build_status:
                    logger.error(f"BuildStatus ID {build_id}를 찾을 수 없습니다.")
                    return

            logger.info(f"빌드 시작 (ID: {build_status.id})")

            # build.py 실행
            result = subprocess.run(
                ['python3', 'build.py'],
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode == 0:
                logger.info("빌드 성공")
                logger.info(f"빌드 출력:\n{result.stdout}")
                build_status.complete(success=True)

                # Cloudflare Pages 배포
                deploy_success = deploy_to_cloudflare()
                if not deploy_success:
                    logger.warning("빌드 성공했으나 Cloudflare Pages 배포 실패")
            else:
                logger.error("빌드 실패")
                logger.error(f"에러 출력:\n{result.stderr}")
                build_status.complete(success=False, error_message=result.stderr)

        except subprocess.TimeoutExpired:
            error_msg = "빌드 타임아웃 (5분 초과)"
            logger.error(error_msg)
            build_status.complete(success=False, error_message=error_msg)

        except Exception as e:
            error_msg = f"빌드 중 오류 발생: {str(e)}"
            logger.error(error_msg)
            build_status.complete(success=False, error_message=error_msg)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 run_build.py <build_id> [triggered_by]")
        sys.exit(1)

    build_id = sys.argv[1]  # 'auto' 또는 숫자 ID
    triggered_by = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    run_build(build_id, triggered_by)
