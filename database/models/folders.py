from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel, DeletedAtModel
from typing import Optional, TYPE_CHECKING


class BaseFolders(SQLModel):
    name: str = Field(max_length=300)
    parent_id: int | None = Field(default=None, foreign_key="folders.id")
    __table_args__ = (
        UniqueConstraint("name", "parent_id", name="uq_folder_name_parent"),
    )


if TYPE_CHECKING:
    from database.models.files import Files


class Folders(
    BaseFolders,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__ = "folders"
    id: int | None = Field(default=None, primary_key=True)
    files: Optional[list[Files]] = Relationship(back_populates="folder")
    parent: Optional["Folders"] = Relationship(back_populates="children")
    children: Optional[list["Folders"]] = Relationship(back_populates="parent")
