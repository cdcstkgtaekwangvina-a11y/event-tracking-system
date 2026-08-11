from src.shared.base.base_route import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from .user_services import UserServices
from fastapi import Depends
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
