from fastapi import APIRouter, Depends, Request
from database.models.app_db import SessionDep
from .event_schemas import EventCreateRequest
from database.models.events import Events
from .event_services import EventServices
from fastapi.responses import HTMLResponse, JSONResponse

TAG_NAME = "events"
router = APIRouter(tags=[TAG_NAME])
controller = f"/{TAG_NAME}"
api = f"/api/{TAG_NAME}"
base_path = "modules/events/views/"


def get_event_service(session: SessionDep) -> EventServices:
    return EventServices(session)


@router.get(f"{controller}", response_class=HTMLResponse)
def events(req: Request):
    templates = req.app.state.templates
    return templates.TemplateResponse(req, name=f"{base_path}index.j2")


@router.post(f"{api}", response_class=JSONResponse)
async def create_event(
    event: EventCreateRequest, services: EventServices = Depends(get_event_service)
) -> Events:
    return await services.create_event(event)
