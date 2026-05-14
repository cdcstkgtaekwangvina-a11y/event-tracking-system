from fastapi import APIRouter
from src.modules.authentication.auth_routes import router as auth_routes
from src.modules.events.event_routes import router as event_routes

router = APIRouter()

router.include_router(auth_routes)
router.include_router(event_routes)
