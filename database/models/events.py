from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel, DeletedAtModel
from sqlalchemy import DateTime
from typing import cast, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.files import Files
    from database.models.events_employees import EventsEmployees


class BaseEvents(SQLModel):
    name: str = Field(max_length=300)
    description: str | None = Field(default=None, nullable=True)
    start_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    end_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    url_image: str | None = Field(default=None)
    url_map: str | None = Field(default=None, nullable=True)


class Events(
    BaseEvents,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__: str = "events"
    id: int | None = Field(default=None, primary_key=True)
    file_id: Optional[int] = Field(default=None, foreign_key="files.id")
    employee_links: Optional[List[EventsEmployees]] = Relationship(
        back_populates="event"
    )
    file: Optional["Files"] = Relationship(back_populates="events")
