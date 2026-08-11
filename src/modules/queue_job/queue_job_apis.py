from fastapi import Depends

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
