from uuid import UUID

from src.shared.base.base_schema import BaseSchema


class LoginSelect(BaseSchema):
    id: UUID
    email: str
    username: str
    password: str | None
    role: str
    is_active: bool
    otp_code: str | None
    expired_at: str | None
    google_sub: str | None
    token_version: int = 0
