from fastapi import Depends

from src.modules.account.account_services import AccountServices
from src.modules.user.role_constants import ROLE
from src.shared.base import BaseRequest, BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares.auth_middlewares import AuthContext, RequireAuth
from src.shared.schemas.pagination_schemas import PaginationQuery

TAG_NAME = "admin/account"
router = BaseRouter(
    controller=TAG_NAME,
    tags=[TAG_NAME],
    dependencies=[Depends(RequireAuth(roles=[ROLE.ADMIN]))],
)
base_path = "modules/account/views/admin/"


@clean_cbv(router)
class AccountAdminViews:
    def __init__(self, service: AccountServices = Depends()):
        self.service = service

    @router.get(name="accounts")
    async def accounts(
        self,
        req: BaseRequest,
        pagination: PaginationQuery,
        auth: AuthContext = Depends(RequireAuth(roles=[ROLE.ADMIN])),
    ):
        if "limit" not in req.query_params:
            pagination.limit = 20
        pagination_data = await self.service.list_accounts_raw(pagination)
        return req.response_html(
            name=f"{base_path}index.j2",
            context={
                "accounts": pagination_data.data if pagination_data else [],
                "total": pagination_data.total_items if pagination_data else 0,
                "pagination": pagination,
                "search": pagination.search or "",
                "can_edit_email": auth.payload.role == ROLE.SUPER_ADMIN,
            },
        )

    @router.get("table/html", name="accounts_table")
    async def accounts_table_html(
        self,
        req: BaseRequest,
        pagination: PaginationQuery,
        auth: AuthContext = Depends(RequireAuth(roles=[ROLE.ADMIN])),
    ):
        if "limit" not in req.query_params:
            pagination.limit = 20
        pagination_data = await self.service.list_accounts_raw(pagination)
        return req.response_html(
            name=f"{base_path}account_table.j2",
            context={
                "accounts": pagination_data.data if pagination_data else [],
                "total": pagination_data.total_items if pagination_data else 0,
                "pagination": pagination,
                "search": pagination.search or "",
                "can_edit_email": auth.payload.role == ROLE.SUPER_ADMIN,
            },
        )
