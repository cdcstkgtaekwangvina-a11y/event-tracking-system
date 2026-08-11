from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.shared.base.base_schema import BaseSchema


class QueueJobSelect(BaseSchema):
    id: UUID
    type: str
    status: str
    finished_at: datetime | None
    progress: int = Field(default=0, ge=0, le=100)
    created_at: datetime | None
