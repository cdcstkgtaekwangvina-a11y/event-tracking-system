from src.shared.base.base_route import BaseRouter
from fastapi import Depends
from src.shared.middlewares.auth_middlewares import RequireAuth

TAG_NAME = "employees"
router = BaseRouter(
    controller=TAG_NAME,
    tags=[TAG_NAME],
    dependencies=[Depends(RequireAuth(is_required_auth=True))],
)
