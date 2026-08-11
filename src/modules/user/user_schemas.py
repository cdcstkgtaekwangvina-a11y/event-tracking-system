from src.shared.base.base_schema import BaseSchema
from uuid import UUID
from typing import Optional
from datetime import datetime


class UserSchema(BaseSchema):
    id: Optional[UUID]
    name: Optional[str]
    username: Optional[str]
    email: Optional[str]
    role: Optional[str]
    is_active: bool
    avatar_url: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    file_id: Optional[int] = None
    file_url: Optional[str] = None
    token_version: int = 0
