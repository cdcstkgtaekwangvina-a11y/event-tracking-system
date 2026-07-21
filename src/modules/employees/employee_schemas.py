from datetime import date
from uuid import UUID

from pydantic import Field

from src.shared.base.base_schema import BaseSchema


class EmployeeCreateRequest(BaseSchema):
    name: str = Field(max_length=300)
    email: str | None = Field(max_length=500)
    position: str | None = Field(max_length=300)
    gender: str | None = Field(max_length=20)
    department: str | None
    starting_date: date | None


class EmployeeUpdateRequest(BaseSchema):
    name: str = Field(max_length=300)
    email: str | None = Field(max_length=500)
    position: str | None = Field(max_length=300)
    gender: str | None = Field(max_length=20)
    department: str | None
    starting_date: date | None


class BulkUpsertEmployeeRequest(BaseSchema):
    file_url: str
    column_map: dict[str, str] | None = None
    header_row: int | None = Field(default=None, ge=0)


class BulkUpsertResponse(BaseSchema):
    job_id: UUID


BulkUpsertResponse.model_rebuild()
