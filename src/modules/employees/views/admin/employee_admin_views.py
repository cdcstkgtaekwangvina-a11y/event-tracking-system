from fastapi import Depends

from src.modules.employees.employee_services import EmployeeServices
from src.shared.base import BaseRequest, BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares.auth_middlewares import RequireAuth
from src.shared.schemas.pagination_schemas import PaginationQuery

TAG_NAME = "admin/employees"
router = BaseRouter(
    controller=TAG_NAME,
    tags=[TAG_NAME],
    dependencies=[Depends(RequireAuth(is_required_auth=True))],
)
base_path = "modules/employees/views/admin/"


@clean_cbv(router)
class EmployeeAdminViews:
    def __init__(self, service: EmployeeServices = Depends()):
        self.service = service

    @router.get(name="employees")
    def employees(self, req: BaseRequest):
        is_hx_fragment = bool(req.headers.get("hx-request"))
        return req.response_html(
            name=f"{base_path}index.j2",
            cache_time=3600 if is_hx_fragment else 0,
        )

    @router.get("table/html", name="employees_table")
    async def employees_table_html(
        self,
        req: BaseRequest,
        pagination: PaginationQuery,
    ):
        if "limit" not in req.query_params:
            pagination.limit = 20
        pagination_data = await self.service.get_employees_raw(pagination)
        return req.response_html(
            name=f"{base_path}employee_table.j2",
            context={
                "employees": pagination_data.data if pagination_data else [],
                "total": pagination_data.total_items if pagination_data else 0,
                "pagination": pagination,
                "search": pagination.search or "",
            },
        )
