"""
백그라운드 SSG 빌드 실행
"""
import subprocess
import logging
from datetime import datetime
from models import db, BuildStatus

logger = logging.getLogger(__name__)


def trigger_build(triggered_by='manual', skip_db_check=False):
    """
    비동기 빌드 트리거

    Args:
        triggered_by: 빌드를 트리거한 작업 (예: 'notice_created', 'activity_updated')
        skip_db_check: DB 확인 건너뛰기 (after_commit에서 호출시 True)
    """
    try:
        if not skip_db_check:
            # 현재 빌드 중인지 확인
            current = BuildStatus.get_current()
            if current.status == 'building':
                logger.warning("빌드가 이미 진행 중입니다.")
                return False

            # 빌드 상태 시작
            build_status = BuildStatus.start_build(triggered_by=triggered_by)
            build_id = build_status.id
            logger.info(f"SSG 빌드 시작 (ID: {build_id}, triggered_by: {triggered_by})")
        else:
            # DB 확인 건너뛰기 - run_build.py에서 처리
            build_id = 'auto'
            logger.info(f"SSG 빌드 트리거 (triggered_by: {triggered_by})")

        # 백그라운드에서 빌드 실행
        # nohup을 사용하여 프로세스가 독립적으로 실행되도록 함
        subprocess.Popen(
            ['python3', 'run_build.py', str(build_id), triggered_by],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        logger.info(f"빌드 프로세스가 백그라운드에서 시작되었습니다.")
        return True

    except Exception as e:
        logger.error(f"빌드 트리거 실패: {str(e)}")
        return False
