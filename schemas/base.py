"""
Base Schema Classes
Common response schemas and base models
"""
from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional, List, Any
from datetime import datetime


T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response schema"""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataResponse(BaseResponse, Generic[T]):
    """Generic data response schema"""
    data: T


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated response schema"""
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = False
    error_code: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MessageResponse(BaseResponse):
    """Simple message response"""
    message: str
