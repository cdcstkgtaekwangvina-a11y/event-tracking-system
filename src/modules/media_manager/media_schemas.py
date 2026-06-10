from fastapi import UploadFile
from src.shared.base.base_schema import BaseSchema
from typing import Optional, Literal, List
from pydantic import Field
from datetime import datetime


class CreateFileSchema(BaseSchema):
    file: UploadFile


class FileCreate(BaseSchema):
    file: UploadFile
    folder_id: Optional[int] = None


class FileUpdate(BaseSchema):
    file: Optional[UploadFile] = None
    name: Optional[str] = None
    folder_id: Optional[int] = None


class FolderCreate(BaseSchema):
    name: str = Field(max_length=300)
    parent_id: Optional[int] = None


class FolderUpdate(BaseSchema):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class FolderCursorNode(BaseSchema):
    type: Literal["folder"] = "folder"
    id: int
    name: str
    parent_id: Optional[int]
    updated_at: Optional[datetime]


class FileCursorNode(BaseSchema):
    type: Literal["file"] = "file"
    id: int
    name: str
    url: str
    file_type: str
    sizes: Optional[int]
    folder_id: Optional[int]
    updated_at: Optional[datetime]


CursorNode = FolderCursorNode | FileCursorNode


class FolderTreeNode(BaseSchema):
    id: int
    name: str
    parent_id: Optional[int]
    children: List["FolderTreeNode"] = []
    item_count: int = 0

    class Config:
        from_attributes = True


FolderTreeNode.model_rebuild()
