from fastapi import APIRouter
from .views import event_views
from . import event_apis

router = APIRouter()

router.include_router(event_views.router)
router.include_router(event_apis.router)
