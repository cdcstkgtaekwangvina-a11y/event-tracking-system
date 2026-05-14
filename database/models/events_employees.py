from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum


class EVENT_EMPLOYEE_STATUS(str, Enum):
    PENDING = "PENDING"
    CHECK_IN = "CHECK_IN"
    NO_SHOW = "NO_SHOW"


if TYPE_CHECKING:
    from .events import Events
    from .employees import Employees


class EventsEmployees(SQLModel, table=True):
    __tablename__ = "events_employees"
    status: str = Field(
        default=EVENT_EMPLOYEE_STATUS.PENDING, nullable=False, max_length=50
    )

    join_at: datetime | None = Field(default=None, nullable=True)
    check_in_at: datetime | None = Field(default=None, nullable=True)

    event_id: int | None = Field(
        default=None, primary_key=True, foreign_key="events.id"
    )
    employee_id: int | None = Field(
        default=None, primary_key=True, foreign_key="employees.id"
    )

    event: Optional["Events"] = Relationship(back_populates="employees")
    employee: Optional["Employees"] = Relationship(back_populates="events")
