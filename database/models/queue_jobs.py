from sqlmodel import SQLModel, Field
from .base_model import PrimaryModel, CreatedAtModel
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from typing import cast, Any
from uuid import UUID, uuid8
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseQueueJob(SQLModel):
    type: str = Field(max_length=30, nullable=False)
    status: str = Field(default=JobStatus.PENDING, max_length=30)
    finished_at: datetime | None = Field(
        default=None, sa_type=cast(Any, DateTime(timezone=True)), nullable=True
    )
    progress: int = Field(default=0, ge=0, le=100)
    meta: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    logs: list[dict] | None = Field(default=None, sa_type=JSONB)


class QueueJob(PrimaryModel, CreatedAtModel, BaseQueueJob):
    __tablename__: str = "queue_job"
    id: UUID = Field(default=uuid8(), primary_key=True)
