import os
from typing import Any, cast

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

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
            name="Queue Jobs", icon="queue", id="queue_jobs", path="/admin/queue-jobs"
        ),
        PageSchema(
            name="Tài khoản",
            icon="deployed_code_account",
            id="account",
            path="/admin/account",
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

    return templates
