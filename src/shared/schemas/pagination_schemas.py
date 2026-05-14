from pydantic import BaseModel
from typing import Any, Optional


class FilterRequest(BaseModel):
    field: Optional[str] = None
    value: Any


class PaginationRequest(BaseModel):
    page: int = 1
    limit: int = 10
    sort_field: Optional[str] = None
    is_desc: bool = False
    filters: Optional[list["FilterRequest"]] = None
    search: Optional[str] = None


class PaginationResponse(BaseModel):
    page: int
    limit: int
    total: int
    total_items: int
    data: list[Any]
