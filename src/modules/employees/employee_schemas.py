from database.models.employees import BaseEmployees
from sqlmodel import SQLModel
from typing import Optional
from datetime import date


class EmployeeCreateRequest(BaseEmployees):
    pass


class EmployeeUpdateRequest(SQLModel):
    name: Optional[str] = None
    position: Optional[str] = None
    gender: Optional[str] = None
    department: Optional[str] = None
    starting_date: Optional[date] = None
