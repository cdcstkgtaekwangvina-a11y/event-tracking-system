from src.shared.base import BaseRequest, BaseRouter
from src.shared.helpers.cbv import clean_cbv
from fastapi import Depends
from src.modules.events.event_services import EventServices
from src.shared.middlewares.auth_middlewares import RequireAuth

TAG_NAME = "admin/events"
router = BaseRouter(
    controller=TAG_NAME,
    tags=[TAG_NAME],
    dependencies=[Depends(RequireAuth(is_required_auth=True))],
)
base_path = "modules/events/views/"


@clean_cbv(router)
class EventViews:
    def __init__(self, service: EventServices = Depends()):
        self.service = service

    @router.get(name="event_admin")
    def events(self, req: BaseRequest):
        return req.response_html(name=f"{base_path}index.j2")
