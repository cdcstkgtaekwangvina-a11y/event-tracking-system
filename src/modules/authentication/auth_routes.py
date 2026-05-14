from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Optional
# from .auth_services import service

TAG = "auth"
router = APIRouter(tags=[TAG])
api = f"/api/{TAG}"
controller = f"/{TAG}"


@router.get(f"{controller}/login", response_class=HTMLResponse, name="login_view")
async def LoginView(req: Request, redirect: Optional[str] = None):
    templates = req.app.state.templates
    return templates.TemplateResponse(
        req, "modules/authentication/views/login.j2", context={"redirect": redirect}
    )


@router.get(
    f"{controller}/forgot-password",
    response_class=HTMLResponse,
    name="forgot_password_view",
)
async def ForgotPasswordView(req: Request, redirect: Optional[str] = None):
    templates = req.app.state.templates
    return templates.TemplateResponse(
        req,
        "modules/authentication/views/forgot_password.j2",
        context={"redirect": redirect},
    )
