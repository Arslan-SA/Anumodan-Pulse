"""
AICTE FlowOps — Storage Backend Interface

Defines the abstract interface for binary file storage, supporting both
local filesystem storage for development and S3-compatible object storage
for production deployments.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class StorageBackend(ABC):
    """Abstract base class defining statutory document storage operations."""

    @abstractmethod
    def save(self, storage_key: str, data: BinaryIO | bytes, content_type: Optional[str] = None) -> int:
        """
        Store a file at the designated storage_key.
        Returns the number of bytes written.
        """
        pass


    @abstractmethod
    def get(self, storage_key: str) -> BinaryIO:
        """
        Retrieve a readable binary stream for the specified storage_key.
        Raises FileNotFoundError if the key does not exist.
        """
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """
        Delete the file at storage_key.
        Returns True if deleted, False if it did not exist.
        """
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check whether a file exists at storage_key."""
        pass

    @abstractmethod
    def get_local_path(self, storage_key: str) -> Optional[str]:
        """
        Return the absolute local filesystem path if this backend supports direct file access.
        Returns None for remote object storage backends.
        """
        pass

    @abstractmethod
    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> Optional[str]:
        """
        Generate a pre-signed download URL for object storage backends.
        Returns None if direct file serving is used.
        """
        pass
