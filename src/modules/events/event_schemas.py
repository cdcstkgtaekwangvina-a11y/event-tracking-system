from datetime import date, datetime
from typing import Literal

from fastapi import Depends, Query
from pydantic import Field, model_validator

from database.models.events import BaseEvents
from src.shared.base.base_schema import BaseSchema
from src.shared.schemas.pagination_schemas import PaginationRequest, parse_pagination


class EventCreateRequest(BaseEvents):
    name: str = Field(max_length=300)
    description: str | None = Field(default=None)
    start_at: datetime | None = Field(default=None)
    end_at: datetime | None = Field(default=None)
    url_image: str | None = Field(default=None)
    url_map: str | None = Field(default=None)
    location: str | None = Field(default=None, max_length=500)


class EventUpdateRequest(BaseSchema):
    name: str = Field(max_length=300)
    description: str | None = None
    location: str | None = Field(default=None, max_length=500)
    start_at: datetime | None = Field(default=None)
    end_at: datetime | None = Field(default=None)
    url_image: str | None = Field(default=None)
    url_map: str | None = Field(default=None)

    @model_validator(mode="after")
    def check_start_end_time(self):
        if self.end_at is not None and self.start_at is not None:
            if self.end_at <= self.start_at:
                raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu")
        return self


class EventsPagination(BaseSchema):
    id: int
    name: str
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    url_image: str | None = None
    url_map: str | None = None


class EventsSchema(BaseSchema):
    id: int
    name: str
    description: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    url_image: str | None = None
    url_map: str | None = None
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


class EmployeeInEvent(BaseSchema):
    event_id: int
    employee_id: int
    name: str | None
    email: str | None
    position: str | None
    gender: str | None
    department: str | None
    starting_date: date | None
    status: str
    join_at: datetime | None
    check_in_at: datetime | None
    send_at: datetime | None


class EmployeeIdsSchema(BaseSchema):
    employee_ids: list[int] = Field(min_length=1)


class CheckInEmployeeRequest(BaseSchema):
    employee_id: int
    event_id: int
