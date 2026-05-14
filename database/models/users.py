from uuid import UUID, uuid8
from sqlmodel import Field, SQLModel
from src.modules.user.role_constants import ROLE
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel


class BaseUsers(SQLModel):
    name: str = Field(max_length=300)
    username: str = Field(max_length=350, unique=True)
    email: str = Field(nullable=False, max_length=300, unique=True)
    role: str = Field(max_length=20, nullable=False, default=ROLE.COMMON)
    avatar: str | None = Field(default=None, nullable=True)
    is_active: bool = Field(default=True, nullable=False)


class Users(
    PrimaryModel[UUID],
    CreatedAtModel,
    UpdatedAtModel,
    BaseUsers,
    table=True,
):
    __tablename__ = "users"
    id: UUID = Field(default=uuid8(), primary_key=True)
    password: str | None = Field(default=None, max_length=500, nullable=True)
    google_sub: str | None = Field(
        default=None, max_length=500, nullable=True, unique=True, index=True
    )
