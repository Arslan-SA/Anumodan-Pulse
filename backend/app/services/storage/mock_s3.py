"""
AICTE FlowOps — In-Memory Mock S3 Cloud Storage Backend

Provides an in-memory mock implementation of StorageBackend for automated testing.
Does not write any bytes to the local filesystem and requires no real AWS/cloud credentials.
Simulates S3 bucket behavior, object upload/download, deletion, existence checks,
and controlled failure injection.
"""

import io
from typing import BinaryIO, Dict, Optional, Tuple

from app.services.storage.base import StorageBackend


class MockS3StorageBackend(StorageBackend):
    def __init__(self, bucket_name: str = "test-aicte-documents", region: str = "ap-south-1"):
        self.bucket_name = bucket_name
        self.region = region
        # Maps storage_key -> (bytes, content_type)
        self._objects: Dict[str, Tuple[bytes, Optional[str]]] = {}
        # Failure simulation flag
        self.simulate_outage: bool = False

    def save(self, storage_key: str, data: BinaryIO | bytes, content_type: Optional[str] = None) -> int:
        if self.simulate_outage:
            raise RuntimeError("Simulated S3 Cloud Storage Connection Error (503 Service Unavailable)")

        if isinstance(data, bytes):
            raw_bytes = data
        else:
            raw_bytes = data.read()

        self._objects[storage_key] = (raw_bytes, content_type)
        return len(raw_bytes)

    def get(self, storage_key: str) -> BinaryIO:
        if self.simulate_outage:
            raise RuntimeError("Simulated S3 Cloud Storage Connection Error (503 Service Unavailable)")

        if storage_key not in self._objects:
            raise FileNotFoundError(f"Document '{storage_key}' not found in S3 bucket '{self.bucket_name}'.")

        raw_bytes, _ = self._objects[storage_key]
        return io.BytesIO(raw_bytes)

    def delete(self, storage_key: str) -> bool:
        if self.simulate_outage:
            raise RuntimeError("Simulated S3 Cloud Storage Connection Error (503 Service Unavailable)")

        if storage_key in self._objects:
            del self._objects[storage_key]
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        if self.simulate_outage:
            return False
        return storage_key in self._objects

    def get_local_path(self, storage_key: str) -> Optional[str]:
        # Remote cloud object storage has no local path
        return None

    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> Optional[str]:
        if self.simulate_outage:
            return None
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{storage_key}?X-Amz-Expires={expires_in_seconds}&X-Amz-Signed=true"

    def clear(self) -> None:
        """Clear all stored objects."""
        self._objects.clear()
