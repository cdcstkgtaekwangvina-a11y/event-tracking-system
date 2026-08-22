from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import BIGINT, Field, Relationship, SQLModel, UniqueConstraint

from .base_model import CreatedAtModel, DeletedAtModel, PrimaryModel, UpdatedAtModel

if TYPE_CHECKING:
    from database.models.users import Users


class BaseMedia(SQLModel):
    name: str = Field(index=True, max_length=800, nullable=False)
    url: str | None = Field(default=None, nullable=True)
    prefix: str = Field(default="", index=True)
    media_metadata: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    parent_id: int | None = Field(default=None, index=True, foreign_key="medias.id")
    is_folder: bool = Field(default=False, nullable=False)
    is_direct_delete: bool = Field(default=False)
    __table_args__ = (
        UniqueConstraint("name", "parent_id", name="uq_media_name_parent"),
    )


class Medias(
    BaseMedia,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__: str = "medias"
    id: int | None = Field(default=None, primary_key=True, sa_type=BIGINT)
    parent: Optional["Medias"] = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "Medias.id"}
    )
    children: list["Medias"] | None = Relationship(back_populates="parent")

    users: list["Users"] | None = Relationship(back_populates="media")
