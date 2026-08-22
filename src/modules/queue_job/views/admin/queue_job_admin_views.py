from fastapi import Depends

from src.modules.queue_job.queue_job_services import QueueJobServices
from src.shared.base import BaseRequest, BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares.auth_middlewares import auth
from src.shared.schemas.pagination_schemas import FilterRequest, PaginationQuery

TAG_NAME = "admin/queue-jobs"
router = BaseRouter(
    controller=TAG_NAME,
    tags=[TAG_NAME],
    dependencies=[auth(is_required_auth=True)],
)
base_path = "modules/queue_job/views/admin/"


@clean_cbv(router)
class QueueJobAdminViews:
    def __init__(self, service: QueueJobServices = Depends()):
        self.service = service

    @router.get(name="queue_jobs")
    def queue_jobs(
        self,
        req: BaseRequest,
        status: str | None = None,
    ):
        is_hx_fragment = bool(req.headers.get("hx-request"))
        return req.response_html(
            name=f"{base_path}index.j2",
            context={
                "status_filter": status or "all",
            },
            cache_time=3600 if is_hx_fragment else 0,
        )

    @router.get("table/html", name="queue_jobs_table")
    async def queue_jobs_table_html(
        self,
        req: BaseRequest,
        pagination: PaginationQuery,
        status: str | None = None,
    ):
        if "limit" not in req.query_params:
            pagination.limit = 20

        if status and status != "all":
            if not pagination.filters:
                pagination.filters = []
            pagination.filters.append(FilterRequest(field="status", value=status))

        response = await self.service.get_jobs(pagination)
        pagination_data = response.data if response.status_code == 200 else None

        return req.response_html(
            name=f"{base_path}queue_job_table.j2",
            context={
                "jobs": pagination_data.data if pagination_data else [],
                "total": pagination_data.total_items if pagination_data else 0,
                "pagination": pagination,
                "status_filter": status or "all",
                "search": pagination.search or "",
            },
        )
