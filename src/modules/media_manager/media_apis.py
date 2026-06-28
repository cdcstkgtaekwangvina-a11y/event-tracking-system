from fastapi import Depends
from typing import Optional
from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
)
from .media_schemas import (
    CreateMediaSchema,
)
from .media_services import MediaServices

TAG_NAME = "media"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class MediaController:
    def __init__(self, service: MediaServices = Depends()):
        self.service = service

    @router.get_api()
    async def list_items(
        self,
        parent_id: Optional[int] = None,
        q: CursorPaginationRequest = Depends(),
        type_filter: Optional[str] = None,
    ):
        return await self.service.list_items_by_folder_cursor(
            parent_id, q, type_filter=type_filter
        )

    @router.get_api("{id}")
    async def get_media(self, id: int):
        return await self.service.get_one_media(id)

    @router.post_api()
    async def create_media(
        self, payload: CreateMediaSchema = Depends(CreateMediaSchema.as_form)
    ):
        return await self.service.create_media(payload)

    @router.delete_api("{id}")
    async def delete_media(self, id: int, is_soft_delete: bool = True):
        return await self.service.delete_media(id, is_soft_delete)
