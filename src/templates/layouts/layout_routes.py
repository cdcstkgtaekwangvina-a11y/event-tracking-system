import asyncio
from datetime import date

from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import and_, col, func, select

from src.shared.base import BaseRequest
from src.shared.middlewares.auth_middlewares import AuthContext, auth


async def __get_dashboard_stats():
    from database.models.app_db import get_session_factory

    async def __count_account():
        from database.models.users import Users

        async with get_session_factory()() as session:
            statement = select(func.count()).select_from(Users)
            count_acc = await session.exec(statement)
            return count_acc.one()

    async def __count_file():
        from database.models.media import Medias

        async with get_session_factory()() as session:
            statement = (
                select(func.count())
                .select_from(Medias)
                .where(Medias.is_folder == False)
            )
            count_file = await session.exec(statement)
            return count_file.one()

    async def __count_check_in_today():
        from database.models.events_employees import EventsEmployees

        async with get_session_factory()() as session:
            today = date.today()
            statement = (
                select(func.count())
                .select_from(EventsEmployees)
                .where(
                    and_(
                        col(EventsEmployees.check_in_at).is_not(None),
                        func.date(col(EventsEmployees.check_in_at)) == today,
                    )
                )
            )
            count_check_in_today = await session.exec(statement)
            return count_check_in_today.one()

    total_acc, total_file, total_check_in_today = await asyncio.gather(
        __count_account(),
        __count_file(),
        __count_check_in_today(),
    )
    return {
        "count_acc": total_acc,
        "count_file": total_file,
        "count_check_in_today": total_check_in_today,
    }


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
        page: int = 1,
        search: str = "",
        status: str = "all",
        sort_field: str = "check_in_at",
        is_desc: bool = True,
    ):

        return req.response_html(
            name="/templates/layouts/admin_home.j2",
            context={
                "page": page,
                "search": search,
                "status": status,
                "sort_field": sort_field,
                "is_desc": is_desc,
            },
            cache_time=3600,
            public_cache=False,
        )

    @app.get(
        "/admin/guideline",
        include_in_schema=False,
        response_class=HTMLResponse,
        name="admin_guideline",
    )
    def admin_guideline(
        req: BaseRequest,
        auth: AuthContext = auth(is_required_auth=True),
    ):
        return req.response_html(
            name="/templates/guideline.j2",
            context={},
            cache_time=3600,
            public_cache=False,
        )

    @app.get("/api/dashboard-stats", response_class=JSONResponse)
    async def dashboard_stats(
        req: BaseRequest,
        auth: AuthContext = auth(is_required_auth=True),
    ):
        from src.shared.base.base_response import BaseResponse

        if not auth.is_valid:
            return BaseResponse.unauthorized()

        return BaseResponse.ok(data=await __get_dashboard_stats())

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

    @app.get(
        "/email",
        include_in_schema=False,
        response_class=HTMLResponse,
        name="email_test",
    )
    def email_test(req: BaseRequest):
        return req.response_html(
            name="/templates/email/index.j2",
            context={
                "title": "Event Tracking System",
            },
        )

    return app
