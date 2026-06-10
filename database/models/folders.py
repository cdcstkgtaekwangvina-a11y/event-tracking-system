from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel, DeletedAtModel
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.files import Files


class BaseFolders(SQLModel):
    name: str = Field(index=True, max_length=500, nullable=False)
    parent_id: int | None = Field(default=None, foreign_key="folders.id")
    __table_args__ = (
        UniqueConstraint("name", "parent_id", name="uq_folder_name_parent"),
    )


class Folders(
    BaseFolders,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__: str = "folders"
    id: int | None = Field(default=None, primary_key=True)
    files: Optional[List["Files"]] = Relationship(back_populates="folder")
    parent: Optional["Folders"] = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "Folders.id"}
    )
    children: Optional[List["Folders"]] = Relationship(back_populates="parent")
