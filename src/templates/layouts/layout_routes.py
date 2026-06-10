from fastapi import Depends, FastAPI
from src.shared.middlewares.auth_middlewares import RequireAuth, AuthContext
from fastapi.responses import HTMLResponse
from src.shared.base import BaseRequest


def layouts_routes(app: FastAPI) -> FastAPI:
    @app.get("/", include_in_schema=False, response_class=HTMLResponse, name="home")
    def root(
        req: BaseRequest,
        auth: AuthContext = Depends(RequireAuth(is_required_auth=False)),
    ):
        return req.response_html(
            name="/templates/layouts/main.j2",
            context={
                "is_navbar": True,
                "is_authenticated": auth.is_valid,
                "user": auth.payload.user or None,
            },
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
            context={
                "is_navbar": True,
                "is_authenticated": auth.is_valid,
                "user": auth.payload.user or None,
            },
        )

    return app
