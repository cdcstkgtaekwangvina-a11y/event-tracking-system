from database.models.events import BaseEvents
from typing import Optional
from datetime import datetime
from src.shared.base.base_schema import BaseSchema


class EventCreateRequest(BaseEvents):
    pass


class EventUpdateRequest(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    url_image: Optional[str] = None
    url_map: Optional[str] = None


class EventsSchema(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    url_image: Optional[str] = None
    url_map: Optional[str] = None
    employee_count: int = 0
