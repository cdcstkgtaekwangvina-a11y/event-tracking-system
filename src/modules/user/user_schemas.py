from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from src.shared.base.base_schema import BaseSchema
from src.shared.validators.account_validators import (
    validate_strong_password,
    validate_username,
)


class UpdateProfileRequest(BaseSchema):
    name: str | None = Field(default=None, max_length=300)
    username: str | None = Field(default=None, max_length=350)
    email: str | None = Field(default=None, max_length=300)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_username(v)


class SetAvatarFromMediaRequest(BaseSchema):
    """Links an already-uploaded file from the Media library as the avatar,
    instead of uploading a new one — see `UserServices.set_avatar_from_media`."""

    media_id: int


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_strong_password(v)

    @model_validator(mode="after")
    def validate_confirm_password(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("Xác nhận mật khẩu mới không khớp")
        return self


class CreateAccountRequest(BaseSchema):
    """Admin-facing account creation (`/admin/account`) — role is always
    hardcoded to ADMIN server-side, never accepted from the client."""

    name: str = Field(max_length=300)
    username: str = Field(max_length=350)
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_strong_password(v)


class UpdateAccountRequest(BaseSchema):
    """Admin-facing account edit — email is only honored if the requester
    is SUPER_ADMIN (enforced in `UserServices.update_account`)."""

    name: str | None = Field(default=None, max_length=300)
    username: str | None = Field(default=None, max_length=350)
    email: str | None = Field(default=None, max_length=300)
    password: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_strong_password(v)


class UserSchema(BaseSchema):
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
