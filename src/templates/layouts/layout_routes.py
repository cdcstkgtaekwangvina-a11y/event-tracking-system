from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse, RedirectResponse

from src.shared.base import BaseRequest
from src.shared.middlewares.auth_middlewares import AuthContext, auth


def layouts_routes(app: FastAPI) -> FastAPI:
    @app.get("/", include_in_schema=False, response_class=HTMLResponse, name="home")
    def root(
        req: BaseRequest,
        auth: AuthContext = auth(is_required_auth=False),
    ):
        return req.response_html(name="/templates/layouts/main.j2", context={})

    @app.get(
        "/admin",
        include_in_schema=False,
        response_class=HTMLResponse,
        name="admin_dashboard",
    )
    def admin(
        req: BaseRequest,
        auth: AuthContext = auth(is_required_auth=True),
    ):

        return req.response_html(
            name="/templates/layouts/admin_home.j2", context={}, cache_time=3600
        )

    @app.get("/.well-known/appspecific/com.chrome.devtools.json")
    def silence_chrome():
        return {"status": "ok"}

    @app.get(
        "/404", include_in_schema=False, response_class=HTMLResponse, name="not_found"
    )
    def not_found(
        req: BaseRequest,
        auth: AuthContext = auth(is_required_auth=False),
    ):
        return req.response_html(
            name="/templates/not_found.j2",
            context={},
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )

    @app.get(
        "/error", include_in_schema=False, response_class=HTMLResponse, name="error"
    )
    def error(
        req: BaseRequest,
        auth: AuthContext = auth(is_required_auth=False),
    ):
        if not req.cookies.get("error_permitted"):
            return RedirectResponse(url="/404", status_code=status.HTTP_302_FOUND)

        response = req.response_html(
            name="/templates/error.j2",
            context={},
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )
        response.delete_cookie("error_permitted")
        return response

    return app
