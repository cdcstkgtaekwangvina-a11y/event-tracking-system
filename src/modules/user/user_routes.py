from fastapi import APIRouter
from . import user_apis
from .views import user_views
from .views.admin import account_admin_views

router = APIRouter()

router.include_router(user_apis.router)
router.include_router(user_apis.account_router)
router.include_router(user_views.router)
router.include_router(account_admin_views.router)
