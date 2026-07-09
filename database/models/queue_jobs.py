from sqlmodel import SQLModel, Field
from .base_model import PrimaryModel, CreatedAtModel
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from typing import cast, Any
from uuid import UUID, uuid8
from enum import Enum
from src.shared.base.base_schema import BaseSchema


class JobStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueueJobLogs(BaseSchema):
    errors: list[dict[str, Any]] | None = []
    logs: list[dict[str, Any]] | None = []


class BaseQueueJob(SQLModel):
    type: str = Field(max_length=30, nullable=False)
    status: str = Field(default=JobStatus.RUNNING, max_length=30)
    finished_at: datetime | None = Field(
        default=None, sa_type=cast(Any, DateTime(timezone=True)), nullable=True
    )
    progress: int = Field(default=0, ge=0, le=100)
    meta: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    logs: QueueJobLogs | None = Field(default=None, sa_type=JSONB)
    next_payload: dict[str, Any] | None = Field(default=None, sa_type=JSONB)


class QueueJob(PrimaryModel[UUID], CreatedAtModel, BaseQueueJob, table=True):
    __tablename__: str = "queue_job"
    id: UUID = Field(default=uuid8(), primary_key=True)
