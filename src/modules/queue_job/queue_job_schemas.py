from typing import Any

from pydantic import Field

from database.models.queue_jobs import QueueJobLogs
from src.shared.base.base_schema import BaseSchema


class CreateQueueJobSchema(BaseSchema):
    type: str = Field(max_length=30)
    progress: int = Field(default=0, ge=0, le=100)
    meta: dict[str, Any] | None = Field(default=None)
    logs: QueueJobLogs | None = Field(default=None)
    next_payload: dict[str, Any] | None = Field(default=None)
