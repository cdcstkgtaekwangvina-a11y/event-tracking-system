from src.shared.base.base_route import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from .role_constants import ROLE
from .user_schemas import (
    ChangePasswordRequest,
    CreateAccountRequest,
    SetAvatarFromMediaRequest,
    UpdateAccountRequest,
    UpdateProfileRequest,
)
from .user_services import UserServices
from fastapi import Depends
from src.shared.middlewares.auth_middlewares import RequireAuth, AuthContext
from src.shared.base.base_response import BaseResponse
from src.shared.schemas.pagination_schemas import PaginationQuery

TAG = "User"
router = BaseRouter(tags=[TAG], controller=TAG)


@clean_cbv(router)
class UserApis:
    def __init__(self, services: UserServices = Depends()):
        self.services = services

    @router.get_api("profile", dependencies=[Depends(RequireAuth())])
    async def get_profile(self, auth_context: AuthContext = Depends(RequireAuth())):
        if not auth_context.is_valid:
            return BaseResponse.unauthorized()

        return BaseResponse.ok(auth_context.payload.user)

    @router.put_api("profile", dependencies=[Depends(RequireAuth())])
    async def update_profile(
        self,
        payload: UpdateProfileRequest,
        auth_context: AuthContext = Depends(RequireAuth()),
    ):
        if not auth_context.is_valid:
            return BaseResponse.unauthorized()

        return await self.services.update_profile(
            id=auth_context.payload.id,
            payload=payload,
            requester_role=auth_context.payload.role,
        )

    @router.put_api("profile/avatar/media", dependencies=[Depends(RequireAuth())])
    async def set_avatar_from_media(
        self,
        payload: SetAvatarFromMediaRequest,
        auth_context: AuthContext = Depends(RequireAuth()),
    ):
        if not auth_context.is_valid:
            return BaseResponse.unauthorized()

        return await self.services.set_avatar_from_media(
            id=auth_context.payload.id, media_id=payload.media_id
        )

    @router.put_api("profile/password", dependencies=[Depends(RequireAuth())])
    async def change_password(
        self,
        payload: ChangePasswordRequest,
        auth_context: AuthContext = Depends(RequireAuth()),
    ):
        if not auth_context.is_valid:
            return BaseResponse.unauthorized()

        return await self.services.change_password(
            id=auth_context.payload.id, payload=payload
        )


ACCOUNT_TAG = "Account"
account_router = BaseRouter(
    controller=ACCOUNT_TAG,
    tags=[ACCOUNT_TAG],
    dependencies=[Depends(RequireAuth(roles=[ROLE.ADMIN]))],
)


@clean_cbv(account_router)
class AccountApis:
    """Admin-facing account management (`/api/Account`) — ADMIN/SUPER_ADMIN
    only. Reuses `UserServices` (see its `list_accounts`/`create_account`/
    `update_account`) rather than a separate service class, since both this
    and the self-service `/api/User/profile` endpoints above operate on the
    same `Users` table."""

    def __init__(self, service: UserServices = Depends()):
        self.service = service

    @account_router.get_api()
    async def get_accounts(self, pagination: PaginationQuery):
        return await self.service.list_accounts(pagination)

    @account_router.post_api()
    async def create_account(self, payload: CreateAccountRequest):
        return await self.service.create_account(payload)

    @account_router.put_api("{account_id}")
    async def update_account(
        self,
        account_id: str,
        payload: UpdateAccountRequest,
        auth: AuthContext = Depends(RequireAuth(roles=[ROLE.ADMIN])),
    ):
        return await self.service.update_account(
            id=account_id, payload=payload, requester_role=auth.payload.role
        )
