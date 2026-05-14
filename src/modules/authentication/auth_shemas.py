from sqlalchemy.sql.operators import regexp_match_op
from pydantic import BaseModel, EmailStr, field_validator, model_validator, Field
from typing import Annotated, Optional


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="Email của bạn")
    username: Optional[str] = None = Field(description="Tên đăng nhập nếu không nhập mặc định là email", pattern="^[a-zA-Z][a-zA-Z0-9_.-@]{2,19}$")
    name: str = Field(max_length=300, description="Tên hiển thị của bạn")
    password: str = Field(
        min_length=8,
        max_length=500,
        pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
        description="Mật khẩu của bạn, ít nhất 8 ký tự, chứa chữ hoa, chữ thường, số và ký tự đặc biệt",
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
