from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import DateTime
from sqlmodel import BIGINT, Field, Relationship, SQLModel

from .base_model import CreatedAtModel, DeletedAtModel, PrimaryModel, UpdatedAtModel

if TYPE_CHECKING:
    from database.models.events_employees import EventsEmployees


class EVENT_STATUS(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class BaseEvents(SQLModel):
    name: str = Field(max_length=300)
    status: str = Field(max_length=50, default=EVENT_STATUS.DRAFT.value)
    description: str | None = Field(default=None, nullable=True)
    start_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    end_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    url_image: str | None = Field(default=None)
    url_map: str | None = Field(default=None, nullable=True)
    location: str | None = Field(default=None, max_length=500, nullable=True)


class Events(
    BaseEvents,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__: str = "events"
    id: int | None = Field(default=None, primary_key=True, sa_type=BIGINT)
    employee_links: list[EventsEmployees] | None = Relationship(back_populates="event")
