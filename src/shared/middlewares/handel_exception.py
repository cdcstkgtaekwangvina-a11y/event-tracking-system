from fastapi import FastAPI, Request, status
from fastapi.responses import (
    JSONResponse,
    HTMLResponse,
    RedirectResponse,
)  # Thêm RedirectResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_exceptions(app: FastAPI, templates: Jinja2Templates) -> FastAPI:
    @app.middleware("http")
    async def catch_exceptions_middleware(request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            route = request.scope.get("route")
            route_path = getattr(route, "path", None) or request.url.path
            logger.exception(
                "Đã xảy ra lỗi không xác định tại API: %s %s",
                request.method,
                route_path,
            )
            raise e

    async def core_exception_handler(req: Request, exc: Exception):
        detail = None
        if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
            status_code = exc.status_code or 500
            detail = exc.detail
        else:
            status_code = 500
            detail = getattr(exc, "message", str(exc))

        route = req.scope.get("route")
        route_path = getattr(route, "path", None) or req.url.path

        logger.exception(
            "Global exception tại API: %s %s | status=%s | detail=%s",
            req.method,
            route_path,
            status_code,
            detail,
        )

        response_class = getattr(route, "response_class", None) if route else None
        is_api = str(req.url.path).startswith("/api")
        if response_class == HTMLResponse or not is_api:
            if req.url.path in ["/404", "/error"]:
                return HTMLResponse(
                    content="<h1>Hệ thống gặp sự cố!</h1>", status_code=500
                )

            if status_code == 404:
                response = RedirectResponse(
                    url="/404", status_code=status.HTTP_302_FOUND
                )
                return response

            response = RedirectResponse(url="/error", status_code=status.HTTP_302_FOUND)
            response.set_cookie(
                key="error_permitted", value="true", max_age=10, httponly=True
            )
            return response

        return JSONResponse(status_code=status_code, content={"detail": detail})

    @app.exception_handler(Exception)
    async def generic_exception_handler(req: Request, exc: Exception):
        return await core_exception_handler(req, exc)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(req: Request, exc: StarletteHTTPException):
        return await core_exception_handler(req, exc)

    return app
