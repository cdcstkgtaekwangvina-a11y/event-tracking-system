from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import BIGINT, Field, Relationship, SQLModel

from .base_model import CreatedAtModel, DeletedAtModel, PrimaryModel, UpdatedAtModel

if TYPE_CHECKING:
    from database.models.events_employees import EventsEmployees


class BaseEmployees(SQLModel):
    name: str = Field(max_length=300, nullable=False)
    email: str | None = Field(max_length=500, nullable=True)
    position: str | None = Field(default=None, nullable=True, max_length=300)
    gender: str | None = Field(default=None, nullable=True, max_length=20)
    department: str | None = Field(default=None, nullable=True)
    starting_date: date | None = Field(default=None, nullable=True)
    qr_url: str | None = Field(default=None, nullable=True)
    meta_data: dict[str, Any] | None = Field(default=None, sa_type=JSONB)


class Employees(
    BaseEmployees,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__: str = "employees"
    id: int | None = Field(default=None, sa_type=BIGINT, primary_key=True)

    event_links: list[EventsEmployees] | None = Relationship(back_populates="employee")
