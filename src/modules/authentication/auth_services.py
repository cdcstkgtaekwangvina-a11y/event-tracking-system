from fastapi import Response, HTTPException
from database.models.app_db import SessionDep, Depends
from typing import TYPE_CHECKING
from sqlmodel import or_
from src.modules.user.role_constants import ROLE
from .auth_schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    TokenData,
)
from .auth_select import LoginSelect
from pwdlib import PasswordHash
from datetime import timedelta, datetime, timezone
from jwt import decode, encode, InvalidTokenError, ExpiredSignatureError
from dotenv import load_dotenv
import os
from src.shared.base.base_response import BaseResponse
from src.modules.user.user_services import UserServices

if TYPE_CHECKING:
    from database.models.users import Users

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
AUDIENCE = os.getenv("AUDIENCE")
ISSUER = os.getenv("ISSUER")

if not SECRET_KEY or not AUDIENCE or not ISSUER:
    raise HTTPException(status_code=500, detail="forgot environment auth service")


class AuthenticationServices:
    def __init__(self, session: SessionDep, user_services: UserServices = Depends()):

        from database.models.users import Users
        from src.shared.base.base_crud import BaseCrud

        self.session = session
        self.crud = BaseCrud[Users](session, Users)
        self.user_services = user_services

    async def register(self, req: RegisterRequest) -> BaseResponse[Users]:
        from database.models.users import Users

        return await self.user_services.create_user(
            Users(**req.model_dump(), role=ROLE.COMMON)
        )

    def __create_token(
        self,
        data: dict,
        algorithm: str = "HS256",
        expires: datetime | None = None,
    ) -> TokenData:
        to_encode = data | {"aud": AUDIENCE, "iss": ISSUER}
        if expires is None:
            expires = datetime.now(timezone.utc) + timedelta(weeks=12)
        to_encode.update({"exp": expires})
        encoded_jwt: str = encode(to_encode, SECRET_KEY, algorithm=algorithm)
        return TokenData(access_token=encoded_jwt, exp=expires)

    async def login(
        self, req: LoginRequest, response: Response
    ) -> BaseResponse[TokenResponse]:
        from database.models.users import Users

        user = (
            await self.crud.select(LoginSelect)
            .where(
                or_(
                    Users.email == req.email_or_username,
                    Users.username == req.email_or_username,
                )
            )
            .find_one()
        )

        if user is None or not user:
            return BaseResponse.not_found(message="Tài khoản không tồn tại")

        if not user.is_active:
            return BaseResponse.fail(message="Tài khoản đã bị khóa", status_code=403)

        password_hash = PasswordHash.recommended()
        if not user.password or not password_hash.verify(req.password, user.password):
            return BaseResponse.fail(message="Mật khẩu không chính xác")

        res = BaseResponse.no_content(message="Đăng nhập thành công")
        token_data = self.__create_token(
            {"id": str(user.id), "role": user.role, "version": user.token_version}
        )

        res.set_cookie(
            key="access_token",
            value=token_data.access_token,
            httponly=True,
            expires=token_data.exp,
            samesite="lax",
            secure=False,
        )
        return res

    def verify_token(self, token: str, algorithm: str = "HS256") -> TokenData:
        if token.strip() == "":
            return TokenData(
                status_code=401,
                valid=False,
                access_token=token,
                message="Không có token",
            )
        try:
            payload = decode(
                token,
                SECRET_KEY,
                algorithms=[algorithm],
                audience=AUDIENCE,
                issuer=ISSUER,
            )
            data = TokenData(**payload, access_token=token)

            return data
        except ExpiredSignatureError:
            return TokenData(
                valid=False,
                status_code=401,
                access_token=token,
                message="Token đã hết hạn sử dụng",
            )
        except InvalidTokenError:
            return TokenData(
                valid=False,
                status_code=401,
                access_token=token,
                message="Token không hợp lệ",
            )
