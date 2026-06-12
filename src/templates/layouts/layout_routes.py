from fastapi import Depends, FastAPI, status
from src.shared.middlewares.auth_middlewares import RequireAuth, AuthContext
from fastapi.responses import HTMLResponse, RedirectResponse
from src.shared.base import BaseRequest


def layouts_routes(app: FastAPI) -> FastAPI:
    @app.get("/", include_in_schema=False, response_class=HTMLResponse, name="home")
    def root(
        req: BaseRequest,
        auth: AuthContext = Depends(RequireAuth(is_required_auth=False)),
    ):
        return req.response_html(
            name="/templates/layouts/main.j2",
            context={},
        )

    @app.get(
        "/admin",
        include_in_schema=False,
        response_class=HTMLResponse,
        name="admin_dashboard",
    )
    def admin(
        req: BaseRequest,
        auth: AuthContext = Depends(RequireAuth(is_required_auth=True)),
    ):

        return req.response_html(
            name="/templates/layouts/admin_home.j2",
            context={"is_navbar": True},
        )

    @app.get(
        "/404", include_in_schema=False, response_class=HTMLResponse, name="not_found"
    )
    def not_found(req: BaseRequest):
        return req.response_html(
            name="/templates/not_found.j2", context={}, status_code=404
        )

    @app.get(
        "/error", include_in_schema=False, response_class=HTMLResponse, name="error"
    )
    def error(req: BaseRequest):
        if not req.cookies.get("error_permitted"):
            return RedirectResponse(url="/404", status_code=status.HTTP_302_FOUND)

        response = req.response_html(
            name="/templates/error.j2", context={}, status_code=500
        )
        response.delete_cookie("error_permitted")
        return response

    return app
