from typing import Any

from pydantic import Field

from src.shared.base.base_schema import BaseSchema


class FileConfigSchema(BaseSchema):
    max_size_file: int = Field(gt=0)


class UpdateSettingSchema(BaseSchema):
    value: dict[str, Any] | None = Field(default={})
    description: str | None = Field(default=None)
