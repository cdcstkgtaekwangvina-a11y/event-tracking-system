from sqlmodel.ext.asyncio.session import AsyncSession
from database.models.employees import Employees
from src.shared.base import BaseCrud, BaseResponse
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from .employee_schemas import EmployeeCreateRequest, EmployeeUpdateRequest


class EmployeeServices:
    session: AsyncSession
    crud: BaseCrud[Employees]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.crud = BaseCrud[Employees](session, Employees)

    async def create_employee(self, employee: EmployeeCreateRequest) -> BaseResponse[Employees]:
        new_employee = await self.crud.create(employee)
        return BaseResponse.created(new_employee, message="Thêm nhân viên thành công")

    async def get_employees(self, pagination: PaginationRequest) -> BaseResponse[PaginationResponse]:
        result = await self.crud.pagination_async(pagination)
        return BaseResponse.ok(result, message="Lấy danh sách nhân viên thành công")

    async def get_employee_by_id(self, employee_id: int) -> BaseResponse[Employees]:
        employee = await self.crud.find_by_id(employee_id)
        if not employee:
            return BaseResponse.not_found(message="Không tìm thấy nhân viên")
        return BaseResponse.ok(employee, message="Lấy chi tiết nhân viên thành công")

    async def update_employee(self, employee_id: int, employee_data: EmployeeUpdateRequest) -> BaseResponse[Employees]:
        db_obj = await self.crud.find_by_id(employee_id)
        if db_obj is None:
            return BaseResponse.not_found(message="Không tìm thấy nhân viên")

        # Hỗ trợ cập nhật một phần (PATCH-style)
        update_dict = employee_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return BaseResponse.ok(db_obj, message="Cập nhật thông tin nhân viên thành công")

    async def delete_employee(self, employee_id: int) -> BaseResponse[None]:
        deleted = await self.crud.delete(employee_id, is_soft_delete=True)
        if not deleted:
            return BaseResponse.not_found(message="Không tìm thấy nhân viên")
        return BaseResponse.ok(message="Xóa nhân viên thành công")
