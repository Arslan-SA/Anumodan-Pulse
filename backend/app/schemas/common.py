"""
AICTE FlowOps — Common Schemas

Generic pagination and response wrappers.
"""

from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated collection response."""
    items: List[T]
    total: int = Field(..., description="Total matching records count")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total pages available")
