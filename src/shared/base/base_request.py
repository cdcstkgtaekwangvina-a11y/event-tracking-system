from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Mapping
from starlette.background import BackgroundTask


class BaseRequest(Request):
    def get_templates(self) -> Jinja2Templates:
        return self.app.state.templates

    def response_html(
        self,
        name: str,
        context: dict[str, Any] | None = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> HTMLResponse:
        templates = self.get_templates()
        if context is None:
            context = {}
        context.setdefault(
            "auth",
            {
                "is_authenticated": getattr(self.state, "is_authenticated", False),
                "user": getattr(self.state, "user", None),
            },
        )
        context.setdefault("request", self)
        context.setdefault("req", self)
        return templates.TemplateResponse(
            request=self,
            name=name,
            context=context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
