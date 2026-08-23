from fastapi import Depends

from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.middlewares.auth_middlewares import auth

from .setting_constants import AppConfigKey
from .setting_schemas import FileConfigSchema, UpdateSettingSchema
from .setting_services import AppSettingServices

TAG_NAME = "setting"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class SettingController:
    def __init__(self, service: AppSettingServices = Depends()):
        self.service = service

    @router.get_api("max_file_sizes")
    async def get_max_file_sizes(self):
        return await self.service.get_app_setting(AppConfigKey.file_config)

    @router.put("max_file_sizes", dependencies=[auth()])
    async def update_max_file_sizes(self, payload: FileConfigSchema):
        return await self.service.update_app_setting(
            AppConfigKey.file_config, UpdateSettingSchema(value=payload.model_dump())
        )
