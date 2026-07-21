from fastapi import Depends

from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv

from .employee_schemas import BulkUpsertEmployeeRequest
from .employee_services import EmployeeServices

TAG_NAME = "employees"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class EmployeeController:
    def __init__(self, service: EmployeeServices = Depends()):
        self.service = service

    @router.post_api("import")
    async def import_employee(self, payload: BulkUpsertEmployeeRequest):
        return await self.service.bulk_upsert_employees(payload)
