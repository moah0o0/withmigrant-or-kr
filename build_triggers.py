"""
DB 변동 감지 및 자동 빌드 트리거

SQLAlchemy 이벤트 리스너를 사용하여 SSG에 영향을 주는 모델이
변경될 때 자동으로 빌드를 트리거합니다.
"""
from sqlalchemy import event
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

# 빌드를 트리거할 모델 목록
BUILD_TRIGGER_MODELS = [
    'Notice',
    'ActivityPost',
    'Newsletter',
    'SiteInfo',
    'BusinessArea',
    'VolunteerArea',
    'DonationArea',
    'DonationUsage',
    'HistorySection',
    'HistoryItem',
    'ActivityPhoto',
    'ActivityCategory',
    'BusStop',
    'BusRoute',
    'OperatingHours',
    'OfficeInfo',
]


def should_trigger_build(mapper, connection, target):
    """
    빌드를 트리거해야 하는지 확인

    Args:
        mapper: SQLAlchemy mapper
        connection: DB connection
        target: 변경된 모델 인스턴스

    Returns:
        bool: 빌드 트리거 여부
    """
    model_name = target.__class__.__name__
    return model_name in BUILD_TRIGGER_MODELS


def trigger_build_after_commit(session, triggered_by='auto'):
    """
    트랜잭션 커밋 후 빌드 트리거

    Args:
        session: SQLAlchemy session
        triggered_by: 빌드를 트리거한 작업
    """
    from background_builder import trigger_build

    # 빌드 트리거 (비동기)
    # skip_db_check=True: 커밋된 세션에서 DB 조회 방지
    success = trigger_build(triggered_by=triggered_by, skip_db_check=True)

    if success:
        logger.info(f"자동 빌드 트리거됨: {triggered_by}")
    else:
        logger.warning(f"빌드 트리거 실패 (이미 빌드 중일 수 있음): {triggered_by}")


class BuildTriggerManager:
    """빌드 트리거 관리"""

    def __init__(self):
        self._pending_build = False
        self._triggered_by = None

    def mark_for_build(self, triggered_by):
        """빌드 예약"""
        self._pending_build = True
        if not self._triggered_by:
            self._triggered_by = triggered_by

    def execute_if_pending(self, session):
        """대기 중인 빌드 실행"""
        if self._pending_build:
            trigger_build_after_commit(session, self._triggered_by or 'auto')
            self._pending_build = False
            self._triggered_by = None


# 전역 빌드 트리거 매니저
build_manager = BuildTriggerManager()


def on_model_change(mapper, connection, target):
    """모델 변경 감지 (after_insert, after_update, after_delete)"""
    if should_trigger_build(mapper, connection, target):
        model_name = target.__class__.__name__
        # ID가 있으면 (update/delete), 없으면 (insert)
        action = 'updated' if hasattr(target, 'id') and target.id else 'created'
        triggered_by = f'{model_name}_{action}'

        build_manager.mark_for_build(triggered_by)
        logger.debug(f"빌드 예약: {triggered_by}")


def on_after_commit(session):
    """커밋 후 빌드 실행"""
    build_manager.execute_if_pending(session)


def setup_build_triggers(app):
    """
    빌드 트리거 이벤트 리스너 설정

    Args:
        app: Flask application instance

    Usage:
        from build_triggers import setup_build_triggers
        setup_build_triggers(app)
    """
    # 모델 클래스 import
    from models import (
        Notice, ActivityPost, Newsletter, SiteInfo,
        BusinessArea, VolunteerArea, DonationArea, DonationUsage,
        HistorySection, HistoryItem, ActivityPhoto, ActivityCategory,
        BusStop, BusRoute, OperatingHours, OfficeInfo
    )

    # 모델 클래스 매핑
    model_classes = {
        'Notice': Notice,
        'ActivityPost': ActivityPost,
        'Newsletter': Newsletter,
        'SiteInfo': SiteInfo,
        'BusinessArea': BusinessArea,
        'VolunteerArea': VolunteerArea,
        'DonationArea': DonationArea,
        'DonationUsage': DonationUsage,
        'HistorySection': HistorySection,
        'HistoryItem': HistoryItem,
        'ActivityPhoto': ActivityPhoto,
        'ActivityCategory': ActivityCategory,
        'BusStop': BusStop,
        'BusRoute': BusRoute,
        'OperatingHours': OperatingHours,
        'OfficeInfo': OfficeInfo,
    }

    # 모든 모델에 대해 이벤트 리스너 등록
    for model_name, model_class in model_classes.items():
        # Insert 이벤트
        event.listen(model_class, 'after_insert', on_model_change)
        # Update 이벤트
        event.listen(model_class, 'after_update', on_model_change)
        # Delete 이벤트
        event.listen(model_class, 'after_delete', on_model_change)

        logger.info(f"빌드 트리거 이벤트 리스너 등록: {model_name}")

    # 커밋 후 이벤트
    event.listen(Session, 'after_commit', on_after_commit)

    app.logger.info("빌드 트리거 시스템 활성화됨")


def disable_build_triggers():
    """빌드 트리거 비활성화 (테스트용)"""
    global build_manager
    build_manager._pending_build = False
    logger.info("빌드 트리거 비활성화됨")
