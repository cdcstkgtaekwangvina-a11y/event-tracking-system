from sqlmodel import Field, SQLModel, Relationship
from datetime import date
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel, DeletedAtModel
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.events_employees import EventsEmployees


class BaseEmployees(SQLModel):
    name: str = Field(max_length=300, nullable=False)
    email: str | None = Field(max_length=500, nullable=True)
    position: str | None = Field(default=None, nullable=True, max_length=300)
    gender: str | None = Field(default=None, nullable=True, max_length=20)
    department: str | None = Field(default=None, nullable=True)
    starting_date: date | None = Field(default=None, nullable=True)


class Employees(
    BaseEmployees,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__: str = "employees"
    id: int | None = Field(default=None, primary_key=True)

    event_links: Optional[List[EventsEmployees]] = Relationship(
        back_populates="employee"
    )
