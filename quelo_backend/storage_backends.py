# quelo_backend/storage_backends.py

from storages.backends.s3boto3 import S3Boto3Storage
from .settings import AWS_STORAGE_BUCKET_NAME_STATIC,AWS_STORAGE_BUCKET_NAME_MEDIA


class StaticStorage(S3Boto3Storage):
    """
    Storage for static files (CSS, JS, images).
    Uploads to: s3://<bucket>/static/
    """
    
    bucket_name = AWS_STORAGE_BUCKET_NAME_STATIC
    location = "static"
    default_acl = None
    file_overwrite = True       # overwrite old versions (good for static)
    

class MediaStorage(S3Boto3Storage):
    """
    Storage for user-uploaded media.
    Uploads to: s3://<bucket>/media/
    """
    
    bucket_name = AWS_STORAGE_BUCKET_NAME_MEDIA
    location = "media"
    default_acl = None
    file_overwrite = False      # keep unique filenames for uploads

    