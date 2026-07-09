import logging
from uuid import UUID
from database.models.app_db import SessionDep
from database.models.queue_jobs import QueueJob, JobStatus, QueueJobLogs
from src.shared.helpers.time_extensions import get_now_vn
from typing import Optional, Any

logger = logging.getLogger(__name__)


class QueueJobServices:
    """Service to manage QueueJob logs and progress tracking in the database."""

    def __init__(self, session: SessionDep):
        self.session = session

    async def create_job(self, job_type: str, data: Any, job_id: UUID) -> QueueJob:
        """Creates a pending queue job record."""
        db_job = QueueJob(
            id=job_id,
            type=job_type,
            status=JobStatus.PENDING,
            progress=0,
            meta={"data": data, "total_records": len(data)},
            logs=QueueJobLogs(
                logs=[
                    {
                        "time": get_now_vn().isoformat(),
                        "message": f"Job enqueued with {len(data)} records.",
                    }
                ]
            ),
        )
        self.session.add(db_job)
        await self.session.commit()
        return db_job

    async def update_job(
        self,
        job_id: UUID,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        log_message: Optional[str] = None,
        log_error: Optional[str] = None,
        finished: bool = False,
    ) -> QueueJob | None:
        """Updates an existing queue job's status, progress, finished time, and appends logs."""
        db_job = await self.session.get(QueueJob, job_id)
        if not db_job:
            return None

        if status:
            db_job.status = status
        if progress is not None:
            db_job.progress = progress
        if finished:
            db_job.finished_at = get_now_vn()

        if db_job.logs is None:
            db_job.logs = QueueJobLogs(logs=[], errors=[])

        if log_message:
            db_job.logs.logs.append(
                {"time": get_now_vn().isoformat(), "message": log_message}
            )
        if log_error:
            db_job.logs.errors.append(
                {"time": get_now_vn().isoformat(), "error": log_error}
            )

        self.session.add(db_job)
        await self.session.commit()
        return db_job
