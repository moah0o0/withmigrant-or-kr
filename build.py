#!/usr/bin/env python3
"""
SSG 빌드 스크립트
정적 HTML 파일을 dist/ 폴더에 생성합니다.

사용법:
    python build.py          # 전체 빌드
    python build.py --clean  # dist 폴더 초기화 후 빌드
"""

import os
import sys
import shutil
import argparse
import re
from datetime import datetime
from math import ceil
from types import SimpleNamespace

# Flask 앱 컨텍스트 사용
from flask import Flask, render_template
from config import Config
from models import (
    db, SiteInfo, ActivityPhoto, BusinessArea, SponsorshipInfo,
    VolunteerArea, DonationArea, DonationUsage, HistorySection,
    Notice, ActivityPost, Newsletter, ActivityCategory,
    BusStop, BusRoute, OperatingHours, OfficeInfo
)


def strip_html_tags(text):
    """HTML 태그를 제거하고 텍스트만 반환"""
    if not text:
        return ''
    # HTML 태그 제거
    clean_text = re.sub(r'<[^>]+>', '', text)
    # 연속된 공백을 하나로
    clean_text = re.sub(r'\s+', ' ', clean_text)
    return clean_text.strip()


def create_app():
    """SSG 빌드용 Flask 앱 생성"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 템플릿 필터 등록
    @app.template_filter('fix_upload_urls')
    def fix_upload_urls(content):
        """레거시 /static/uploads/ 경로를 /uploads/로 변환"""
        if not content:
            return content
        return content.replace('/static/uploads/', '/uploads/')

    # Jinja2 환경 설정
    app.jinja_env.globals['STATIC_DOMAIN'] = Config.STATIC_DOMAIN
    app.jinja_env.globals['API_DOMAIN'] = Config.API_DOMAIN
    app.jinja_env.globals['SEO'] = Config.SEO_DEFAULTS
    app.jinja_env.globals['now'] = datetime.now()
    app.jinja_env.globals['build_time'] = datetime.now().isoformat()

    db.init_app(app)
    return app


def clean_dist():
    """dist 폴더 초기화 (uploads 폴더는 보존)"""
    if os.path.exists(Config.DIST_DIR):
        # uploads 폴더를 제외한 모든 파일/폴더 삭제
        for item in os.listdir(Config.DIST_DIR):
            item_path = os.path.join(Config.DIST_DIR, item)
            if item == 'uploads':
                continue  # uploads 폴더 보존
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    else:
        os.makedirs(Config.DIST_DIR)

    # uploads 폴더가 없으면 생성
    uploads_dir = os.path.join(Config.DIST_DIR, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    print(f"✓ dist 폴더 초기화 완료 (uploads 보존): {Config.DIST_DIR}")


def copy_static_files():
    """정적 파일 복사 (css, js, images)"""
    static_src = os.path.join(Config.BASE_DIR, 'static')
    static_dst = os.path.join(Config.DIST_DIR, 'static')

    # 복사할 폴더 목록 (uploads 제외)
    folders_to_copy = ['css', 'js', 'images']

    os.makedirs(static_dst, exist_ok=True)

    for folder in folders_to_copy:
        src_path = os.path.join(static_src, folder)
        dst_path = os.path.join(static_dst, folder)

        if os.path.exists(src_path):
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            print(f"  ✓ static/{folder} 복사 완료")

    print(f"✓ 정적 파일 복사 완료")


def save_html(path, content):
    """HTML 파일 저장"""
    full_path = os.path.join(Config.DIST_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)


def get_site_context():
    """공통 사이트 컨텍스트 반환"""
    site_info = SiteInfo.query.first()
    return {
        'site': site_info.to_dict() if site_info else {},
    }


def normalize_seo(seo):
    """
    SEO 설정 정규화 - og_image를 절대 URL로 변환
    Args:
        seo: SEO 설정 딕셔너리
    Returns:
        정규화된 SEO 딕셔너리
    """
    normalized = seo.copy()

    # og_image를 절대 URL로 변환
    if 'og_image' in normalized:
        og_image = normalized['og_image']
        if og_image:
            # 이미 STATIC_DOMAIN을 포함하고 있는지 확인 (중복 방지)
            if Config.STATIC_DOMAIN in og_image:
                # 이미 절대 URL로 변환됨 (그대로 사용)
                normalized['og_image'] = og_image
            elif og_image.startswith(('http://', 'https://')):
                # 다른 도메인의 절대 URL (그대로 사용)
                normalized['og_image'] = og_image
            else:
                # 상대 경로 (/uploads/... 등) -> 절대 URL로 변환
                normalized['og_image'] = Config.STATIC_DOMAIN + og_image

    return normalized


def build_index(app):
    """메인 페이지 빌드"""
    with app.app_context():
        ctx = get_site_context()

        # 데이터 조회
        hero_photos = ActivityPhoto.query.filter_by(is_active=True)\
            .order_by(ActivityPhoto.display_order).limit(5).all()
        business_areas = BusinessArea.query.filter_by(is_active=True)\
            .order_by(BusinessArea.display_order).all()
        notices = Notice.query.order_by(Notice.is_pinned.desc(), Notice.created_at.desc()).limit(5).all()
        activities = ActivityPost.query.order_by(ActivityPost.created_at.desc()).limit(6).all()
        newsletters = Newsletter.query.order_by(Newsletter.published_at.desc()).limit(4).all()
        sponsorship = SponsorshipInfo.query.first()
        volunteer_areas = VolunteerArea.query.filter_by(is_active=True)\
            .order_by(VolunteerArea.display_order).all()
        donation_areas = DonationArea.query.filter_by(is_active=True)\
            .order_by(DonationArea.display_order).all()

        # SEO 설정
        seo = normalize_seo({**Config.SEO_DEFAULTS, **Config.SEO_PAGES.get('index', {})})

        html = render_template('ssg/index.html',
            **ctx,
            hero_photos=hero_photos,
            business_areas=business_areas,
            notices=notices,
            activities=activities,
            newsletters=newsletters,
            sponsorship=sponsorship,
            volunteer_areas=volunteer_areas,
            donation_areas=donation_areas,
            seo=seo,
            current_page='index'
        )

        save_html('index.html', html)
        print("  ✓ index.html")


def build_intro(app):
    """소개 페이지 빌드"""
    with app.app_context():
        ctx = get_site_context()

        history_sections = HistorySection.query.order_by(HistorySection.display_order).all()
        business_areas = BusinessArea.query.filter_by(is_active=True)\
            .order_by(BusinessArea.display_order).all()
        bus_stops = BusStop.query.filter_by(is_active=True).order_by(BusStop.display_order).all()
        bus_routes = BusRoute.query.filter_by(is_active=True).order_by(BusRoute.route_type, BusRoute.display_order).all()

        routes_by_type = {'일반': [], '좌석': [], '마을': []}
        for route in bus_routes:
            if route.route_type in routes_by_type:
                routes_by_type[route.route_type].append(route)

        operating_hours = OperatingHours.query.filter_by(is_active=True).order_by(OperatingHours.display_order).all()
        office_info = OfficeInfo.get()

        seo = normalize_seo({**Config.SEO_DEFAULTS, **Config.SEO_PAGES.get('intro', {})})

        html = render_template('ssg/intro.html',
            **ctx,
            history_sections=history_sections,
            business_areas=business_areas,
            bus_stops=bus_stops,
            routes_by_type=routes_by_type,
            operating_hours=operating_hours,
            office_info=office_info,
            seo=seo,
            current_page='intro'
        )

        save_html('intro.html', html)
        print("  ✓ intro.html")


def build_notice_list(app):
    """공지사항 목록 빌드"""
    with app.app_context():
        ctx = get_site_context()
        per_page = Config.PAGINATION['notice']

        total = Notice.query.count()
        total_pages = ceil(total / per_page) if total > 0 else 1

        seo = normalize_seo({**Config.SEO_DEFAULTS, **Config.SEO_PAGES.get('notice_list', {})})

        for page in range(1, total_pages + 1):
            notices = Notice.query.order_by(Notice.is_pinned.desc(), Notice.created_at.desc())\
                .offset((page - 1) * per_page).limit(per_page).all()

            # 간단한 페이지네이션 객체 생성 (SimpleNamespace 사용)
            pagination = SimpleNamespace(
                items=notices,
                page=page,
                pages=total_pages,
                total=total,
                has_prev=page > 1,
                has_next=page < total_pages,
                prev_num=page - 1 if page > 1 else None,
                next_num=page + 1 if page < total_pages else None,
            )

            html = render_template('ssg/notice.html',
                **ctx,
                pagination=pagination,
                seo=seo,
                current_page='notice_list'
            )

            if page == 1:
                save_html('notice/index.html', html)
                print("  ✓ notice/index.html")
            else:
                save_html(f'notice/page/{page}.html', html)
                print(f"  ✓ notice/page/{page}.html")


def build_notice_detail(app):
    """공지사항 상세 페이지 빌드"""
    with app.app_context():
        ctx = get_site_context()

        notices = Notice.query.order_by(Notice.created_at.desc()).all()

        for i, notice in enumerate(notices):
            prev_notice = notices[i + 1] if i + 1 < len(notices) else None
            next_notice = notices[i - 1] if i > 0 else None

            seo = normalize_seo({
                **Config.SEO_DEFAULTS,
                'title': notice.title,
                'description': strip_html_tags(notice.content)[:160] if notice.content else '',
            })

            html = render_template('ssg/notice_detail.html',
                **ctx,
                notice=notice,
                prev_notice=prev_notice,
                next_notice=next_notice,
                seo=seo,
                current_page='notice_detail'
            )

            save_html(f'notice/{notice.id}.html', html)

        print(f"  ✓ notice/*.html ({len(notices)}개)")


def build_activity_list(app):
    """활동후기 목록 빌드"""
    with app.app_context():
        ctx = get_site_context()
        per_page = Config.PAGINATION['activity']

        categories = ActivityCategory.query.filter_by(is_active=True)\
            .order_by(ActivityCategory.display_order).all()

        seo = normalize_seo({**Config.SEO_DEFAULTS, **Config.SEO_PAGES.get('activity_list', {})})

        # 전체 목록
        total = ActivityPost.query.count()
        total_pages = ceil(total / per_page) if total > 0 else 1

        for page in range(1, total_pages + 1):
            activities = ActivityPost.query.order_by(ActivityPost.created_at.desc())\
                .offset((page - 1) * per_page).limit(per_page).all()

            pagination = SimpleNamespace(
                items=activities,
                page=page,
                pages=total_pages,
                total=total,
                has_prev=page > 1,
                has_next=page < total_pages,
                prev_num=page - 1 if page > 1 else None,
                next_num=page + 1 if page < total_pages else None,
            )

            html = render_template('ssg/activity.html',
                **ctx,
                pagination=pagination,
                categories=categories,
                current_category=None,
                seo=seo,
                current_page='activity_list'
            )

            if page == 1:
                save_html('activity/index.html', html)
                print("  ✓ activity/index.html")
            else:
                save_html(f'activity/page/{page}.html', html)
                print(f"  ✓ activity/page/{page}.html")

        # 카테고리별 목록
        for cat in categories:
            cat_total = ActivityPost.query.filter_by(category=cat.name).count()
            cat_pages = ceil(cat_total / per_page) if cat_total > 0 else 1

            for page in range(1, cat_pages + 1):
                activities = ActivityPost.query.filter_by(category=cat.name)\
                    .order_by(ActivityPost.created_at.desc())\
                    .offset((page - 1) * per_page).limit(per_page).all()

                pagination = SimpleNamespace(
                    items=activities,
                    page=page,
                    pages=cat_pages,
                    total=cat_total,
                    has_prev=page > 1,
                    has_next=page < cat_pages,
                    prev_num=page - 1 if page > 1 else None,
                    next_num=page + 1 if page < cat_pages else None,
                )

                html = render_template('ssg/activity.html',
                    **ctx,
                    pagination=pagination,
                    categories=categories,
                    current_category=cat.name,
                    seo=seo,
                    current_page='activity_list'
                )

                cat_slug = cat.name.replace(' ', '-')
                if page == 1:
                    save_html(f'activity/category/{cat_slug}/index.html', html)
                else:
                    save_html(f'activity/category/{cat_slug}/page/{page}.html', html)

            print(f"  ✓ activity/category/{cat.name}/ ({cat_pages}페이지)")


def build_activity_detail(app):
    """활동후기 상세 페이지 빌드"""
    with app.app_context():
        ctx = get_site_context()

        activities = ActivityPost.query.order_by(ActivityPost.created_at.desc()).all()

        for post in activities:
            category_obj = None
            if post.category:
                category_obj = ActivityCategory.query.filter_by(name=post.category).first()

            related_posts = []
            if post.category:
                related_posts = ActivityPost.query.filter(
                    ActivityPost.category == post.category,
                    ActivityPost.id != post.id
                ).order_by(ActivityPost.created_at.desc()).limit(3).all()

            seo = normalize_seo({
                **Config.SEO_DEFAULTS,
                'title': post.title,
                'description': strip_html_tags(post.content)[:160] if post.content else '',
                'og_image': post.image_url if post.image_url else Config.SEO_DEFAULTS['og_image'],
            })

            html = render_template('ssg/activity_detail.html',
                **ctx,
                post=post,
                related_posts=related_posts,
                category_obj=category_obj,
                seo=seo,
                current_page='activity_detail'
            )

            save_html(f'activity/{post.id}.html', html)

        print(f"  ✓ activity/*.html ({len(activities)}개)")


def build_newsletter_list(app):
    """소식지 목록 빌드"""
    with app.app_context():
        ctx = get_site_context()
        per_page = Config.PAGINATION['newsletter']

        total = Newsletter.query.count()
        total_pages = ceil(total / per_page) if total > 0 else 1

        seo = normalize_seo({**Config.SEO_DEFAULTS, **Config.SEO_PAGES.get('newsletter_list', {})})

        for page in range(1, total_pages + 1):
            newsletters = Newsletter.query.order_by(Newsletter.published_at.desc())\
                .offset((page - 1) * per_page).limit(per_page).all()

            pagination = SimpleNamespace(
                items=newsletters,
                page=page,
                pages=total_pages,
                total=total,
                has_prev=page > 1,
                has_next=page < total_pages,
                prev_num=page - 1 if page > 1 else None,
                next_num=page + 1 if page < total_pages else None,
            )

            html = render_template('ssg/newsletter.html',
                **ctx,
                pagination=pagination,
                seo=seo,
                current_page='newsletter_list'
            )

            if page == 1:
                save_html('newsletter/index.html', html)
                print("  ✓ newsletter/index.html")
            else:
                save_html(f'newsletter/page/{page}.html', html)
                print(f"  ✓ newsletter/page/{page}.html")


def build_newsletter_detail(app):
    """소식지 상세 페이지 빌드"""
    with app.app_context():
        ctx = get_site_context()

        newsletters = Newsletter.query.order_by(Newsletter.published_at.desc()).all()

        for i, newsletter in enumerate(newsletters):
            prev_newsletter = newsletters[i + 1] if i + 1 < len(newsletters) else None
            next_newsletter = newsletters[i - 1] if i > 0 else None

            seo = normalize_seo({
                **Config.SEO_DEFAULTS,
                'title': newsletter.title,
                'description': newsletter.description or '',
            })

            html = render_template('ssg/newsletter_detail.html',
                **ctx,
                newsletter=newsletter,
                prev_newsletter=prev_newsletter,
                next_newsletter=next_newsletter,
                seo=seo,
                current_page='newsletter_detail'
            )

            save_html(f'newsletter/{newsletter.id}.html', html)

        print(f"  ✓ newsletter/*.html ({len(newsletters)}개)")


def build_donation(app):
    """후원 페이지 빌드"""
    with app.app_context():
        ctx = get_site_context()

        sponsorship = SponsorshipInfo.query.first()
        volunteer_areas = VolunteerArea.query.filter_by(is_active=True)\
            .order_by(VolunteerArea.display_order).all()
        donation_areas = DonationArea.query.filter_by(is_active=True)\
            .order_by(DonationArea.display_order).all()
        donation_usages = DonationUsage.query.filter_by(is_active=True)\
            .order_by(DonationUsage.display_order).all()

        seo = normalize_seo({**Config.SEO_DEFAULTS, **Config.SEO_PAGES.get('donation', {})})

        html = render_template('ssg/donation.html',
            **ctx,
            sponsorship=sponsorship,
            volunteer_areas=volunteer_areas,
            donation_areas=donation_areas,
            donation_usages=donation_usages,
            seo=seo,
            current_page='donation'
        )

        save_html('donation.html', html)
        print("  ✓ donation.html")


def build_donation_complete(app):
    """후원 완료 페이지 빌드"""
    with app.app_context():
        ctx = get_site_context()

        seo = normalize_seo({
            **Config.SEO_DEFAULTS,
            'title': '후원 신청 완료',
            'description': '양산외국인노동자의집 후원 신청이 완료되었습니다. 소중한 마음에 진심으로 감사드립니다.',
        })

        html = render_template('donation_complete.html',
            **ctx,
            seo=seo
        )

        save_html('donation-complete.html', html)
        print("  ✓ donation-complete.html")


def main():
    parser = argparse.ArgumentParser(description='SSG 빌드 스크립트')
    parser.add_argument('--clean', action='store_true', help='dist 폴더 초기화 후 빌드')
    args = parser.parse_args()

    print("=" * 50)
    print("SSG 빌드 시작")
    print("=" * 50)

    start_time = datetime.now()

    # dist 폴더 초기화
    if args.clean or not os.path.exists(Config.DIST_DIR):
        clean_dist()

    # Flask 앱 생성
    app = create_app()

    # 정적 파일 복사
    print("\n[1/3] 정적 파일 복사")
    copy_static_files()

    # 페이지 빌드
    print("\n[2/3] 페이지 빌드")
    build_index(app)
    build_intro(app)
    build_notice_list(app)
    build_notice_detail(app)
    build_activity_list(app)
    build_activity_detail(app)
    build_newsletter_list(app)
    build_newsletter_detail(app)
    build_donation(app)
    build_donation_complete(app)

    # 완료
    elapsed = datetime.now() - start_time
    print("\n" + "=" * 50)
    print(f"✓ 빌드 완료! (소요 시간: {elapsed.total_seconds():.2f}초)")
    print(f"  출력 폴더: {Config.DIST_DIR}")
    print("=" * 50)


if __name__ == '__main__':
    main()
