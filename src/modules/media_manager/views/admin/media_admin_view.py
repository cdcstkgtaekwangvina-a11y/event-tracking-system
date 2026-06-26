from src.shared.base import BaseRequest, BaseRouter
from fastapi import Depends
from typing import Optional, cast
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
    CursorPaginationResponse,
)
from src.modules.media_manager.media_services import MediaServices
from src.shared.middlewares.auth_middlewares import RequireAuth

TAG_NAME = "admin/media"
router = BaseRouter(
    controller=TAG_NAME,
    tags=[TAG_NAME],
    dependencies=[Depends(RequireAuth(is_required_auth=True))],
)
base_path = "modules/media_manager/views/admin/"


@clean_cbv(router)
class MediaViews:
    def __init__(self, service: MediaServices = Depends()):
        self.service = service

    @router.get(name="media_manager")
    async def media_manager(self, req: BaseRequest, folder_id: Optional[int] = None):
        return req.response_html(
            name=f"{base_path}index.j2",
            context={
                "folder_id": folder_id,
            },
        )

    @router.get("items/html")
    async def list_items_html(
        self,
        req: BaseRequest,
        folder_id: Optional[int] = None,
        cursor_request: CursorPaginationRequest = Depends(),
        type_filter: Optional[str] = None,
    ):
        cursor_request = await self.apply_sort_request(cursor_request)
        result = await self.service.list_items_by_folder_cursor_raw(
            folder_id, cursor_request, type_filter=type_filter
        )

        return req.response_html(
            name=f"{base_path}items_grid.j2",
            context={
                **(result.model_dump(mode="json") if result else {}),
                "folder_id": folder_id,
                "cursor_request": cursor_request,
            },
        )

    async def apply_sort_request(
        self, request: CursorPaginationRequest
    ) -> CursorPaginationRequest:
        return request
