import os
from granian.constants import Interfaces
from granian.log import LogLevels
from fastapi import FastAPI, Request, HTTPException
import granian
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

environment: str = os.getenv("env") or "dev"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is running")
    from database.models.app_db import init_db

    await init_db()
    yield
    print("Server is shutdown")


SRC_DIR = Path(__file__).resolve().parent  # Thư mục 'src'
PROJECT_ROOT = SRC_DIR.parent


def create_app() -> FastAPI:
    from src.modules.app_routes import router as main_router
    from src import subscription_services as services

    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)

    app.mount("/static", StaticFiles(directory=SRC_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=PROJECT_ROOT / "src")
    app.state.templates = templates

    @app.get("/", response_class=HTMLResponse, include_in_schema=False, name="home")
    async def root(req: Request):
        try:
            base_url = os.getenv("BASE_URL", "http://localhost:8000")

            templates = req.app.state.templates
            return templates.TemplateResponse(
                request=req,
                name="/templates/home.j2",
                context={"base_url": base_url, "is_navbar": True},
            )
        except Exception as e:
            print(f"Template Error: {e}")
            raise e

    app.include_router(main_router)

    @app.middleware("http")
    async def catch_exceptions_middleware(request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            import traceback

            traceback.print_exc()
            logger.exception("Đã xảy ra lỗi không xác định tại API:")
            raise e

    @app.exception_handler(500)
    async def global_exception_handler(req: Request, exc: HTTPException):
        detail = getattr(exc, "detail", str(exc))
        print(f"GLOBAL ERROR CAUGHT: {detail}")

        if hasattr(exc, "detail") and exc.detail:
            return JSONResponse(
                status_code=getattr(exc, "status_code", 500),
                content={"error": exc.detail},
            )

        try:
            templates = req.app.state.templates
            return templates.TemplateResponse(
                request=req,
                name="/templates/error.j2",
                context={"error_msg": detail},
            )
        except Exception as render_exc:
            return JSONResponse(
                status_code=500,
                content={"message": "Critical Error", "debug": str(render_exc)},
            )

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exc: Exception):
        return templates.TemplateResponse(
            request=request,
            name="templates/not_found.j2",
            status_code=404,
            context={"message": "Trang bạn tìm kiếm không tồn tại"},
        )

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
