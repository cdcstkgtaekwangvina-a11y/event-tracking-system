from database.models.events import BaseEvents
from typing import Literal, Optional
from datetime import datetime
from fastapi import Depends, Query
from src.shared.base.base_schema import BaseSchema
from src.shared.schemas.pagination_schemas import PaginationRequest, parse_pagination


class EventCreateRequest(BaseEvents):
    pass


class EventUpdateRequest(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    url_image: Optional[str] = None
    url_map: Optional[str] = None


class EventsSchema(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    url_image: Optional[str] = None
    url_map: Optional[str] = None
    employee_count: int = 0


class PublicEventQuery(PaginationRequest):
    """Query parameters used by the public event listing on the home page."""

    limit: int = 10
    status: Literal["all", "ongoing", "upcoming"] = "all"
    sort_field: Literal["start_at", "name"] = "start_at"
    is_desc: bool = False


class AdminEventQuery(PaginationRequest):
    """Query parameters for the event management screen."""

    limit: int = 10
    status: Literal["all", "ongoing", "upcoming", "ended"] = "all"
    sort_field: Literal["start_at", "name", "created_at", "updated_at"] = "start_at"
    is_desc: bool = False


def parse_public_event_query(
    pagination: PaginationRequest = Depends(parse_pagination),
    status: Literal["all", "ongoing", "upcoming"] = Query(default="all"),
) -> PublicEventQuery:
    """Parse public event filters without exposing Pydantic factories to FastAPI."""
    data = pagination.model_dump()
    data["sort_field"] = pagination.sort_field or "start_at"
    data["status"] = status
    return PublicEventQuery.model_validate(data)


def parse_admin_event_query(
    pagination: PaginationRequest = Depends(parse_pagination),
    status: Literal["all", "ongoing", "upcoming", "ended"] = Query(default="all"),
) -> AdminEventQuery:
    """Parse admin event filters without exposing Pydantic factories to FastAPI."""
    data = pagination.model_dump()
    data["sort_field"] = pagination.sort_field or "start_at"
    data["status"] = status
    return AdminEventQuery.model_validate(data)
