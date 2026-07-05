from fastapi import APIRouter
from .employee_apis import router as employee_apis_router
from .views.admin.employee_admin_views import router as employee_admin_router

router = APIRouter()

router.include_router(employee_admin_router)
router.include_router(employee_apis_router)
