from database.models.app_db import SessionDep, SessionFactoryDep
from database.models.employees import Employees
from src.shared.base import BaseCrud, BaseResponse
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse

from .employee_schemas import (
    BulkUpsertEmployeeRequest,
    BulkUpsertResponse,
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
)


class EmployeeServices:
    def __init__(
        self,
        session: SessionDep,
        session_factory: SessionFactoryDep,
    ):
        self.session = session
        self.session_factory = session_factory
        self.crud = BaseCrud(session, Employees)

    async def create_employee(
        self, employee: EmployeeCreateRequest
    ) -> BaseResponse[Employees]:
        new_employee = await self.crud.create(employee)
        return BaseResponse.created(new_employee, message="Thêm nhân viên thành công")

    async def get_employees(
        self, pagination: PaginationRequest
    ) -> BaseResponse[PaginationResponse]:
        result = await self.crud.pagination_async(pagination)
        return BaseResponse.ok(result, message="Lấy danh sách nhân viên thành công")

    async def get_employee_by_id(self, employee_id: int) -> BaseResponse[Employees]:
        employee = await self.crud.find_by_id(employee_id)
        if not employee:
            return BaseResponse.not_found(message="Không tìm thấy nhân viên")
        return BaseResponse.ok(employee, message="Lấy chi tiết nhân viên thành công")

    async def update_employee(
        self, employee_id: int, employee_data: EmployeeUpdateRequest
    ) -> BaseResponse[Employees]:
        is_exist = (
            await self.crud.select(Employees)
            .where(Employees.id == employee_id)
            .any_async()
        )
        if not is_exist:
            return BaseResponse.not_found(message="Không tìm thấy nhân viên")

        update_employee = await self.crud.update(id=employee_id, data=employee_data)
        return BaseResponse.ok(update_employee)

    async def delete_employee(self, employee_id: int) -> BaseResponse[None]:
        deleted = await self.crud.delete(employee_id)
        if not deleted:
            return BaseResponse.not_found(message="Không tìm thấy nhân viên")
        return BaseResponse.ok(message="Xóa nhân viên thành công")

    async def bulk_upsert_employees(
        self, employees: BulkUpsertEmployeeRequest
    ) -> BaseResponse[BulkUpsertResponse]:
        from src.modules.queue_job.queue_job_schemas import CreateQueueJobSchema
        from src.modules.queue_job.queue_job_services import QueueJobServices
        from src.shared.constants.queue_keys import QueueKeys

        job_service = QueueJobServices(session=self.session)
        new_job = await job_service.create_job(
            CreateQueueJobSchema(
                type=QueueKeys.BULK_UPSERT_EMPLOYEES.value,
                next_payload=employees.model_dump(),
            )
        )

        if new_job:
            from src.shared.backgroundtasks.employee_bg_tasks import (
                EmployeeBackgroundTask,
            )

            job = EmployeeBackgroundTask()
            await job.bulk_upsert_employees_db(new_job.id)
            return BaseResponse.ok(
                BulkUpsertResponse(job_id=new_job.id),
                message="Bulk upsert employee thành công",
            )

        return BaseResponse.fail(message="Bulk upsert employee thất bại")
