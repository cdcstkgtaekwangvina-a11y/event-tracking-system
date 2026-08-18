from uuid import UUID

from fastapi import Depends
from pwdlib import PasswordHash

from database.models.app_db import SessionDep
from src.modules.user.role_constants import ROLE
from src.modules.user.user_services import UserServices
from src.shared.base import BaseCrud, BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from src.shared.services.redis_services import RedisDep

from .account_schemas import CreateAccountRequest, UpdateAccountRequest
from .account_select import AccountSelect


class AccountServices:
    def __init__(
        self,
        session: SessionDep,
        redis: RedisDep,
        user_services: UserServices = Depends(),
    ):
        from database.models.users import Users

        self.session = session
        self.redis = redis
        self.user_services = user_services
        self.crud = BaseCrud[Users](session, Users)

    async def list_accounts_raw(
        self, pagination: PaginationRequest
    ) -> PaginationResponse:
        cache_key = self.redis.get_pagination_key(CacheTags.USER, pagination)

        async def get_data_async():
            return await self.crud.select(AccountSelect).pagination_async(
                pagination, search_fields=["name", "username", "email"]
            )

        return await self.redis.get_or_set_async(
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

        new_user = await self.user_services.create_user_or_fail(
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

        await self.redis.invalidate_tags_async(CacheTags.USER)
        account = AccountSelect.model_validate(updated, from_attributes=True)
        return BaseResponse.ok(account, message="Cập nhật tài khoản thành công")
