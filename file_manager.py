#!/usr/bin/env python3
"""
파일 관리 통합 스크립트
- DB 동기화: 누락된 파일을 files 테이블에 등록
- 고아 파일 확인: 어디서도 사용되지 않는 파일 확인
- 고아 파일 제거: 어디서도 사용되지 않는 파일 삭제
"""

import os
import sys
import sqlite3
import mimetypes
from datetime import datetime
from pathlib import Path

# 설정
DB_PATH = 'data.db'
UPLOADS_DIR = 'dist/uploads'


def get_file_info(filepath):
    """파일 정보 추출"""
    filename = os.path.basename(filepath)
    size = os.path.getsize(filepath)
    mimetype, _ = mimetypes.guess_type(filepath)

    return {
        'filename': filename,
        'original_filename': filename,
        'mimetype': mimetype or 'application/octet-stream',
        'size': size,
        'created_at': datetime.utcnow().isoformat()
    }


def check_file_usage(cursor, file_id, filename):
    """파일이 사용되는지 확인"""

    # notice_attachments 확인
    cursor.execute("SELECT COUNT(*) FROM notice_attachments WHERE file_id = ?", (file_id,))
    if cursor.fetchone()[0] > 0:
        return True

    # activity_attachments 확인
    cursor.execute("SELECT COUNT(*) FROM activity_attachments WHERE file_id = ?", (file_id,))
    if cursor.fetchone()[0] > 0:
        return True

    # activity_photos 확인
    cursor.execute("SELECT COUNT(*) FROM activity_photos WHERE file_id = ?", (file_id,))
    if cursor.fetchone()[0] > 0:
        return True

    # activity_posts 썸네일 확인
    cursor.execute("SELECT COUNT(*) FROM activity_posts WHERE thumbnail_file_id = ?", (file_id,))
    if cursor.fetchone()[0] > 0:
        return True

    # business_areas 사진 확인
    cursor.execute("SELECT COUNT(*) FROM business_areas WHERE photo_file_id = ?", (file_id,))
    if cursor.fetchone()[0] > 0:
        return True

    # newsletters PDF 확인
    cursor.execute("SELECT COUNT(*) FROM newsletters WHERE pdf_file_id = ?", (file_id,))
    if cursor.fetchone()[0] > 0:
        return True

    # 콘텐츠 내 이미지 참조 확인 (notices)
    cursor.execute("SELECT COUNT(*) FROM notices WHERE content LIKE ?", (f'%/uploads/{filename}%',))
    if cursor.fetchone()[0] > 0:
        return True

    # 콘텐츠 내 이미지 참조 확인 (activity_posts)
    cursor.execute("SELECT COUNT(*) FROM activity_posts WHERE content LIKE ?", (f'%/uploads/{filename}%',))
    if cursor.fetchone()[0] > 0:
        return True

    return False


