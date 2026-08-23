from fastapi import Depends

from src.modules.events.event_services import EventServices
from src.shared.base import BaseRequest, BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares.auth_middlewares import AuthContext, RequireAuth

base_path = "modules/events/views/"

admin_router = BaseRouter(
    controller="admin/events",
    tags=["admin/events"],
    dependencies=[Depends(RequireAuth(is_required_auth=True))],
)

public_router = BaseRouter(
    controller="events",
    tags=["events"],
)


@clean_cbv(admin_router)
class AdminEventViews:
    def __init__(self, service: EventServices = Depends()):
        self.service = service

    @admin_router.get(name="event_admin")
    def events(self, req: BaseRequest):
        return req.response_html(name=f"{base_path}index.j2", cache_time=3600)

    @admin_router.get("{event_id}", name="admin_event_detail")
    def admin_event_detail(self, req: BaseRequest, event_id: int):
        return req.response_html(
            name=f"{base_path}admin_event_detail.j2",
            context={"event_id": event_id},
            cache_time=3600,
        )


@clean_cbv(public_router)
class PublicEventViews:
    def __init__(self, service: EventServices = Depends()):
        self.service = service

    @public_router.get("{event_id}", name="public_event_detail")
    def public_event_detail(
        self,
        req: BaseRequest,
        event_id: int,
        auth: AuthContext = Depends(RequireAuth(is_required_auth=False)),
    ):
        return req.response_html(
            name=f"{base_path}public_event_detail.j2",
            context={"event_id": event_id},
            cache_time=3600,
        )
