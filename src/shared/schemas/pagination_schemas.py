import json
from typing import Annotated, Any
from urllib.parse import unquote

from fastapi import Depends, Query
from pydantic import Field

from src.shared.base.base_schema import BaseSchema


class FilterRequest(BaseSchema):
    field: str | None = None
    value: Any


class PaginationRequest(BaseSchema):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, gt=0, le=100)
    sort_field: str | None = None
    is_desc: bool = False
    filters: list[FilterRequest] = Field(default_factory=list)
    search: str | None = None


def parse_pagination(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, gt=0, le=100),
    sort_field: str | None = Query(default=None),
    is_desc: bool = Query(default=False),
    search: str | None = Query(default=None),
    filters: str | None = Query(default=None, description="JSON string filters"),
) -> PaginationRequest:

    parsed_filters: list[FilterRequest] = []

    if filters:
        try:
            raw_json = unquote(filters).strip()

            data = json.loads(raw_json)
            if isinstance(data, dict):
                data = [data]

            if isinstance(data, list):
                parsed_filters = [
                    FilterRequest(**item) for item in data if isinstance(item, dict)
                ]
        except Exception:
            parsed_filters = []

    return PaginationRequest(
        page=page,
        limit=limit,
        sort_field=sort_field,
        is_desc=is_desc,
        search=search,
        filters=parsed_filters,
    )


PaginationQuery = Annotated[PaginationRequest, Depends(parse_pagination)]


class PaginationResponse(BaseSchema):
    page: int
    limit: int
    total: int
    total_items: int = Field(default=0, ge=0)
    data: list[Any] | None


class CursorPaginationRequest(BaseSchema):
    search: str | None = None
    filters: list[FilterRequest] = Field(default_factory=list)
    limit: int = Field(default=20, le=100, gt=1)
    cursor: str | None = None
    sort_field: str | None = None
    is_desc: bool = True
    is_cursor_desc: bool = True


def parse_cursor_pagination(
    search: str | None = Query(default=None),
    filters: str | None = Query(default=None, description="JSON string filters"),
    limit: int = Query(default=20, gt=1, le=100),
    cursor: str | None = Query(default=None),
    sort_field: str | None = Query(default=None),
    is_desc: bool = Query(default=True),
    is_cursor_desc: bool = Query(default=True),
) -> CursorPaginationRequest:

    parsed_filters: list[FilterRequest] = []
    if filters:
        try:
            raw_json = unquote(filters).strip()

            data = json.loads(raw_json)
            if isinstance(data, dict):
                data = [data]

            if isinstance(data, list):
                parsed_filters = [
                    FilterRequest(**item) for item in data if isinstance(item, dict)
                ]
        except Exception:
            parsed_filters = []

    return CursorPaginationRequest(
        search=search,
        filters=parsed_filters,
        limit=limit,
        cursor=cursor,
        sort_field=sort_field,
        is_desc=is_desc,
        is_cursor_desc=is_cursor_desc,
    )


CursorPaginationQuery = Annotated[
    CursorPaginationRequest, Depends(parse_cursor_pagination)
]


class CursorPaginationResponse(BaseSchema):
    data: list[Any] | None = None
    next_cursor: str | None = None
    has_more: bool = False
