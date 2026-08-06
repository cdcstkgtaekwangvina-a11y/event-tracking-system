from __future__ import annotations
from fastapi import Depends, Response
from typing import Optional
from .auth_services import AuthenticationServices
from .auth_schemas import RegisterRequest, LoginRequest
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares.auth_middlewares import RequireAuth, AuthContext
from src.shared.base import BaseRequest, BaseRouter

TAG = "auth"
router = BaseRouter(controller=TAG, tags=[TAG])


@clean_cbv(router)
class AuthenticationController:
    def __init__(self, services: AuthenticationServices = Depends()):
        self.services = services

    @router.get("login", name="login_view", include_in_schema=False)
    def login_view(
        self,
        req: BaseRequest,
        redirect: Optional[str] = None,
        auth: AuthContext = Depends(RequireAuth(is_required_auth=False)),
    ):
        if auth.is_valid:
            return auth.redirect_with(redirect or "/")
        return req.response_html(
            name="modules/authentication/views/login.j2", context={"redirect": redirect}
        )

    @router.get("forgot-password", name="forgot_password_view", include_in_schema=False)
    def forgot_password_view(self, req: BaseRequest, redirect: Optional[str] = None):
        req.response_html(
            name="modules/authentication/views/forgot_password.j2",
            context={"redirect": redirect},
        )

    @router.post_api("register")
    async def register(
        self,
        req: RegisterRequest,
    ):
        return await self.services.register(req)

    @router.post_api("login")
    async def login(
        self,
        req: LoginRequest,
        response: Response,
    ):
        return await self.services.login(req, response)

    @router.post_api("logout")
    def logout(
        self,
        response: Response,
        auth: AuthContext = Depends(RequireAuth(is_required_auth=True)),
    ):
        return self.services.logout(response)
