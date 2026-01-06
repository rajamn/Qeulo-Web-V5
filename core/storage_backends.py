# core/storage_backends.py
from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    bucket_name = "quelo-static"
    location = "static"           # prefix inside the bucket
    default_acl = "public-read"   # optional if your bucket policy is public
    file_overwrite = True

class MediaStorage(S3Boto3Storage):
    bucket_name = "quelo-media"
    location = "media"
    default_acl = "public-read"   # optional if your bucket policy is public
    file_overwrite = False
