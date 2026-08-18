from pydantic import EmailStr, Field, field_validator

from src.shared.base.base_schema import BaseSchema
from src.shared.validators.account_validators import (
    validate_strong_password,
    validate_username,
)


class CreateAccountRequest(BaseSchema):
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
