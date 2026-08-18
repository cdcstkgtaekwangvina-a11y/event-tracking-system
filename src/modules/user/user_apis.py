from src.shared.base.base_route import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from .user_schemas import ChangePasswordRequest, UpdateProfileRequest
from .user_services import UserServices
from fastapi import Depends, File, UploadFile
from src.shared.middlewares.auth_middlewares import RequireAuth, AuthContext
from src.shared.base.base_response import BaseResponse

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

    @router.post_api("profile/avatar", dependencies=[Depends(RequireAuth())])
    async def update_avatar(
        self,
        file: UploadFile = File(...),
        auth_context: AuthContext = Depends(RequireAuth()),
    ):
        if not auth_context.is_valid:
            return BaseResponse.unauthorized()

        return await self.services.update_avatar(id=auth_context.payload.id, file=file)

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
