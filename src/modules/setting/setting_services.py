from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from database.models.app_db import SessionDep
from database.models.settings import Settings
from src.shared.base.base_crud import BaseCrud
from src.shared.base.base_response import BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.services.redis_services import RedisDep

from .setting_constants import AppConfigKey
from .setting_schemas import UpdateSettingSchema


class AppSettingServices:
    def __init__(self, session: SessionDep, redis: RedisDep):
        self.session = session
        self.redis = redis
        self.crud = BaseCrud(session, Settings)

    async def get_raw_app_setting(self, id: AppConfigKey) -> Settings | None:
        result = await self.redis.get_or_set_async(
            key=f"{CacheTags.SETTING}:{id}",
            tags=[CacheTags.SETTING],
            async_func=lambda: self.crud.find_by_id(id=str(id)),
            model_class=Settings,
        )
        if not result:
            raise HTTPException(status_code=500, detail="System config not found")

        return result

    async def get_setting_value[T: BaseModel](
        self, id: AppConfigKey, model_cls: type[T]
    ) -> T | None:
        result = await self.get_raw_app_setting(id=id)
        if result:
            return model_cls(**result.value or {})

        return None

    async def get_app_setting(self, id: AppConfigKey) -> BaseResponse[Settings | None]:
        return BaseResponse.ok(await self.get_raw_app_setting(id=id))

    async def update_app_setting(
        self, id: AppConfigKey, payload: UpdateSettingSchema
    ) -> BaseResponse[Settings]:
        result = await self.crud.update(
            condition=lambda model: model.id == id, data=payload
        )
        if not result:
            return BaseResponse.not_found()
        return BaseResponse.ok(result)


AppSettingServicesDep = Annotated[AppSettingServices, Depends()]
