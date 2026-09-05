import os
from typing import Any, cast

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

from src.modules.user.role_constants import ROLE
from src.shared.schemas.page_schemas import PageSchema


def global_values(templates: Jinja2Templates) -> Jinja2Templates:
    ADMIN_PAGES = [
        PageSchema(name="Dashboard", icon="dashboard", id="dashboard", path="/admin"),
        PageSchema(name="Sự kiện", icon="event", id="event", path="/admin/events"),
        PageSchema(
            name="Lưu trữ", icon="photo_library", id="media", path="/admin/media"
        ),
        PageSchema(
            name="Khách mời", icon="group", id="employees", path="/admin/employees"
        ),
        PageSchema(
            name="Tác vụ", icon="assignment", id="queue_jobs", path="/admin/queue-jobs"
        ),
        PageSchema(
            name="Tài khoản",
            icon="deployed_code_account",
            id="account",
            path="/admin/account",
            include_roles=[ROLE.SUPER_ADMIN.value],
        ),
    ]
    cast(dict[str, Any], templates.env.globals)["ADMIN_PAGES"] = ADMIN_PAGES
    cast(dict[str, Any], templates.env.globals)["ADMIN_PAGES_DICT"] = [
        page.model_dump() for page in ADMIN_PAGES
    ]
    load_dotenv()
    cast(dict[str, Any], templates.env.globals)["base_url"] = os.getenv(
        "BASE_URL", "http://localhost:8000"
    )

    from src.shared.middlewares.timezone_middleware import to_user_timezone
    from datetime import datetime

    def format_user_datetime(dt: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
        if not dt:
            return ""
        local_dt = to_user_timezone(dt)
        return local_dt.strftime(fmt) if local_dt else ""

    templates.env.filters["user_tz"] = to_user_timezone
    templates.env.filters["format_user_datetime"] = format_user_datetime

    return templates
