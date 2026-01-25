"""
관리자 인증 관련 유틸리티
"""
from functools import wraps
from flask import session, redirect, url_for, flash, g
from models import AdminUser


def get_current_admin():
    """현재 로그인한 관리자 정보 반환"""
    if 'admin_id' not in session:
        return None
    if not hasattr(g, 'current_admin'):
        g.current_admin = AdminUser.query.get(session['admin_id'])
    return g.current_admin


def login_required(f):
    """로그인 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('admin.login'))

        admin = get_current_admin()
        if not admin or not admin.is_active:
            session.clear()
            flash('계정이 비활성화되었습니다.', 'error')
            return redirect(url_for('admin.login'))

        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """슈퍼관리자 권한 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('admin.login'))

        admin = get_current_admin()
        if not admin or not admin.is_active:
            session.clear()
            flash('계정이 비활성화되었습니다.', 'error')
            return redirect(url_for('admin.login'))

        if not admin.is_super_admin:
            flash('권한이 없습니다.', 'error')
            return redirect(url_for('admin.dashboard'))

        return f(*args, **kwargs)
    return decorated_function
