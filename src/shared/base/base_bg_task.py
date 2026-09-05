from operator import and_
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database.models.queue_jobs import JobStatus, QueueJob


class BaseBackgroundTask:
    async def get_job(self, session: AsyncSession, job_id: UUID) -> QueueJob | None:
        query_job = await session.exec(
            select(QueueJob).where(
                and_(
                    QueueJob.id == job_id,
                    QueueJob.status == JobStatus.RUNNING.value,
                )
            )
        )
        return query_job.first()
