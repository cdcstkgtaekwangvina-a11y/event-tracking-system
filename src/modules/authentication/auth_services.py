from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from dotenv import load_dotenv
from fastapi import HTTPException, Response
from jwt import ExpiredSignatureError, InvalidTokenError, decode, encode
from pwdlib import PasswordHash
from sqlmodel import or_

from database.models.app_db import SessionDep
from src.modules.user.role_constants import ROLE
from src.modules.user.user_services import UserServiceDep
from src.shared.base.base_response import BaseResponse
from src.shared.constants.cache_tags import CacheTags

from .auth_schemas import (
    LoginRequest,
    NewPasswordRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenData,
    TokenResponse,
)
from .auth_select import LoginSelect

if TYPE_CHECKING:
    from database.models.users import Users

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
AUDIENCE = os.getenv("AUDIENCE")
ISSUER = os.getenv("ISSUER")

if not SECRET_KEY or not AUDIENCE or not ISSUER:
    raise HTTPException(status_code=500, detail="forgot environment auth service")


class AuthenticationServices:
    def __init__(self, session: SessionDep, user_services: UserServiceDep):

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
            {"id": str(user.id), "role": user.role, "token_version": user.token_version}
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

    def logout(self, response: Response) -> BaseResponse[None]:
        res = BaseResponse.no_content(message="Đăng xuất thành công")
        res.delete_cookie(
            key="access_token",
            httponly=True,
            samesite="lax",
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

    async def new_password(
        self, id: UUID, req: NewPasswordRequest
    ) -> BaseResponse[bool]:

        existing_user = await self.crud.find_by_id(id)
        if not existing_user:
            return BaseResponse.not_found(message="Không tìm thấy tài khoản")

        if not existing_user.is_active:
            return BaseResponse.forbidden(message="Tài khoản đã bị khóa")

        password_hash = PasswordHash.recommended()
        if not existing_user.password or not password_hash.verify(
            req.old_password, existing_user.password
        ):
            return BaseResponse.fail(message="Mật khẩu cũ không chính xác")

        dummy_hashh = password_hash.hash(req.new_password)
        existing_user.password = dummy_hashh
        existing_user.token_version += 1

        self.session.add(existing_user)
        await self.session.commit()
        await self.user_services.cache.remove_async(f"{CacheTags.USER}:{id}")
        return BaseResponse.ok(True)

    async def reset_password(self, req: ResetPasswordRequest) -> BaseResponse[bool]:
        from database.models.users import Users
        from src.shared.services.verify_auth_email import send_email_auth

        existing_user: Users | None = (
            await self.crud.select(Users).where(Users.email == req.email).find_one()
        )
        if existing_user is None:
            return BaseResponse.not_found("Không tìm thấy tài khoản")

        if not existing_user.is_active:
            return BaseResponse.forbidden("Tài khoản đã bị khóa")

        from src.shared.helpers.random_helpers import RandomHelpers

        new_pass = RandomHelpers(length=8).generate_password()
        password_hash = PasswordHash.recommended()
        existing_user.password = password_hash.hash(new_pass)
        existing_user.token_version += 1
        self.session.add(existing_user)

        sent = await send_email_auth.send_reset_password_email(
            to_email=existing_user.email,
            new_password=new_pass,
            user={"name": existing_user.name, "username": existing_user.username},
        )
        if not sent:
            return BaseResponse.error(message="Không thể gửi email đặt lại mật khẩu")

        await self.session.commit()
        from src.shared.constants.cache_tags import CacheTags
        await self.user_services.cache.remove_async(f"{CacheTags.USER}:{existing_user.id}")
        return BaseResponse.ok(True)
