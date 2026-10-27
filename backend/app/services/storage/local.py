"""
AICTE FlowOps — Local Filesystem Storage Backend

Implements StorageBackend using the local filesystem for local development
and testing. Enforces path traversal prevention and ensures files are kept
strictly outside publicly served frontend directories.
"""

import os
from pathlib import Path
from typing import BinaryIO, Optional

from app.services.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str = "./storage/uploads"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str) -> Path:
        """
        Resolve storage_key relative to base_dir, strictly preventing
        directory traversal attacks.
        """
        # Normalize key
        clean_key = storage_key.lstrip("/\\")
        target_path = (self.base_dir / clean_key).resolve()

        # Enforce that target_path is within base_dir
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError(f"Security error: Path traversal detected in storage key '{storage_key}'")

        return target_path

    def save(self, storage_key: str, data: BinaryIO | bytes, content_type: Optional[str] = None) -> int:
        target_path = self._resolve_safe_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)


        if isinstance(data, bytes):
            with open(target_path, "wb") as f:
                f.write(data)
            return len(data)
        else:
            bytes_written = 0
            with open(target_path, "wb") as f:
                while chunk := data.read(64 * 1024):
                    f.write(chunk)
                    bytes_written += len(chunk)
            return bytes_written

    def get(self, storage_key: str) -> BinaryIO:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.is_file():
            raise FileNotFoundError(f"Stored file '{storage_key}' does not exist.")
        return open(target_path, "rb")

    def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_safe_path(storage_key)
        if target_path.is_file():
            target_path.unlink()
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_safe_path(storage_key)
        return target_path.is_file()

    def get_local_path(self, storage_key: str) -> Optional[str]:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.is_file():
            raise FileNotFoundError(f"Stored file '{storage_key}' does not exist.")
        return str(target_path)

    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> Optional[str]:
        # Local storage does not use pre-signed URLs; files are served directly through the API
        return None
