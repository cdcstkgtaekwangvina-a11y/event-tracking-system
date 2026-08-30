import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.shared.base.base_logger import get_logger
from src.shared.base.base_queue import queue_service
from src.shared.middlewares.handel_exception import handle_exceptions

logger = get_logger("main")
load_dotenv()

environment: str = os.getenv("env") or "dev"
from src.shared.backgroundtasks import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server is starting")
    from database.models.app_db import init_db

    await init_db()

    await queue_service.start()
    await queue_service.fill_job_from_db()

    app.state.queue_service = queue_service

    yield

    await queue_service.stop()
    logger.info("Server is shutdown")


SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent


class CachedStaticFiles(StaticFiles):
    def __init__(self, *args, cache_control: str = "public, max-age=2592000", **kwargs):
        self.cache_control = cache_control
        super().__init__(*args, **kwargs)

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        if response.status_code == 200:
            response.headers["Cache-Control"] = self.cache_control
        return response


def create_app() -> FastAPI:
    from src import subscription_services as services
    from src.modules.app_routes import router as main_router
    from src.shared.base import BaseRoute
    from src.shared.base.base_config_jinja import global_values

    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
    app.router.route_class = BaseRoute

    static_cache = "public, max-age=604800" if environment == "dev" else "public, max-age=2592000, stale-while-revalidate=86400"
    app.mount("/static", CachedStaticFiles(directory=SRC_DIR / "static", cache_control=static_cache), name="static")
    fonts_dir = PROJECT_ROOT / "public" / "fonts"
    if fonts_dir.exists():
        app.mount("/fonts", CachedStaticFiles(directory=fonts_dir, cache_control="public, max-age=31536000, immutable"), name="fonts")
    templates = global_values(Jinja2Templates(directory=PROJECT_ROOT / "src"))

    app.state.templates = templates

    app.include_router(main_router)
    app = handle_exceptions(app, templates)
    from src.templates.layouts.layout_routes import layouts_routes

    app = layouts_routes(app)
    if environment == "dev":
        app = services.add_openapi(app)
    return app


app = create_app()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import granian
    from granian.constants import Interfaces

    port = int(os.getenv("PORT", 8000))

    reload: bool = environment == "dev"

    granian.Granian(
        target="src.main:app",
        port=port,
        interface=Interfaces.ASGI,
        reload=reload,
    ).serve()
