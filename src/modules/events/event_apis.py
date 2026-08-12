from fastapi import Depends
from .event_schemas import AdminEventQuery, EventCreateRequest, EventUpdateRequest, PublicEventQuery
from .event_services import EventServices
from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import PaginationRequest
from src.shared.base.base_request import BaseRequest
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone

TAG_NAME = "events"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])
base_path = "modules/events/views/"


@clean_cbv(router)
class EventController:
    def __init__(self, service: EventServices = Depends()):
        self.service = service

    @router.post_api()
    async def create_event(self, event: EventCreateRequest):
        return await self.service.create_event(event)

    @router.get_api()
    async def get_events(self, q: PaginationRequest = Depends()):
        return await self.service.get_events(q)

    @router.get_api("cards-html", response_class=HTMLResponse)
    async def get_events_cards_html(
        self,
        req: BaseRequest,
        q: PublicEventQuery = Depends(),
    ):
        pagination_result = await self.service.get_public_events_raw(pagination=q)
        limit = pagination_result.limit
        total = pagination_result.total
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        templates = req.app.state.templates
        return templates.TemplateResponse(
            req,
            name=f"{base_path}event_cards.j2",
            context={
                "events": pagination_result.data or [],
                "page": pagination_result.page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "search": q.search or "",
                "status": q.status,
                "sort_field": q.sort_field,
                "is_desc": q.is_desc,
                "now": datetime.now(timezone.utc),
            },
        )

    @router.get_api("admin-cards-html", response_class=HTMLResponse)
    async def get_events_admin_cards_html(
        self,
        req: BaseRequest,
        q: AdminEventQuery = Depends(),
    ):
        pagination_result = await self.service.get_admin_events_raw(pagination=q)
        limit = pagination_result.limit
        total = pagination_result.total
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        templates = req.app.state.templates
        return templates.TemplateResponse(
            req,
            name=f"{base_path}admin_event_cards.j2",
            context={
                "events": pagination_result.data or [],
                "page": pagination_result.page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "search": q.search or "",
                "status": q.status,
                "sort_field": q.sort_field,
                "is_desc": q.is_desc,
                "now": datetime.now(timezone.utc),
            },
        )

    @router.get_api("{event_id}")
    async def get_event_by_id(self, event_id: int):
        return await self.service.get_event_by_id(event_id)

    @router.put_api("{event_id}")
    async def update_event(self, event_id: int, event: EventUpdateRequest):
        return await self.service.update_event(event_id, event)

    @router.delete_api("{event_id}")
    async def delete_event(self, event_id: int):
        return await self.service.delete_event(event_id)

    @router.post_api("{event_id}/register")
    async def register_event(self, event_id: int, employee_id: int):
        return await self.service.register_employee(event_id, employee_id)
