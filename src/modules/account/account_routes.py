from fastapi import APIRouter

from .account_apis import router as account_apis_router
from .views.admin.account_admin_views import router as account_admin_views_router

router = APIRouter()

router.include_router(account_admin_views_router)
router.include_router(account_apis_router)
