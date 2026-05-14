from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel, DeletedAtModel
from .events_employees import EventsEmployees
from sqlalchemy import DateTime
from typing import cast, Any, Optional, TYPE_CHECKING


class BaseEvents(SQLModel):
    name: str = Field(max_length=300)
    start_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    end_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    url_image: str | None = Field(default=None)
    url_map: str | None = Field(default=None, nullable=True)


if TYPE_CHECKING:
    from database.models.files import Files


class Events(
    BaseEvents,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__ = "events"
    id: int | None = Field(default=None, primary_key=True)
    file_id: Optional[int] = Field(default=None, foreign_key="files.id")
    employees: list["EventsEmployees"] = Relationship(back_populates="event")
    file: Optional["Files"] = Relationship(back_populates="events")
