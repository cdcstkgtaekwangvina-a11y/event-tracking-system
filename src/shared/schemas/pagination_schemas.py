from pydantic import Field
from src.shared.base.base_schema import BaseSchema
from typing import Any, Optional


class FilterRequest(BaseSchema):
    field: Optional[str] = None
    value: Any


class PaginationRequest(BaseSchema):
    # page: int = Field(default=1, gt=1)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, gt=0, le=100)
    sort_field: Optional[str] = None
    is_desc: bool = False
    filters: Optional[list[FilterRequest]] = None
    search: Optional[str] = None


class PaginationResponse(BaseSchema):
    page: int
    limit: int
    total: int
    total_items: int = Field(default=0, ge=0)
    data: Optional[list[Any]]


class CursorPaginationRequest(BaseSchema):
    search: Optional[str] = None
    filters: Optional[list[FilterRequest]] = None
    limit: int = Field(default=20, le=100, gt=1)
    cursor: Optional[str] = None
    sort_field: Optional[str] = None
    is_desc: bool = True
    is_cursor_desc: bool = True


class CursorPaginationResponse(BaseSchema):
    data: Optional[list[Any]] = None
    next_cursor: Optional[str] = None
    has_more: bool = False
