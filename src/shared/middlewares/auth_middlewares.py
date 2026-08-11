from typing import Optional, Sequence

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.modules.authentication.auth_schemas import TokenData
from src.modules.authentication.auth_services import AuthenticationServices


class AuthContext:
    payload: TokenData
    is_valid: bool

    def __init__(self, payload: TokenData, is_valid: bool):
        self.payload = payload
        self.is_valid = is_valid

    @staticmethod
    def redirect_with(url: str):
        return RedirectResponse(url=url, status_code=302)

    def is_has_roles(self, roles: Sequence[str]) -> bool:
        if not self.is_valid:
            return False

        if len(roles) > 0 and not self.payload:
            return False
        return self.payload.role in roles


class RequireAuth:
    def __init__(
        self, roles: Optional[Sequence[str]] = None, is_required_auth: bool = True
    ):
        self.roles = roles
        self.is_required_auth = is_required_auth

    async def __call__(
        self, req: Request, service: AuthenticationServices = Depends()
    ) -> AuthContext:
        access_token = None

        auth_header = req.headers.get("Authorization")

        if auth_header and auth_header.lower().startswith("bearer "):
            parts = auth_header.split(" ")
            if len(parts) == 2:
                access_token = parts[1]
        if not access_token:
            access_token = req.cookies.get("access_token")

        def raise_or_set_error(status_code: int, message: str):
            if self.is_required_auth:
                if req.url.path.startswith("/api"):
                    raise HTTPException(status_code=status_code, detail=message)
                raise HTTPException(status_code=404, detail=message)

            payload.valid = False
            payload.message = message
            payload.status_code = status_code

        # 1. Kiểm tra nếu thiếu token khi bắt buộc phải auth
        if self.is_required_auth and not access_token:
            raise_or_set_error(401, "Vui lòng đăng nhập")

        payload = service.verify_token(access_token or "")

        if payload.valid is False:
            raise_or_set_error(payload.status_code or 401, payload.message or "")
            return AuthContext(payload=payload, is_valid=False)

        # 2. Kiểm tra User tồn tại
        payload.user = await service.user_services.get_raw_user(payload.id or "")
        if not payload.user:
            raise_or_set_error(401, "User không tồn tại")
            return AuthContext(payload=payload, is_valid=False)

        # 3. Kiểm tra Token Version
        if payload.user.token_version != payload.token_version:
            raise_or_set_error(401, "Token không hợp lệ")
            return AuthContext(payload=payload, is_valid=False)

        if self.roles:
            from src.modules.user.role_constants import ROLE

            if payload.role not in self.roles and payload.role != ROLE.SUPER_ADMIN:
                raise_or_set_error(404, "Không có quyền truy cập")
                if self.is_required_auth:
                    return AuthContext(payload=payload, is_valid=False)

        req.state.user = payload.user
        req.state.is_authenticated = payload.valid

        return AuthContext(payload=payload, is_valid=payload.valid)


def auth(roles: list[str] = None, is_required_auth: bool = True):
    return Depends(RequireAuth(roles=roles, is_required_auth=is_required_auth))
