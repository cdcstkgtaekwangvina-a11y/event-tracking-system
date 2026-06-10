from fastapi import APIRouter
from src.modules.authentication.auth_routes import router as auth_routes
from src.modules.events.event_routes import router as event_routes
from src.modules.employees.employee_routes import router as employee_routes
from src.modules.media_manager.media_routes import router as media_routes
from src.modules.user.user_routes import router as user_routes

router = APIRouter()

router.include_router(auth_routes)
router.include_router(event_routes)
router.include_router(employee_routes)
router.include_router(media_routes)
router.include_router(user_routes)
