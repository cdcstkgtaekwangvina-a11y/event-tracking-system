import os
from fastapi.routing import APIRoute
from granian.constants import Interfaces
from granian.log import LogLevels
from fastapi import FastAPI
import granian
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from src.shared.middlewares.handel_exception import handle_exceptions


load_dotenv()

environment: str = os.getenv("env") or "dev"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is running")
    from database.models.app_db import init_db
    from src.shared.base.base_queue import QueueServices

    for route in app.routes:
        if isinstance(route, APIRoute):
            if "." in route.name:
                route.name = route.name.split(".")[-1]

    await init_db()
    bg_host = QueueServices()
    await bg_host.start()
    await bg_host.fill_job_from_db()
    yield
    await bg_host.stop()
    print("Server is shutdown")


SRC_DIR = Path(__file__).resolve().parent  # Thư mục 'src'
PROJECT_ROOT = SRC_DIR.parent


def create_app() -> FastAPI:
    from src.modules.app_routes import router as main_router
    from src import subscription_services as services
    from src.shared.base import BaseRoute
    from src.shared.base.base_config_jinja import global_values

    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
    app.router.route_class = BaseRoute
    app.mount("/static", StaticFiles(directory=SRC_DIR / "static"), name="static")
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))

    reload: bool = environment == "dev"

    granian.Granian(
        target="src.main:app",
        port=port,
        interface=Interfaces.ASGI,
        reload=reload,
        log_level=LogLevels.debug,
    ).serve()
