from sqlmodel.ext.asyncio.session import AsyncSession
from database.models.events import Events
from .event_schemas import EventCreateRequest


class EventServices:
    session: AsyncSession
    #crud: BaseCrud
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(self, event: EventCreateRequest) -> Events:
        new_event = Events(**event.model_dump())
        self.session.add(new_event)
        await self.session.commit()
        await self.session.refresh(new_event)
        return new_event
