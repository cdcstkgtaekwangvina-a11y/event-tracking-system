from typing import Any

from jinja2 import Environment, FileSystemLoader


class BaseEmailService:
    def __get_email_template(
        self, path: str = "/templates/email/index.j2", data: dict[str, Any] = {}
    ):
        env = Environment(loader=FileSystemLoader("src"))

        template = env.get_template(path)
        return template.render(data)
