from __future__ import annotations

from fastapi import Depends, HTTPException, Response

from src.shared.base import BaseRequest, BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares import rate_limit
from src.shared.middlewares.auth_middlewares import AuthContext, auth

from .auth_schemas import (
    LoginRequest,
    NewPasswordRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from .auth_services import AuthenticationServices

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
        redirect: str | None = None,
        auth: AuthContext = auth(is_required_auth=False),
    ):
        if auth.is_valid:
            target = redirect or "/"
            lower = target.lower()
            if any(
                bad in lower
                for bad in ["404", "error", "/auth/login", "/auth/register"]
            ):
                target = "/"
            return auth.redirect_with(target)
        return req.response_html(
            name="modules/authentication/views/login.j2",
            cache_time=3600,
            context={"redirect": redirect},
        )

    @router.get("forgot-password", name="forgot_password_view", include_in_schema=False)
    def forgot_password_view(self, req: BaseRequest, redirect: str | None = None):
        return req.response_html(
            name="modules/authentication/views/forgot_password.j2",
            cache_time=3600,
            context={"redirect": redirect},
        )

    @router.post_api(
        "register", dependencies=[rate_limit(request_per_windows=5, windows_time=300)]
    )
    async def register(
        self,
        req: RegisterRequest,
    ):
        return await self.services.register(req)

    @router.post_api(
        "login", dependencies=[rate_limit(request_per_windows=5, windows_time=300)]
    )
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
        auth: AuthContext = auth(is_required_auth=True),
    ):
        return self.services.logout(response)

    @router.put_api("new-password")
    async def new_password(
        self,
        req: NewPasswordRequest,
        auth: AuthContext = auth(is_required_auth=True),
    ):
        if not auth.is_valid or auth.payload is None or auth.payload.id is None:
            raise HTTPException(status_code=401)

        return await self.services.new_password(auth.payload.id, req)

    @router.post_api("reset-password")
    async def reset_password(self, req: ResetPasswordRequest):
        return await self.services.reset_password(req)
