from fastapi import APIRouter

from .queue_job_apis import router as queue_job_apis
from .views.admin.queue_job_admin_views import (
    router as queue_job_admin_views_router,
)

router = APIRouter()

router.include_router(queue_job_admin_views_router)
router.include_router(queue_job_apis)
