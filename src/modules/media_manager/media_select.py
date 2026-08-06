from typing import Any
from src.shared.base.base_schema import BaseSchema
from datetime import datetime


class ValidateNameSelect(BaseSchema):
    id: int
    name: str
    parent_id: int | None
    is_folder: bool


class PrefixSelect(BaseSchema):
    id: int
    name: str


class MediaSelect(BaseSchema):
    id: int
    name: str
    url: str | None
    prefix: str | None
    media_metadata: dict[str, Any] | None
    parent_id: int | None
    is_folder: bool
    created_at: datetime
    updated_at: datetime | None
