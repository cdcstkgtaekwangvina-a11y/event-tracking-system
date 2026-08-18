from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from src.shared.base.base_schema import BaseSchema
from src.shared.validators.account_validators import (
    validate_strong_password,
    validate_username,
)


class LoginRequest(BaseSchema):
    email_or_username: str = Field(description="Email hoặc username của bạn")
    password: str

    @field_validator("email_or_username")
    @classmethod
    def validate_email_or_username(cls, v: str) -> str:
        if not v or len(v) < 3 or len(v) > 20:
            raise ValueError("Email hoặc tên đăng nhập không hợp lệ")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_strong_password(v)


class RegisterRequest(BaseSchema):
    email: EmailStr = Field(description="Email của bạn")
    username: str | None = Field(
        default=None,
        description="Tên đăng nhập nếu không nhập mặc định là email",
    )
    name: str = Field(max_length=300, description="Tên hiển thị của bạn")
    password: str = Field(
        description="Mật khẩu của bạn (ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt)"
    )

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_strong_password(v)


class TokenResponse(BaseSchema):
    access_token: str


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class UserVerifyToken(BaseSchema):
    id: UUID | None = None
    token_version: int | None = 0
    role: str | None = None


class TokenData(BaseSchema):
    id: UUID | None = None
    role: str | None = None
    exp: datetime | None = None
    valid: bool = True
    user: Any | None = None
    access_token: str
    token_version: int | None = 0
    status_code: int | None = None
    audience: str | None = None
    issuer: str | None = None
    message: str | None = None
