from typing import Any

from database.models.app_db import SessionDep, SessionFactoryDep
from database.models.employees import Employees
from src.shared.base import BaseCrud, BaseResponse
from src.shared.constants.cache_tags import CacheTags
from src.shared.helpers.file_handel import FileHandelHelper
from src.shared.schemas.pagination_schemas import PaginationRequest, PaginationResponse
from src.shared.services.redis_services import RedisDep

from .employee_schemas import (
    BulkUpsertEmployeeRequest,
    BulkUpsertResponse,
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
    ReadSheetFile,
)


class EmployeeServices:
    def __init__(
        self,
        session: SessionDep,
        session_factory: SessionFactoryDep,
        redis: RedisDep,
    ):
        self.session = session
        self.session_factory = session_factory
        self.redis = redis
        self.crud = BaseCrud(session, Employees)

    async def create_employee(
        self, employee: EmployeeCreateRequest
    ) -> BaseResponse[Employees]:
        new_employee = await self.crud.create(employee)
        await self.redis.invalidate_tags_async(CacheTags.EMPLOYEE)
        return BaseResponse.created(new_employee, message="Thêm nhân viên thành công")

    async def get_employees_raw(
        self, pagination: PaginationRequest
    ) -> PaginationResponse:
        cache_key = self.redis.get_pagination_key(CacheTags.EMPLOYEE, pagination)

        async def get_data_async():
            return await self.crud.pagination_async(
                pagination,
                search_fields=["name", "email", "department", "position"],
            )

        return await self.redis.get_or_set_async(
            key=cache_key,
            async_func=get_data_async,
            tags=[CacheTags.EMPLOYEE],
            model_class=PaginationResponse,
        )

    async def get_employees(
        self, pagination: PaginationRequest
    ) -> BaseResponse[PaginationResponse]:
        result = await self.get_employees_raw(pagination)
        return BaseResponse.ok(result, message="Lấy danh sách nhân viên thành công")

    async def get_employee_by_id_raw(self, employee_id: int) -> Employees | None:
        cache_key = f"{CacheTags.EMPLOYEE}:{employee_id}"

        async def get_data_async():
            return await self.crud.find_by_id(employee_id)

        return await self.redis.get_or_set_async(
            key=cache_key,
            async_func=get_data_async,
            tags=[CacheTags.EMPLOYEE],
            model_class=Employees,
        )

    async def get_employee_by_id(self, employee_id: int) -> BaseResponse[Employees]:
        employee = await self.get_employee_by_id_raw(employee_id)
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
        await self.redis.invalidate_tags_async(CacheTags.EMPLOYEE)
        return BaseResponse.ok(update_employee, message="Cập nhật nhân viên thành công")

    async def delete_employee(self, employee_id: int) -> BaseResponse[None]:
        deleted = await self.crud.delete(employee_id)
        if not deleted:
            return BaseResponse.not_found(message="Không tìm thấy nhân viên")
        await self.redis.invalidate_tags_async(CacheTags.EMPLOYEE)
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

    async def read_sheet_file(self, file: ReadSheetFile) -> BaseResponse[Any]:
        from src.shared.base.base_client import BaseClient

        async with BaseClient() as client:
            response = await client.get(file.url)
            file_bytes = response.content

        clean_url = file.url.split("?")[0].lower()

        # 2. Nhận diện file type
        if (
            file_bytes.startswith(b"PK\x03\x04")
            or file_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
            or clean_url.endswith((".xlsx", ".xls"))
        ):
            file_type = "excel"
        elif file_bytes.strip().startswith((b"{", b"[")) or clean_url.endswith(".json"):
            file_type = "json"
        else:
            file_type = "csv"

        header_row_index = file.header_row - 1 if file.header_row else None
        fh = FileHandelHelper()

        # 3. Phân nhánh đọc file dựa trên type
        if file_type == "json":
            df = fh.read_json(file_bytes)
        else:
            df = fh.read_sheet_file(
                file_bytes=file_bytes,
                type=file_type,
                analytics_file=True,
                header_row=header_row_index,
            )

        if df is None or df.is_empty():
            return BaseResponse.error(
                message="Không thể đọc dữ liệu từ file hoặc file trống"
            )

        # 4. Giới hạn số dòng preview
        if hasattr(file, "row_count") and file.row_count:
            df = df.head(file.row_count)

        headers = df.columns
        rows = df.to_dicts()

        return BaseResponse.ok(
            {
                "headers": headers,
                "rows": rows,
                "header_index": header_row_index if file_type != "json" else None,
                "file_type": file_type,
            },
            message="Read sheet file thành công",
        )

    async def export_employees(self) -> Any:
        import csv
        import io

        from fastapi.responses import Response

        employees = await self.crud.find_many()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "ID",
                "Họ và tên",
                "Email",
                "Phòng ban",
                "Chức vụ",
                "Giới tính",
                "Ngày bắt đầu",
            ]
        )

        for emp in employees:
            writer.writerow(
                [
                    emp.id,
                    emp.name or "",
                    emp.email or "",
                    emp.department or "",
                    emp.position or "",
                    emp.gender or "",
                    str(emp.starting_date) if emp.starting_date else "",
                ]
            )

        content = output.getvalue().encode("utf-8-sig")
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=danh_sach_nhan_vien.csv"
            },
        )