def sync_missing_files():
    """누락된 파일을 DB에 등록"""
    print("\n" + "=" * 80)
    print("1. 누락된 파일 DB 동기화")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # DB에 이미 등록된 파일명 목록
    cursor.execute("SELECT filename FROM files")
    db_files = set(row[0] for row in cursor.fetchall())

    print(f"DB에 등록된 파일: {len(db_files)}개")

    # dist/uploads의 모든 파일
    upload_files = []
    for filepath in Path(UPLOADS_DIR).rglob('*'):
        if filepath.is_file() and filepath.name != '.DS_Store':
            upload_files.append(filepath)

    print(f"dist/uploads의 파일: {len(upload_files)}개")

    # 누락된 파일 찾기
    missing_files = []
    for filepath in upload_files:
        filename = filepath.name
        if filename not in db_files:
            missing_files.append(filepath)

    print(f"DB에 누락된 파일: {len(missing_files)}개")

    if not missing_files:
        print("✅ 누락된 파일이 없습니다.")
        conn.close()
        return

    # 누락된 파일을 DB에 등록
    print("\n파일 등록 중...")
    registered = 0
    skipped = 0

    for filepath in missing_files:
        try:
            file_info = get_file_info(filepath)

            cursor.execute("""
                INSERT INTO files (filename, original_filename, mimetype, size, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                file_info['filename'],
                file_info['original_filename'],
                file_info['mimetype'],
                file_info['size'],
                file_info['created_at']
            ))

            registered += 1

            if registered % 50 == 0:
                print(f"  {registered}개 등록됨...")

        except Exception as e:
            print(f"  오류 - {filepath.name}: {e}")
            skipped += 1

    # 커밋
    conn.commit()

    print(f"\n완료!")
    print(f"  등록됨: {registered}개")
    print(f"  건너뜀: {skipped}개")
    print(f"  총 파일 수: {len(db_files) + registered}개")

    conn.close()


def check_orphan_files():
    """고아 파일 확인"""
    print("\n" + "=" * 80)
    print("2. 고아 파일 확인")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 모든 파일 가져오기
    cursor.execute("SELECT id, filename, original_filename, size FROM files ORDER BY id")
    all_files = cursor.fetchall()

    print(f"총 파일 수: {len(all_files)}개\n")
    print("고아 파일 (어디서도 사용되지 않는 파일) 확인 중...\n")

    orphan_files = []
    total_orphan_size = 0

    for file_id, filename, original_filename, size in all_files:
        is_used = check_file_usage(cursor, file_id, filename)

        if not is_used:
            orphan_files.append({
                'id': file_id,
                'filename': filename,
                'original_filename': original_filename,
                'size': size if size else 0
            })
            total_orphan_size += size if size else 0

    if orphan_files:
        print(f"발견된 고아 파일: {len(orphan_files)}개")
        print(f"총 용량: {total_orphan_size / (1024*1024):.2f} MB\n")
        print("-" * 80)

        for i, file_info in enumerate(orphan_files[:20], 1):
            size_mb = file_info['size'] / (1024*1024) if file_info['size'] else 0
            print(f"{i:2d}. ID: {file_info['id']:3d} | {file_info['filename'][:40]:<40} | {size_mb:.2f} MB")
            if file_info['original_filename'] != file_info['filename']:
                print(f"     원본: {file_info['original_filename']}")

        if len(orphan_files) > 20:
            print(f"\n... 외 {len(orphan_files) - 20}개 더 있음")
    else:
        print("✅ 고아 파일 없음! 모든 파일이 사용 중입니다.")

    print("\n" + "-" * 80)
    print("\n📊 요약:")
    print(f"  - 전체 파일: {len(all_files)}개")
    print(f"  - 사용 중인 파일: {len(all_files) - len(orphan_files)}개")
    print(f"  - 고아 파일: {len(orphan_files)}개")

    if orphan_files:
        print(f"\n💡 고아 파일들을 삭제하면 {total_orphan_size / (1024*1024):.2f} MB를 절약할 수 있습니다.")

    conn.close()
    return len(orphan_files)


def remove_orphan_files():
    """고아 파일 제거"""
    print("\n" + "=" * 80)
    print("3. 고아 파일 제거")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 모든 파일 가져오기
    cursor.execute("SELECT id, filename, original_filename, size FROM files ORDER BY id")
    all_files = cursor.fetchall()

    print(f"총 파일 수: {len(all_files)}개\n")
    print("고아 파일 찾는 중...\n")

    orphan_files = []
    total_orphan_size = 0

    for file_id, filename, original_filename, size in all_files:
        is_used = check_file_usage(cursor, file_id, filename)

        if not is_used:
            orphan_files.append({
                'id': file_id,
                'filename': filename,
                'original_filename': original_filename,
                'size': size if size else 0
            })
            total_orphan_size += size if size else 0

    if not orphan_files:
        print("✅ 고아 파일 없음! 모든 파일이 사용 중입니다.")
        conn.close()
        return

    print(f"발견된 고아 파일: {len(orphan_files)}개")
    print(f"총 용량: {total_orphan_size / (1024*1024):.2f} MB\n")

    # 확인
    response = input("⚠️  정말로 삭제하시겠습니까? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ 취소되었습니다.")
        conn.close()
        return

    print("\n" + "-" * 80)

    # 고아 파일 삭제
    deleted_count = 0
    deleted_size = 0
    failed_count = 0

    for file_info in orphan_files:
        file_id = file_info['id']
        filename = file_info['filename']
        size = file_info['size']

        try:
            # DB에서 삭제
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))

            # 실제 파일 삭제
            filepath = Path(UPLOADS_DIR) / filename
            if filepath.exists():
                filepath.unlink()
                print(f"✓ 삭제: {filename} ({size / 1024:.1f} KB)")
            else:
                print(f"⚠ DB에서만 삭제 (파일 없음): {filename}")

            deleted_count += 1
            deleted_size += size

        except Exception as e:
            print(f"✗ 실패: {filename} - {e}")
            failed_count += 1

    # 커밋
    conn.commit()

    print("\n" + "=" * 80)
    print("\n📊 완료:")
    print(f"  - 삭제된 파일: {deleted_count}개")
    print(f"  - 절약된 공간: {deleted_size / (1024*1024):.2f} MB")
    print(f"  - 실패한 파일: {failed_count}개")
    print(f"  - 남은 파일: {len(all_files) - deleted_count}개")

    conn.close()


def show_menu():
    """메뉴 표시"""
    print("\n" + "=" * 80)
    print("파일 관리 도구")
    print("=" * 80)
    print("1. DB 동기화 (누락된 파일 등록)")
    print("2. 고아 파일 확인")
    print("3. 고아 파일 제거")
    print("4. 전체 실행 (1 → 2)")
    print("0. 종료")
    print("=" * 80)


def main():
    """메인 함수"""
    # 경로 확인
    if not os.path.exists(DB_PATH):
        print(f"❌ 오류: {DB_PATH} 파일을 찾을 수 없습니다.")
        print(f"   현재 디렉토리: {os.getcwd()}")
        sys.exit(1)

    if not os.path.exists(UPLOADS_DIR):
        print(f"❌ 오류: {UPLOADS_DIR} 디렉토리를 찾을 수 없습니다.")
        sys.exit(1)

    # 명령행 인수가 있으면 자동 실행
    if len(sys.argv) > 1:
        option = sys.argv[1]

        if option == '1' or option == 'sync':
            sync_missing_files()
        elif option == '2' or option == 'check':
            check_orphan_files()
        elif option == '3' or option == 'remove':
            remove_orphan_files()
        elif option == '4' or option == 'all':
            sync_missing_files()
            check_orphan_files()
        else:
            print(f"❌ 알 수 없는 옵션: {option}")
            print("\n사용법:")
            print("  python3 file_manager.py [옵션]")
            print("\n옵션:")
            print("  1 또는 sync   - DB 동기화")
            print("  2 또는 check  - 고아 파일 확인")
            print("  3 또는 remove - 고아 파일 제거")
            print("  4 또는 all    - 전체 실행 (1 → 2)")
        return

    # 대화형 모드
    while True:
        show_menu()
        choice = input("\n선택하세요: ").strip()

        if choice == '1':
            sync_missing_files()
        elif choice == '2':
            check_orphan_files()
        elif choice == '3':
            remove_orphan_files()
        elif choice == '4':
            sync_missing_files()
            orphan_count = check_orphan_files()
            if orphan_count > 0:
                print("\n고아 파일을 제거하려면 옵션 3을 선택하세요.")
        elif choice == '0':
            print("\n종료합니다.")
            break
        else:
            print("\n❌ 잘못된 선택입니다.")

        input("\nEnter를 눌러 계속...")


if __name__ == '__main__':
    main()
