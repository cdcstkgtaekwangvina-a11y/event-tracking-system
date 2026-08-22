# from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, cast

from sqlmodel import DateTime, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from database.models.employees import Employees
    from database.models.events import Events


class EVENT_EMPLOYEE_STATUS(str, Enum):
    PENDING = "PENDING"
    CHECK_IN = "CHECK_IN"
    NO_SHOW = "NO_SHOW"


class EventsEmployees(SQLModel, table=True):
    __tablename__: str = "events_employees"
    status: str = Field(
        default=EVENT_EMPLOYEE_STATUS.PENDING, nullable=False, max_length=50
    )

    join_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    check_in_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )
    send_at: datetime | None = Field(
        default=None, nullable=True, sa_type=cast(Any, DateTime(timezone=True))
    )

    event_id: int | None = Field(
        default=None, primary_key=True, foreign_key="events.id"
    )
    employee_id: int | None = Field(
        default=None, primary_key=True, foreign_key="employees.id"
    )

    event: Optional["Events"] = Relationship(back_populates="employee_links")
    employee: Optional["Employees"] = Relationship(back_populates="event_links")
