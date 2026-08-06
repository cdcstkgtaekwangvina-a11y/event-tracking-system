from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Generic, TypeVar, cast, Any
from src.shared.helpers.time_extensions import get_now_vn
from sqlalchemy import DateTime

IDType = TypeVar("IDType")


class PrimaryModel(SQLModel, Generic[IDType]):
    id: IDType = Field(primary_key=True)


class CreatedAtModel(SQLModel):
    created_at: datetime = Field(
        default_factory=get_now_vn,
        sa_type=cast(Any, DateTime(timezone=True)),
        nullable=False,
    )


class UpdatedAtModel(SQLModel):
    updated_at: datetime | None = Field(
        default=None,
        sa_type=cast(Any, DateTime(timezone=True)),
        sa_column_kwargs={"onupdate": get_now_vn},
        nullable=True,
    )


class DeletedAtModel(SQLModel):
    deleted_at: datetime | None = Field(
        default=None, sa_type=cast(Any, DateTime(timezone=True)), nullable=True
    )


class BaseModel(PrimaryModel[IDType], CreatedAtModel, UpdatedAtModel, DeletedAtModel):
    pass
