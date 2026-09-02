from typing import Any

from jinja2 import Environment, FileSystemLoader


class BaseEmailService:
    def _get_email_template(
        self,
        path: str = "/templates/email/index.j2",
        data: dict[str, Any] = {},
        email_service: str = "elastic_email",
    ):
        env = Environment(loader=FileSystemLoader("src"))

        template = env.get_template(path)
        return template.render({**data, "email_service": email_service})
