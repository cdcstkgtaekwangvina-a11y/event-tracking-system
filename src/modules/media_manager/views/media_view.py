from src.shared.base import BaseRequest, BaseRouter
from fastapi import Depends
from typing import Optional
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import (
    CursorPaginationRequest,
)
from ..media_services import MediaServices

TAG_NAME = "admin/media"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])
base_path = "modules/media_manager/views/"


@clean_cbv(router)
class MediaViews:
    service: MediaServices = Depends()

    @router.get(name="media_manager")
    def media_manager(self, req: BaseRequest):
        templates = req.app.state.templates
        return templates.TemplateResponse(req, name=f"{base_path}index.j2")

    @router.get("items/html")
    async def list_items_html(
        self,
        req: BaseRequest,
        folder_id: Optional[int] = None,
        cursor_request: CursorPaginationRequest = Depends(),
    ):
        result = await self.service.list_items_by_folder_cursor(
            folder_id, cursor_request
        )
        templates = req.app.state.templates
        items = result.data.data if result.data and result.data.data else []
        next_cursor = result.data.next_cursor if result.data else None
        has_more = result.data.has_more if result.data else False

        return templates.TemplateResponse(
            req,
            name=f"{base_path}items_grid.j2",
            context={
                "items": items,
                "folder_id": folder_id,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "is_desc": cursor_request.is_desc,
            },
        )
