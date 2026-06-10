from fastapi import Depends, UploadFile, File, Form
from typing import Optional
from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import (
    PaginationRequest,
    CursorPaginationRequest,
)
from .media_schemas import (
    FileCreate,
    FileUpdate,
    FolderCreate,
    FolderUpdate,
)
from .media_services import MediaServices

TAG_NAME = "media"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class MediaController:
    service: MediaServices = Depends()

    # FILES CRUD
    @router.post_api("files")
    async def create_file(
        self,
        file: UploadFile = File(...),
        folder_id: Optional[int] = Form(None),
    ):
        data = FileCreate(file=file, folder_id=folder_id)
        return await self.service.create_file(data)

    @router.get_api("files")
    async def list_files(self, q: PaginationRequest = Depends()):
        return await self.service.pagination_files(q)

    @router.get_api("files/{file_id}")
    async def get_file(self, file_id: int):
        return await self.service.read_one_file(file_id)

    @router.put_api("files/{file_id}")
    async def update_file(
        self,
        file_id: int,
        file: Optional[UploadFile] = File(None),
        name: Optional[str] = Form(None),
        folder_id: Optional[int] = Form(None),
    ):
        data = FileUpdate(file=file, name=name, folder_id=folder_id)
        return await self.service.update_file(file_id, data)

    @router.delete_api("files/{file_id}")
    async def delete_file(self, file_id: int):
        return await self.service.delete_file(file_id)

    # FOLDERS CRUD
    @router.post_api("folders")
    async def create_folder(self, data: FolderCreate):
        return await self.service.create_folder(data)

    @router.get_api("folders")
    async def list_folders(self, q: PaginationRequest = Depends()):
        return await self.service.pagination_folders(q)

    @router.get_api("folders/{folder_id}")
    async def get_folder(self, folder_id: int):
        return await self.service.read_one_folder(folder_id)

    @router.put_api("folders/{folder_id}")
    async def update_folder(self, folder_id: int, data: FolderUpdate):
        return await self.service.update_folder(folder_id, data)

    @router.delete_api("folders/{folder_id}")
    async def delete_folder(self, folder_id: int):
        return await self.service.delete_folder(folder_id)

    # FILE MANAGER - Cursor pagination (hỗn hợp file + folder như WordPress)
    @router.get_api("items")
    async def list_items_cursor(
        self,
        folder_id: Optional[int] = None,
        cursor_request: CursorPaginationRequest = Depends(),
    ):
        return await self.service.list_items_by_folder_cursor(folder_id, cursor_request)

    # FOLDER TREE - for sidebar navigation
    @router.get_api("folders/tree")
    async def get_folder_tree(
        self,
        parent_id: Optional[int] = None,
    ):
        return await self.service.get_folder_tree(parent_id)
