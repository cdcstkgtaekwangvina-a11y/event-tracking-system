from src.shared.base.base_schema import BaseSchema
from typing import Any, Optional


class FilterRequest(BaseSchema):
    field: Optional[str] = None
    value: Any


class PaginationRequest(BaseSchema):
    page: int = 1
    limit: int = 10
    sort_field: Optional[str] = None
    is_desc: bool = False
    filters: Optional[list[FilterRequest]] = None
    search: Optional[str] = None
    cursor: Optional[str] = None


class PaginationResponse(BaseSchema):
    page: int
    limit: int
    total: int
    total_items: int
    data: Optional[list[Any]]


class CursorPaginationRequest(BaseSchema):
    limit: int = 20
    cursor: Optional[str] = None
    is_desc: bool = True


class CursorPaginationResponse(BaseSchema):
    data: Optional[list[Any]] = None
    next_cursor: Optional[str] = None
    has_more: bool = False
