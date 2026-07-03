from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel, DeletedAtModel
from typing import Optional, List, TYPE_CHECKING, Any
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from database.models.users import Users
    from database.models.events import Events


class BaseMedia(SQLModel):
    name: str = Field(index=True, max_length=800, nullable=False)
    url: Optional[str] = Field(default=None, nullable=True)
    prefix: str = Field(default="", index=True)
    media_metadata: Optional[dict[str, Any]] = Field(default=None, sa_type=JSONB)
    parent_id: Optional[int] = Field(default=None, index=True, foreign_key="medias.id")
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
    id: int | None = Field(default=None, primary_key=True)
    parent: Optional["Medias"] = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "Medias.id"}
    )
    children: Optional[List["Medias"]] = Relationship(back_populates="parent")

    users: Optional[List["Users"]] = Relationship(back_populates="media")
    events: Optional[List["Events"]] = Relationship(back_populates="media")
