from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import UUID

from pwdlib import PasswordHash

from database.models.app_db import SessionDep
from database.models.media import Medias
from src.modules.user.role_constants import ROLE
from src.shared.base import BaseCrud, BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.helpers import RandomHelpers, get_vn_time
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from src.shared.services.redis_services import RedisDep

from .user_schemas import (
    ChangePasswordRequest,
    CreateAccountRequest,
    UpdateAccountRequest,
    UpdateProfileRequest,
)
from .user_select import AccountSelect, UserSelect

if TYPE_CHECKING:
    from database.models.users import Users


class UserServices:
    """Handles account management for both the logged-in user themselves
    (profile/avatar/password — see `update_profile`/`set_avatar_from_media`/
    `change_password`) and admin-on-others account management (see
    `list_accounts`/`create_account`/`update_account`). Kept as one module
    since both operate on the same `Users` table and the admin flows reuse
    the self-service create/update logic directly (`create_user_or_fail`)."""

    def __init__(self, session: SessionDep, cache: RedisDep):
        self.session = session
        self.cache = cache
        from database.models.users import Users

        self.crud = BaseCrud[Users](session, Users)

    async def get_raw_user(self, id: UUID | str) -> UserSelect | None:
        cache_key = f"{CacheTags.USER}:{id}"

        return cast(
            UserSelect | None,
            await self.cache.get_or_set_async(
                cache_key,
                async_func=lambda: (
                    self.crud.select(
                        UserSelect,
                        logic_column=[
                            Medias.id.label("file_id"),
                            Medias.url.label("file_url"),
                        ],
                    )
                    .join(Medias, isouter=True)
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

    async def _link_avatar_media(
        self, id: UUID | str, media_id: int
    ) -> BaseResponse[UserSelect]:
        updated = await self.crud.update(id=id, data={"media_id": media_id})
        if not updated:
            return BaseResponse.fail(
                message="Không tìm thấy người dùng", status_code=404
            )

        await self.cache.invalidate_tags_async(CacheTags.USER)
        user = await self.get_raw_user(id)
        return BaseResponse.ok(user, message="Cập nhật ảnh đại diện thành công")

    async def set_avatar_from_media(
        self, id: UUID | str, media_id: int
    ) -> BaseResponse[UserSelect]:
        """Picks an EXISTING file already in the Media library as the avatar —
        no upload, just links `Users.media_id` to it (see `_link_avatar_media`)."""
        media = await BaseCrud(self.session, Medias).find_by_id(media_id)
        if not media or media.is_folder:
            return BaseResponse.fail(message="Không tìm thấy file", status_code=404)

        if not media.media_metadata or media.media_metadata.get("type") != "image":
            return BaseResponse.fail(
                message="Chỉ có thể chọn file ảnh làm ảnh đại diện",
                status_code=400,
            )

        return await self._link_avatar_media(id, media.id)

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

    # ------------------------------------------------------------------
    # Admin account management (`/admin/account`) — ADMIN/SUPER_ADMIN only,
    # gated at the route level (see `user_apis.AccountApis`).
    # ------------------------------------------------------------------

    async def list_accounts_raw(
        self, pagination: PaginationRequest
    ) -> PaginationResponse:
        cache_key = self.cache.get_pagination_key(CacheTags.USER, pagination)

        async def get_data_async():
            return await self.crud.select(AccountSelect).pagination_async(
                pagination, search_fields=["name", "username", "email"]
            )

        return await self.cache.get_or_set_async(
            key=cache_key,
            async_func=get_data_async,
            tags=[CacheTags.USER],
            model_class=PaginationResponse,
        )

    async def list_accounts(
        self, pagination: PaginationRequest
    ) -> BaseResponse[PaginationResponse]:
        result = await self.list_accounts_raw(pagination)
        return BaseResponse.ok(result, message="Lấy danh sách tài khoản thành công")

    async def create_account(
        self, payload: CreateAccountRequest
    ) -> BaseResponse[AccountSelect]:
        from database.models.users import Users

        new_user = await self.create_user_or_fail(
            Users(**payload.model_dump(), role=ROLE.ADMIN)
        )
        account = AccountSelect.model_validate(new_user, from_attributes=True)
        return BaseResponse.created(account, message="Tạo tài khoản thành công")

    async def update_account(
        self,
        id: UUID | str,
        payload: UpdateAccountRequest,
        requester_role: str | None,
    ) -> BaseResponse[AccountSelect]:
        from database.models.users import Users

        target = await self.crud.find_by_id(id)
        if not target:
            return BaseResponse.not_found(message="Không tìm thấy tài khoản")

        if target.role == ROLE.SUPER_ADMIN and requester_role != ROLE.SUPER_ADMIN:
            return BaseResponse.fail(
                message="Không có quyền chỉnh sửa tài khoản Super Admin",
                status_code=403,
            )

        if payload.email is not None and requester_role != ROLE.SUPER_ADMIN:
            return BaseResponse.fail(
                message="Chỉ Super Admin mới có quyền chỉnh sửa Email",
                status_code=403,
            )

        update_data = payload.model_dump(
            exclude_unset=True, exclude_none=True, exclude={"password"}
        )
        if payload.password:
            update_data["password"] = PasswordHash.recommended().hash(
                payload.password
            )
            update_data["token_version"] = target.token_version + 1

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
                message="Cập nhật tài khoản thất bại", status_code=400
            )

        await self.cache.invalidate_tags_async(CacheTags.USER)
        account = AccountSelect.model_validate(updated, from_attributes=True)
        return BaseResponse.ok(account, message="Cập nhật tài khoản thành công")
