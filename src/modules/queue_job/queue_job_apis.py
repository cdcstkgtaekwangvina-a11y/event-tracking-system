from fastapi import Depends

from src.modules.queue_job.queue_job_schemas import StopQueueJobSchema
from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import PaginationQuery

from .queue_job_services import QueueJobServices

TAG_NAME = "queue-jobs"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class QueueJobController:
    def __init__(self, service: QueueJobServices = Depends()):
        self.service = service

    @router.get_api()
    async def get_queue_jobs(self, query: PaginationQuery):
        return await self.service.get_jobs(query)

    @router.put_api("cancel-job")
    async def cancel_job(self, job: StopQueueJobSchema):
        return await self.service.cancel_job(job)
