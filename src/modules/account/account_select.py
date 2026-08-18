from datetime import datetime
from uuid import UUID

from src.shared.base.base_schema import BaseSchema


class AccountSelect(BaseSchema):
    id: UUID
    name: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
