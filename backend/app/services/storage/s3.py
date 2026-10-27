"""
AICTE FlowOps — S3-Compatible Object Storage Backend

Provides cloud object storage integration for AWS S3, Cloudflare R2, MinIO, or Google Cloud Storage.
Stores file contents directly in cloud buckets without persisting bytes to the local filesystem.

Configuration:
Set the following environment variables in `.env` to enable S3 storage:
- STORAGE_BACKEND=s3
- S3_BUCKET_NAME=aicte-flowops-documents
- S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com  (optional for MinIO / Cloudflare R2)
- S3_ACCESS_KEY_ID=<access_key>
- S3_SECRET_ACCESS_KEY=<secret_key>
- S3_REGION=ap-south-1
"""

import io
import logging
from typing import Any, BinaryIO, Optional

from app.services.storage.base import StorageBackend

logger = logging.getLogger("aicte_flowops.storage.s3")


class S3StorageBackend(StorageBackend):
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region or "ap-south-1"
        self._client = client

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise NotImplementedError(
                "S3 storage backend is configured, but 'boto3' is not installed. "
                "Install it via `pip install boto3` to use S3-compatible object storage."
            )

        if not self.bucket_name or not self.access_key_id or not self.secret_access_key:
            raise ValueError(
                "S3 storage requires S3_BUCKET_NAME, S3_ACCESS_KEY_ID, and S3_SECRET_ACCESS_KEY to be set."
            )

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
            config=Config(signature_version="s3v4"),
        )
        return self._client

    def save(self, storage_key: str, data: BinaryIO | bytes, content_type: Optional[str] = None) -> int:
        """Upload stream directly to cloud object storage. Does not write to local disk."""
        client = self._get_client()
        if isinstance(data, bytes):
            stream = io.BytesIO(data)
            size = len(data)
        else:
            stream = data
            data.seek(0, 2)
            size = data.tell()
            data.seek(0)

        extra_args = {"ContentType": content_type} if content_type else {}
        try:
            if extra_args:
                client.upload_fileobj(stream, self.bucket_name, storage_key, ExtraArgs=extra_args)
            else:
                client.upload_fileobj(stream, self.bucket_name, storage_key)
            return size
        except Exception as e:
            logger.error(f"S3 upload error for key '{storage_key}' in bucket '{self.bucket_name}': {e}")
            raise RuntimeError(f"Cloud storage upload failed: {e}") from e

    def get(self, storage_key: str) -> BinaryIO:
        """Download stream directly from cloud object storage in-memory."""
        client = self._get_client()
        buffer = io.BytesIO()
        try:
            client.download_fileobj(self.bucket_name, storage_key, buffer)
            buffer.seek(0)
            return buffer
        except Exception as e:
            err_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            if err_code in ["404", "NoSuchKey"]:
                raise FileNotFoundError(f"Document '{storage_key}' not found in cloud storage.")
            logger.error(f"S3 download error for key '{storage_key}': {e}")
            raise RuntimeError(f"Cloud storage download failed: {e}") from e

    def delete(self, storage_key: str) -> bool:
        """Delete object from cloud object storage."""
        client = self._get_client()
        try:
            client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception as e:
            logger.error(f"S3 delete error for key '{storage_key}': {e}")
            return False

    def exists(self, storage_key: str) -> bool:
        """Check object existence in cloud object storage via head_object."""
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception as e:
            err_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            if err_code in ["404", "NoSuchKey"]:
                return False
            logger.warning(f"S3 head_object error for key '{storage_key}': {e}")
            return False

    def get_local_path(self, storage_key: str) -> Optional[str]:
        """S3 storage is remote; no local filesystem path exists."""
        return None

    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> Optional[str]:
        """Generate a time-limited pre-signed download URL."""
        client = self._get_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": storage_key},
                ExpiresIn=expires_in_seconds,
            )
            return url
        except Exception as e:
            logger.error(f"S3 generate_presigned_url error for key '{storage_key}': {e}")
            return None
