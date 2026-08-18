from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import UUID

from fastapi import UploadFile
from pwdlib import PasswordHash
from uuid6 import uuid8

from database.models.app_db import SessionDep
from database.models.media import Medias
from src.modules.user.role_constants import ROLE
from src.shared.base import BaseCrud, BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.helpers import RandomHelpers, get_vn_time
from src.shared.services.redis_services import RedisDep
from src.shared.services.vercel_blob import VercelBlobDep

from .user_schemas import ChangePasswordRequest, UpdateProfileRequest
from .user_select import UserSelect

if TYPE_CHECKING:
    from database.models.users import Users

AVATAR_ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg"}
AVATAR_MAX_SIZE_BYTES = 5 * 1024 * 1024


class UserServices:
    def __init__(self, session: SessionDep, cache: RedisDep, vercel_blob: VercelBlobDep):
        self.session = session
        self.cache = cache
        self.vercel_blob = vercel_blob
        from database.models.users import Users

        self.crud = BaseCrud[Users](session, Users)

    async def get_raw_user(self, id: UUID | str) -> UserSelect | None:
        cache_key = f"{CacheTags.USER}:{id}"
        from database.models.users import Users

        return cast(
            UserSelect | None,
            await self.cache.get_or_set_async(
                cache_key,
                async_func=lambda: (
                    self.crud.select(
                        UserSelect,
                        logic_column=[UserSelect.nameof(lambda x: x.file_id)],
                    )
                    .join(Medias, isouter=True)
                    .group_by(Users.id)
                    .find_by_id(id)
                ),
                tags=[CacheTags.USER],
                model_class=UserSelect,
            ),
        )

    async def get_user(self, id: UUID | str) -> BaseResponse[UserSelect]:
        user = await self.get_raw_user(id)

        if not user:
            return BaseResponse.fail("Không tìm thấy thông tin người dùng", 404)

        return BaseResponse.ok(user)

    async def create_user_or_fail(
        self, req: Users, withVerifyEmail: bool = False
    ) -> Users:
        """Creates a user and returns the raw model (`BaseResponse.fail` raises on
        a duplicate email/username). Shared by `create_user` (register/API response)
        and `AccountServices.create_account`, which needs the raw model rather than
        an already-rendered JSON response so it can project into `AccountSelect`."""
        from database.models.users import Users

        if not req.username:
            req.username = req.email

        email_exists = (
            await self.crud.select(Users).where(Users.email == req.email).any_async()
        )
        if email_exists:
            return BaseResponse.fail(message="Email đã tồn tại", status_code=400)

        username_exists = (
            await self.crud.select(Users)
            .where(Users.username == req.username)
            .any_async()
        )
        if username_exists:
            return BaseResponse.fail(message="Username đã tồn tại", status_code=400)

        dump_req = req.model_dump()
        if withVerifyEmail:
            dump_req["otp_code"] = RandomHelpers.generate_random_number_string(
                override_length=6
            )
            dump_req["expired_at"] = get_vn_time(secs=600)
        if req.password:
            password_hash = PasswordHash.recommended()
            dummy_hashh = password_hash.hash(req.password)
            dump_req["password"] = dummy_hashh

        new_user = await self.crud.create(Users(**dump_req))
        await self.cache.invalidate_tags_async(CacheTags.USER)
        return new_user

    async def create_user(
        self, req: Users, withVerifyEmail: bool = False
    ) -> BaseResponse[Users]:
        new_user = await self.create_user_or_fail(req, withVerifyEmail)
        return BaseResponse.created(new_user)

    async def update_profile(
        self,
        id: UUID | str,
        payload: UpdateProfileRequest,
        requester_role: str | None,
    ) -> BaseResponse[UserSelect]:
        from database.models.users import Users

        if payload.email is not None and requester_role != ROLE.SUPER_ADMIN:
            return BaseResponse.fail(
                message="Chỉ Super Admin mới có quyền chỉnh sửa Email",
                status_code=403,
            )

        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return BaseResponse.fail(
                message="Không có dữ liệu để cập nhật", status_code=400
            )

        if "username" in update_data:
            username_exists = (
                await self.crud.select(Users)
                .where(Users.username == update_data["username"], Users.id != id)
                .any_async()
            )
            if username_exists:
                return BaseResponse.fail(message="Username đã tồn tại", status_code=400)

        if "email" in update_data:
            email_exists = (
                await self.crud.select(Users)
                .where(Users.email == update_data["email"], Users.id != id)
                .any_async()
            )
            if email_exists:
                return BaseResponse.fail(message="Email đã tồn tại", status_code=400)

        updated = await self.crud.update(id=id, data=update_data)
        if not updated:
            return BaseResponse.fail(
                message="Không tìm thấy người dùng", status_code=404
            )

        await self.cache.invalidate_tags_async(CacheTags.USER)
        user = await self.get_raw_user(id)
        return BaseResponse.ok(user, message="Cập nhật thông tin thành công")

    async def update_avatar(
        self, id: UUID | str, file: UploadFile
    ) -> BaseResponse[UserSelect]:
        if file.content_type not in AVATAR_ALLOWED_CONTENT_TYPES:
            return BaseResponse.fail(
                message="Chỉ chấp nhận file ảnh định dạng PNG hoặc JPG/JPEG",
                status_code=400,
            )

        if file.size and file.size > AVATAR_MAX_SIZE_BYTES:
            return BaseResponse.fail(
                message="Kích thước ảnh đại diện không được vượt quá 5MB",
                status_code=400,
            )

        unique_filename = f"avatar_{uuid8()}_{file.filename or 'avatar'}"
        upload_result = await self.vercel_blob.put_async(
            file=file, override_name=unique_filename, folder="avatars/"
        )
        if not upload_result or not upload_result.url:
            return BaseResponse.error(message="Upload ảnh đại diện thất bại")

        updated = await self.crud.update(id=id, data={"avatar_url": upload_result.url})
        if not updated:
            return BaseResponse.fail(
                message="Không tìm thấy người dùng", status_code=404
            )

        await self.cache.invalidate_tags_async(CacheTags.USER)
        user = await self.get_raw_user(id)
        return BaseResponse.ok(user, message="Cập nhật ảnh đại diện thành công")

    async def change_password(
        self, id: UUID | str, payload: ChangePasswordRequest
    ) -> BaseResponse[None]:
        current_user = await self.crud.find_by_id(id)
        if not current_user:
            return BaseResponse.fail(
                message="Không tìm thấy người dùng", status_code=404
            )

        password_hash = PasswordHash.recommended()
        if not current_user.password or not password_hash.verify(
            payload.current_password, current_user.password
        ):
            return BaseResponse.fail(
                message="Mật khẩu hiện tại không đúng", status_code=400
            )

        new_hash = password_hash.hash(payload.new_password)
        await self.crud.update(
            id=id,
            data={
                "password": new_hash,
                "token_version": current_user.token_version + 1,
            },
        )

        await self.cache.invalidate_tags_async(CacheTags.USER)
        return BaseResponse.ok(message="Đổi mật khẩu thành công, vui lòng đăng nhập lại")
