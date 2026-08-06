from fastapi import APIRouter
from . import setting_apis

router = APIRouter()

router.include_router(setting_apis.router)
