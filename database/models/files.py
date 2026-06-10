# from __future__ import annotations
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint, BigInteger
from .base_model import PrimaryModel, CreatedAtModel, UpdatedAtModel, DeletedAtModel
from typing import Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from database.models.folders import Folders
    from database.models.events import Events
    from database.models.users import Users


class BaseFiles(SQLModel):
    name: str = Field(max_length=500, nullable=False, index=True)
    url: str = Field(nullable=False)
    type: str = Field(max_length=100, nullable=False)
    sizes: Optional[int] = Field(default=0, nullable=True, sa_type=BigInteger)
    folder_id: Optional[int] = Field(default=None, index=True, foreign_key="folders.id")
    __table_args__ = (
        UniqueConstraint("name", "folder_id", name="uq_file_name_folder"),
    )


class Files(
    BaseFiles,
    PrimaryModel[int],
    CreatedAtModel,
    UpdatedAtModel,
    DeletedAtModel,
    table=True,
):
    __tablename__: str = "files"
    id: int | None = Field(default=None, primary_key=True)
    folder: Optional["Folders"] = Relationship(back_populates="files")
    events: Optional[List["Events"]] = Relationship(back_populates="file")
    users: Optional[List["Users"]] = Relationship(back_populates="file")
