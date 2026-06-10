import os
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from src.shared.schemas.page_schemas import PageSchema
from typing import Any, cast


def global_values(templates: Jinja2Templates) -> Jinja2Templates:
    cast(dict[str, Any], templates.env.globals)["ADMIN_PAGES"] = [
        PageSchema(
            name="Dashboard", icon="dashboard.svg", id="dashboard", path="/admin"
        ),
        PageSchema(name="Sự kiện", icon="event.svg", id="event", path="/admin/events"),
        PageSchema(name="Lưu trữ", icon="media.svg", id="media", path="/admin/media"),
        PageSchema(
            name="Khách mời", icon="group.svg", id="employee", path="/admin/employee"
        ),
        PageSchema(
            name="Tài khoản", icon="account.svg", id="account", path="/admin/account"
        ),
    ]

    load_dotenv()
    cast(dict[str, Any], templates.env.globals)["base_url"] = os.getenv(
        "BASE_URL", "http://localhost:8000"
    )

    return templates
