from datetime import date
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from src.shared.base.base_schema import BaseSchema


class EmployeeCreateRequest(BaseSchema):
    id: int | None = Field(default=None, description="Mã nhân viên (tuỳ chọn)")
    name: str = Field(max_length=300)
    email: str | None = Field(default=None, max_length=500)
    position: str | None = Field(default=None, max_length=300)
    gender: str | None = Field(default=None, max_length=20)
    department: str | None = None
    starting_date: date | None = None

    @field_validator(
        "email", "position", "gender", "department", "starting_date", mode="before"
    )
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class EmployeeUpdateRequest(BaseSchema):
    name: str = Field(max_length=300)
    email: str | None = Field(default=None, max_length=500)
    position: str | None = Field(default=None, max_length=300)
    gender: str | None = Field(default=None, max_length=20)
    department: str | None = None
    starting_date: date | None = None

    @field_validator(
        "email", "position", "gender", "department", "starting_date", mode="before"
    )
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class BulkUpsertEmployeeRequest(BaseSchema):
    file_url: str
    column_map: dict[str, str] | None = None
    header_row: int | None = Field(default=None, ge=0)


class BulkUpsertResponse(BaseSchema):
    job_id: UUID


class ReadSheetFile(BaseSchema):
    url: str
    row_count: int = Field(default=10, gt=0)
    header_row: int | None = Field(default=None, ge=1)


class ReadSheetFileResponse(BaseSchema):
    row_index: int
    data: list[str]


class EmployeeBulkDeleteRequest(BaseSchema):
    ids: list[int] = Field(min_length=1, description="Danh sách ID nhân viên cần xóa")


BulkUpsertResponse.model_rebuild()
