from src.shared.base.base_schema import BaseSchema
from typing import Optional
from pydantic import Field
from datetime import date
from database.models.employees import Employees


class EmployeeCreateRequest(BaseSchema):
    name: str = Field(max_length=300)
    email: Optional[str] = Field(max_length=500)
    position: Optional[str] = Field(max_length=300)
    gender: Optional[str] = Field(max_length=20)
    department: Optional[str]
    starting_date: Optional[date]


class EmployeeUpdateRequest(BaseSchema):
    name: str = Field(max_length=300)
    email: Optional[str] = Field(max_length=500)
    position: Optional[str] = Field(max_length=300)
    gender: Optional[str] = Field(max_length=20)
    department: Optional[str]
    starting_date: Optional[date]


class BulkUpsertResponse(BaseSchema):
    added_employees: list[Employees] = []
    updated_employees: list[Employees] = []


BulkUpsertResponse.model_rebuild()
