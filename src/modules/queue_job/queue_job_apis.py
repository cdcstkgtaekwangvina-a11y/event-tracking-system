from fastapi import Depends

from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import FilterRequest, PaginationQuery

from .queue_job_services import QueueJobServices

TAG_NAME = "queue-jobs"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class QueueJobController:
    def __init__(self, service: QueueJobServices = Depends()):
        self.service = service

    @router.get_api()
    async def get_queue_jobs(self, query: PaginationQuery, status: str | None = None):
        if status:
            query.filters.append(FilterRequest(field="status", value=status))
        return await self.service.get_jobs(query)

    @router.get_api("{job_id}")
    async def get_queue_job(self, job_id: str):
        from uuid import UUID

        return await self.service.get_job(UUID(job_id))
