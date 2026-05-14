from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from scalar_fastapi import get_scalar_api_reference, Layout, Theme
from fastapi.responses import HTMLResponse


def add_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Check-in app api",
        version="1.0.0",
        summary="Đây là tài liệu api của website hỗ trợ check-in online",
        description="Website này được build vì mục đích check-in online",
        routes=app.routes,
    )

    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }

    app.openapi_schema = openapi_schema

    @app.get("/scalar", include_in_schema=False, response_class=HTMLResponse)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title="Check-in App Documentation",
            layout=Layout.MODERN,
            theme=Theme.DEEP_SPACE,
            authentication={
                "preferredSecurityScheme": "bearerAuth",
                "data": {"bearerAuth": {"token": ""}},
            },
            scalar_proxy_url="https://proxy.scalar.com",
        )

    return app
