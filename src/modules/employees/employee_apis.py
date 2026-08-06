from fastapi import Depends

from src.shared.base import BaseRouter
from src.shared.helpers.cbv import clean_cbv
from src.shared.schemas.pagination_schemas import PaginationQuery

from .employee_schemas import (
    BulkUpsertEmployeeRequest,
    EmployeeBulkDeleteRequest,
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
    ReadSheetFile,
)
from .employee_services import EmployeeServices

TAG_NAME = "employees"
router = BaseRouter(controller=TAG_NAME, tags=[TAG_NAME])


@clean_cbv(router)
class EmployeeController:
    def __init__(self, service: EmployeeServices = Depends()):
        self.service = service

    @router.get_api()
    async def get_employees(self, pagination: PaginationQuery):
        return await self.service.get_employees(pagination)

    @router.get_api("{employee_id}")
    async def get_employee_by_id(self, employee_id: int):
        return await self.service.get_employee_by_id(employee_id)

    @router.post_api()
    async def create_employee(self, payload: EmployeeCreateRequest):
        return await self.service.create_employee(payload)

    @router.put_api("{employee_id}")
    async def update_employee(self, employee_id: int, payload: EmployeeUpdateRequest):
        return await self.service.update_employee(employee_id, payload)

    @router.delete_api("bulk")
    async def delete_bulk_employees(self, payload: EmployeeBulkDeleteRequest):
        return await self.service.bulk_delete_employees(payload.ids)

    @router.delete_api("{employee_id}")
    async def delete_employee(self, employee_id: int):
        return await self.service.delete_employee(employee_id)

    @router.get_api("export")
    async def export_employees(self):
        return await self.service.export_employees()

    @router.post_api("import")
    async def import_employee(self, payload: BulkUpsertEmployeeRequest):
        return await self.service.bulk_upsert_employees(payload)

    @router.post_api("read-import-file")
    async def read_sheet_file(self, payload: ReadSheetFile):
        return await self.service.read_import_file(payload)
