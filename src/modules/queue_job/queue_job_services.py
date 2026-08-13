from uuid import UUID

from sqlmodel import and_, col
from uuid6 import uuid8

from database.models.app_db import SessionDep
from database.models.queue_jobs import JobStatus, QueueJob
from src.shared.base.base_crud import BaseCrud
from src.shared.base.base_logger import get_logger
from src.shared.base.base_response import BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from src.shared.services.redis_services import RedisDep

from .queue_job_schemas import CreateQueueJobSchema, QueueJobSchema, StopQueueJobSchema

logger = get_logger(__name__)


class QueueJobServices:
    """Service to manage QueueJob logs and progress tracking in the database."""

    def __init__(self, session: SessionDep, redis: RedisDep):
        self.session = session
        self.crud = BaseCrud(session, QueueJob)
        self.redis = redis

    async def get_jobs(
        self, pagination: PaginationRequest
    ) -> BaseResponse[PaginationResponse]:
        cache_key = self.redis.get_pagination_key(CacheTags.QUEUE_JOB, pagination)

        result = await self.redis.get_or_set_async(
            key=cache_key,
            async_func=lambda: self.crud.pagination_async(
                pagination, search_fields=["id"]
            ),
            tags=[CacheTags.QUEUE_JOB],
            model_class=PaginationResponse,
        )
        return BaseResponse.ok(result, message="Lấy danh sách job thành công")

    async def get_job(self, id: UUID) -> BaseResponse[QueueJobSchema]:
        cache_key = f"{CacheTags.QUEUE_JOB}:{id}"

        async def get_job_async() -> QueueJobSchema | None:
            result = (
                await self.crud.select(QueueJobSchema)
                .where(QueueJob.id == id)
                .find_one()
            )
            if not result:
                return None

            return QueueJobSchema.model_validate(result, from_attributes=True)

        result = await self.redis.get_or_set_async(
            key=cache_key,
            async_func=get_job_async,
            tags=[CacheTags.QUEUE_JOB],
            model_class=QueueJobSchema,
        )
        if not result:
            return BaseResponse.not_found(message="Không tìm thấy job")
        return BaseResponse.ok(result, message="Lấy job thành công")

    async def create_job(self, create_job: CreateQueueJobSchema) -> QueueJob | None:
        """Creates a pending queue job record."""
        new_job = await self.crud.create(
            QueueJob(id=uuid8(), **create_job.model_dump())
        )
        if not new_job:
            return None
        return new_job

    async def cancel_job(self, jobs: StopQueueJobSchema) -> BaseResponse[None]:
        exiting_jobs = (
            await self.crud.select(QueueJob)
            .where(
                and_(
                    col(QueueJob.status) == JobStatus.RUNNING.value,
                    col(QueueJob.id) == jobs.id,
                )
            )
            .find_one()
        )
        if not exiting_jobs:
            return BaseResponse.not_found(message="Không tìm thấy job")

        from src.shared.base.base_queue import queue_service
        from src.shared.helpers.time_extensions import get_vn_time

        async with self.crud.transaction():
            exiting_jobs.status = JobStatus.CANCELLED.value
            exiting_jobs.finished_at = get_vn_time()
            self.session.add(exiting_jobs)
            canceled = queue_service.cancel_job(str(exiting_jobs.id))

            if not canceled:
                return BaseResponse.error("Có lỗi xảy ra khi hủy tác vụ")

            await self.session.commit()
        await self.redis.invalidate_tags_async([CacheTags.QUEUE_JOB.value])
        return BaseResponse.ok()
