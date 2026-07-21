from fastapi import APIRouter
from .views.admin import media_admin_view
from . import media_apis

router = APIRouter()

router.include_router(media_admin_view.router)
router.include_router(media_apis.router)
