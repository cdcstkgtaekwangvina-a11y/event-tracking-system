from src.shared.base.base_schema import BaseSchema
import re
from pydantic import EmailStr, Field, field_validator
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class LoginRequest(BaseSchema):
    email_or_username: str = Field(
        description="Email hoặc username của bạn",
        pattern="^[a-zA-Z][a-zA-Z0-9_.-@]{2,19}$",
    )
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái viết hoa")

        if not re.search(r"[a-z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái viết thường")

        if not re.search(r"\d", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số")

        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt (@$!%*?&)")

        return v


class RegisterRequest(BaseSchema):
    email: EmailStr = Field(description="Email của bạn")
    username: Optional[str] = Field(
        default=None,
        description="Tên đăng nhập nếu không nhập mặc định là email",
        pattern="^[a-zA-Z][a-zA-Z0-9_.-@]{2,19}$",
    )
    name: str = Field(max_length=300, description="Tên hiển thị của bạn")
    password: str = Field(
        description="Mật khẩu của bạn (ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt)"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái viết hoa")

        if not re.search(r"[a-z]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái viết thường")

        if not re.search(r"\d", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số")

        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt (@$!%*?&)")

        return v


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
