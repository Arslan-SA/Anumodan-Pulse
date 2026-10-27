"""
AICTE FlowOps — Storage Backend Factory
"""

from functools import lru_cache
from typing import Optional

from app.config import get_settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorageBackend
from app.services.storage.mock_s3 import MockS3StorageBackend
from app.services.storage.s3 import S3StorageBackend

_override_backend: Optional[StorageBackend] = None


def set_storage_backend_override(backend: Optional[StorageBackend]) -> None:
    """Set or reset an explicit storage backend override (used for testing)."""
    global _override_backend
    _override_backend = backend


def get_storage_backend() -> StorageBackend:
    """Return active storage backend singleton or test override."""
    global _override_backend
    if _override_backend is not None:
        return _override_backend

    return _get_configured_storage_backend()


@lru_cache
def _get_configured_storage_backend() -> StorageBackend:
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
    "MockS3StorageBackend",
    "get_storage_backend",
    "set_storage_backend_override",
]
