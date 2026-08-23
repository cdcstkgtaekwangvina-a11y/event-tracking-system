from fastapi import Depends
from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from .setting_services import AppSettingServices
from .setting_constants import AppConfigKey

TAG_NAME = "setting"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class SettingController:
    def __init__(self, service: AppSettingServices = Depends()):
        self.service = service

    @router.get_api("max_file_sizes")
    async def get_max_file_sizes(self):
        return await self.service.get_app_setting(AppConfigKey.file_config)
