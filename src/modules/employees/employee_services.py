from database.models.app_db import SessionDep, SessionFactoryDep
from database.models.employees import Employees
from src.shared.base import BaseCrud, BaseResponse
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from .employee_schemas import (
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
    BulkUpsertResponse,
)
from typing import Any, Optional


class EmployeeServices:
    def __init__(self, session: SessionDep, session_factory: SessionFactoryDep):
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
        self, employees: list[Any]
    ) -> str:
        from src.shared.queues import QueueServices
        
        queue_service = QueueServices()
        job_id = await queue_service.enqueue_bulk_upsert_employees(employees)
        return job_id

    async def bulk_upsert_employees_db(
        self, employees: list[Employees]
    ) -> Optional[BulkUpsertResponse]:
        if not employees:
            return BulkUpsertResponse()

        incoming_ids = [e.id for e in employees if e.id is not None]

        async with self.session_factory() as session:
            from sqlmodel import col

            crud = BaseCrud(session=session, model=Employees)
            existing_employees = (
                await crud.select(Employees)
                .where(col(Employees.id).in_(incoming_ids))
                .find_many(soft_delete=False)
            )

            existing_ids = {e.id for e in existing_employees}

            added_instances = []
            updated_instances = []

            # 3. Phân loại và xử lý dữ liệu
            for emp in employees:
                if emp.id in existing_ids:
                    merged_emp = await session.merge(emp)
                    updated_instances.append(merged_emp)
                else:
                    session.add(emp)
                    added_instances.append(emp)

            # 4. Commit một lần duy nhất cho toàn bộ transaction
            await session.commit()

        return BulkUpsertResponse(
            updated_employees=updated_instances,
            added_employees=added_instances,
        )

