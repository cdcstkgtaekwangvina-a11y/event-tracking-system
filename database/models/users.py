from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, cast

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel
from uuid6 import UUID, uuid8

from src.modules.user.role_constants import ROLE

from .base_model import CreatedAtModel, PrimaryModel, UpdatedAtModel

if TYPE_CHECKING:
    from database.models.media import Medias


class BaseUsers(SQLModel):
    name: str = Field(max_length=300)
    username: str = Field(max_length=350, unique=True)
    email: str = Field(nullable=False, max_length=300, unique=True)
    role: str = Field(max_length=20, nullable=False, default=ROLE.COMMON)
    is_active: bool = Field(default=True, nullable=False)
    avatar_url: str | None = Field(default=None, nullable=True)


class Users(
    PrimaryModel[UUID],
    CreatedAtModel,
    UpdatedAtModel,
    BaseUsers,
    table=True,
):
    __tablename__: str = "users"
    id: UUID = Field(default_factory=uuid8, primary_key=True)
    password: str | None = Field(default=None, nullable=True)
    otp_code: str | None = Field(default=None, max_length=10, nullable=True)
    token_version: int = Field(default=0, nullable=False)
    expired_at: datetime | None = Field(
        default=None, sa_type=cast(Any, DateTime(timezone=True)), nullable=True
    )
    google_sub: str | None = Field(
        default=None, max_length=500, nullable=True, unique=True, index=True
    )
    media_id: int | None = Field(default=None, foreign_key="medias.id")
    media: Optional["Medias"] = Relationship(back_populates="users")
