"""
Direct Supabase Storage uploader — bypasses django-storages S3 completely.
Uses the Supabase REST API with the service role key.
"""
import os
import uuid
import mimetypes
import requests


SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://jixuwhmmzdxdrswaeplc.supabase.co')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
BUCKET_NAME = 'campusmart-media'


def upload_image_to_supabase(file_obj, folder='listings') -> str | None:
    """
    Upload a Django InMemoryUploadedFile / TemporaryUploadedFile to Supabase Storage.
    Returns the public URL of the uploaded file, or None on failure.
    """
    if not SUPABASE_SERVICE_KEY:
        return None

    # Generate a unique filename
    ext = os.path.splitext(file_obj.name)[1].lower() or '.jpg'
    filename = f"{folder}/{uuid.uuid4().hex}{ext}"
    content_type = mimetypes.guess_type(file_obj.name)[0] or 'image/jpeg'

    # Read file bytes
    file_obj.seek(0)
    file_bytes = file_obj.read()

    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{filename}"
    headers = {
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': content_type,
        'x-upsert': 'true',
    }

    response = requests.post(url, data=file_bytes, headers=headers, timeout=30)

    if response.status_code in (200, 201):
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{filename}"
        return public_url

    # Log error details for debugging
    print(f"Supabase upload error: {response.status_code} — {response.text}")
    return None
