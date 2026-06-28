from __future__ import annotations
from uuid import UUID
from database.models.app_db import SessionDep
from src.shared.base import BaseCrud, BaseResponse
from sqlmodel import or_
from pwdlib import PasswordHash
from src.shared.helpers import RandomHelpers, get_vn_time
from .user_select import UserSelect
from typing import TYPE_CHECKING, Optional
from src.shared.services.redis_services import RedisDep
from .user_schemas import UserSchema
from src.shared.constants.cache_tags import CacheTags
from database.models.media import Medias

if TYPE_CHECKING:
    from database.models.users import Users


class UserServices:
    def __init__(self, session: SessionDep, cache: RedisDep):
        self.session = session
        self.cache = cache
        from database.models.users import Users

        self.crud = BaseCrud[Users](session, Users)

    async def get_raw_user(self, id: UUID | str) -> Optional[UserSchema]:
        cache_key = f"{CacheTags.USER}:{id}"
        from database.models.users import Users

        return await self.cache.get_or_set_async(
            cache_key,
            async_func=lambda: (
                self.crud.select(
                    UserSchema, logic_column=[UserSchema.nameof(lambda x: x.file_id)]
                )
                .join(Medias, isouter=True)
                .group_by(Users.id)
                .find_by_id(id)
            ),
            tags=[CacheTags.USER],
            model_class=UserSchema,
        )

    async def get_user(self, id: UUID | str) -> BaseResponse[UserSchema]:
        user = await self.get_raw_user(id)

        if not user:
            return BaseResponse.fail("Không tìm thấy thông tin người dùng", 404)

        return BaseResponse.ok(user)

    async def create_user(
        self, req: Users, withVerifyEmail: bool = False
    ) -> BaseResponse[Users]:
        from database.models.users import Users

        if not req.username:
            req.username = req.email

        exiting_user = (
            await self.crud.select(UserSelect)
            .where(or_(Users.email == req.email, Users.username == req.username))
            .find_one()
        )

        if exiting_user is not None:
            if exiting_user.email == req.email:
                return BaseResponse.fail(message="Email đã tồn tại", status_code=400)
            if exiting_user.username == req.username:
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
        return BaseResponse.created(new_user)
