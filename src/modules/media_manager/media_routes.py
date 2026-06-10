from fastapi import APIRouter
from .views import media_view
from . import media_apis

router = APIRouter()

router.include_router(media_view.router)
router.include_router(media_apis.router)
