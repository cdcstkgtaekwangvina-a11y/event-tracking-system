from database.models.app_db import SessionDep
from database.models.queue_jobs import QueueJob
from src.shared.base.base_crud import BaseCrud
from src.shared.base.base_logger import get_logger

from .queue_job_schemas import CreateQueueJobSchema

logger = get_logger(__name__)


class QueueJobServices:
    """Service to manage QueueJob logs and progress tracking in the database."""

    def __init__(self, session: SessionDep):
        self.session = session
        self.crud = BaseCrud(session, QueueJob)

    async def create_job(self, create_job: CreateQueueJobSchema) -> QueueJob | None:
        """Creates a pending queue job record."""
        new_job = await self.crud.create(create_job)
        if not new_job:
            return None
        return new_job
