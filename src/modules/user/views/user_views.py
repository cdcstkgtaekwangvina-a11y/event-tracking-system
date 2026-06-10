from src.shared.base.base_route import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from ..user_services import UserServices
from fastapi import Depends
from src.shared.middlewares.auth_middlewares import RequireAuth, AuthContext
from src.shared.base.base_request import BaseRequest

TAG = "user"
router = BaseRouter(tags=[TAG], controller=TAG)
base_path = "modules/user/views/"


@clean_cbv(router)
class UserViews:
    def __init__(self, services: UserServices = Depends()):
        self.services = services

    @router.get(
        "me",
        include_in_schema=False,
        name="me",
    )
    def user(
        self,
        req: BaseRequest,
        auth: AuthContext = Depends(RequireAuth(is_required_auth=True)),
    ):
        if not auth.is_valid:
            return auth.redirect_with(url=str(req.url))
        return req.response_html(
            name=f"{base_path}me.j2", context={"user": auth.payload.user}
        )
