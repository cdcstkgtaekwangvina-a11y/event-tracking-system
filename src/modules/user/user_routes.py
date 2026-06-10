from fastapi import APIRouter
from . import user_apis
from .views import user_views

router = APIRouter()

router.include_router(user_apis.router)
router.include_router(user_views.router)
