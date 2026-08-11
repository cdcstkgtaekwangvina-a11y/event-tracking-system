from datetime import datetime

from uuid6 import UUID

from src.shared.base.base_schema import BaseSchema


class BaseUserSelect(BaseSchema):
    id: UUID
    name: str
    username: str
    email: str
    role: str


class UserSelect(BaseSchema):
    id: UUID | None
    name: str | None
    username: str | None
    email: str | None
    role: str | None
    is_active: bool
    avatar_url: str | None
    created_at: datetime | None
    updated_at: datetime | None
    file_id: int | None = None
    file_url: str | None = None
    token_version: int = 0
