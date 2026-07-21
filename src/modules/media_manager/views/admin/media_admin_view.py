from src.shared.base import BaseRequest, BaseRouter
from fastapi import Depends
from typing import Optional
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
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
                "deleted_media": False,
            },
        )

    @router.get("items/html", name="media_grid")
    async def list_items_html(
        self,
        req: BaseRequest,
        folder_id: Optional[int] = None,
        deleted_media: bool = False,
        picker: bool = False,
        cursor_request: CursorPaginationRequest = Depends(),
        type_filter: Optional[str] = None,
    ):
        cursor_request = await self.apply_sort_request(cursor_request)
        result = await self.service.list_items_by_folder_cursor_raw(
            folder_id,
            cursor_request,
            deleted_media=deleted_media,
            type_filter=type_filter,
        )

        return req.response_html(
            name=f"{base_path}items_grid.j2",
            context={
                **(result.model_dump(mode="json") if result else {}),
                "folder_id": folder_id,
                "cursor_request": cursor_request,
                "deleted_media": deleted_media,
                "picker_mode": picker,
                "query_params": dict(req.query_params),
            },
        )

    @router.get("trash/html", name="trash")
    async def trash_view(
        self,
        req: BaseRequest,
        folder_id: Optional[int] = None,
    ):
        return req.response_html(
            name=f"{base_path}trash.j2",
            context={
                "folder_id": folder_id,
                "deleted_media": True,
            },
        )

    async def apply_sort_request(
        self, request: CursorPaginationRequest
    ) -> CursorPaginationRequest:
        return request
