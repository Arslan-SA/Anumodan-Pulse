"""
AICTE FlowOps — Storage Backend Factory
"""

from functools import lru_cache

from app.config import get_settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorageBackend
from app.services.storage.s3 import S3StorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    """Return configured storage backend singleton."""
    settings = get_settings()
    backend_type = settings.storage_backend.lower()

    if backend_type == "s3":
        return S3StorageBackend(
            bucket_name=settings.s3_bucket_name,
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            region=settings.s3_region,
        )
    else:
        return LocalStorageBackend(base_dir=settings.storage_local_path)


__all__ = [
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "get_storage_backend",
]
