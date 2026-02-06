"""
기존 dist/uploads/ 파일을 Cloudflare R2로 마이그레이션
사용법: python3 migrate_to_r2.py
"""
import os
import mimetypes
from r2_storage import upload_to_r2, get_r2_client
from config import Config


def migrate():
    uploads_dir = os.path.join(Config.BASE_DIR, 'dist', 'uploads')

    if not os.path.exists(uploads_dir):
        print("dist/uploads/ 폴더가 없습니다.")
        return

    files = [f for f in os.listdir(uploads_dir) if os.path.isfile(os.path.join(uploads_dir, f))]

    if not files:
        print("마이그레이션할 파일이 없습니다.")
        return

    print(f"총 {len(files)}개 파일 마이그레이션 시작...")

    # R2에 이미 있는 파일 확인
    r2 = get_r2_client()
    existing = set()
    try:
        paginator = r2.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=Config.R2_BUCKET_NAME):
            for obj in page.get('Contents', []):
                existing.add(obj['Key'])
    except Exception:
        pass

    success = 0
    skipped = 0
    failed = 0

    for filename in files:
        if filename.startswith('.'):
            continue

        if filename in existing:
            skipped += 1
            continue

        filepath = os.path.join(uploads_dir, filename)
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
            upload_to_r2(file_data, filename, content_type)
            success += 1
            print(f"  ✓ {filename} ({len(file_data)} bytes)")
        except Exception as e:
            failed += 1
            print(f"  ✗ {filename}: {e}")

    print(f"\n완료: 성공 {success}, 건너뜀 {skipped}, 실패 {failed}")


if __name__ == '__main__':
    migrate()
