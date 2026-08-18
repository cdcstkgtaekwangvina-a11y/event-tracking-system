from fastapi import Depends

from src.modules.user.role_constants import ROLE
from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares.auth_middlewares import AuthContext, RequireAuth
from src.shared.schemas.pagination_schemas import PaginationQuery

from .account_schemas import CreateAccountRequest, UpdateAccountRequest
from .account_services import AccountServices

TAG_NAME = "Account"
router = BaseRouter(
    controller=TAG_NAME,
    tags=[TAG_NAME],
    dependencies=[Depends(RequireAuth(roles=[ROLE.ADMIN]))],
)


@clean_cbv(router)
class AccountController:
    def __init__(self, service: AccountServices = Depends()):
        self.service = service

    @router.get_api()
    async def get_accounts(self, pagination: PaginationQuery):
        return await self.service.list_accounts(pagination)

    @router.post_api()
    async def create_account(self, payload: CreateAccountRequest):
        return await self.service.create_account(payload)

    @router.put_api("{account_id}")
    async def update_account(
        self,
        account_id: str,
        payload: UpdateAccountRequest,
        auth: AuthContext = Depends(RequireAuth(roles=[ROLE.ADMIN])),
    ):
        return await self.service.update_account(
            id=account_id, payload=payload, requester_role=auth.payload.role
        )
