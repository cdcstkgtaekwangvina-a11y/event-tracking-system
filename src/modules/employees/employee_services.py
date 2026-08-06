from typing import Any

from fastapi.responses import StreamingResponse

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
    ExportEmployeeRequest,
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
        # Nếu user nhập mã nhân viên, kiểm tra ID đã tồn tại chưa
        if employee.id is not None:
            existing = await self.crud.find_by_id(employee.id, soft_delete=False)
            if existing:
                return BaseResponse.error(
                    message=f"Mã nhân viên {employee.id:08d} đã tồn tại"
                )

        # Tạo dict dữ liệu, loại bỏ id nếu None để DB tự sinh
        create_data = employee.model_dump(exclude_none=True)
        new_employee = await self.crud.create(create_data)

        # Nếu tạo với custom ID, đồng bộ sequence để tránh xung đột
        if employee.id is not None:
            from sqlmodel import func, select as sql_select

            max_id_result = await self.session.exec(sql_select(func.max(Employees.id)))
            max_id = max_id_result.first()
            if max_id is not None:
                await self.session.exec(
                    sql_select(
                        func.setval(
                            func.pg_get_serial_sequence(Employees.__tablename__, "id"),
                            max_id,
                        )
                    )
                )
                await self.session.commit()

        await self.redis.invalidate_tags_async(CacheTags.EMPLOYEE)
        return BaseResponse.created(new_employee, message="Thêm nhân viên thành công")

    def _detect_sheet_file_type(self, file_url: str, file_bytes: bytes) -> str:
        clean_url = file_url.split("?")[0].lower()

        if (
            file_bytes.startswith(b"PK\x03\x04")
            or file_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
            or clean_url.endswith((".xlsx", ".xls"))
        ):
            return "excel"

        if file_bytes.strip().startswith((b"{", b"[")) or clean_url.endswith(".json"):
            return "json"

        if b"," in file_bytes[:2048] or clean_url.endswith(".csv"):
            return "csv"

        raise ValueError(
            "Định dạng file không được hỗ trợ. Hệ thống chỉ chấp nhận .xlsx, .xls, .csv, hoặc .json"
        )

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

    async def bulk_delete_employees(self, ids: list[int]) -> BaseResponse[dict]:
        delete_emps = await self.crud.delete(condition=lambda e: e.id.in_(ids))
        if delete_emps:
            await self.redis.invalidate_tags_async(CacheTags.EMPLOYEE)
            return BaseResponse.ok(message="Xóa nhân viên thành công")
        return BaseResponse.fail(message="Xóa nhân viên thất bại")

    async def bulk_upsert_employees(
        self, employees: BulkUpsertEmployeeRequest
    ) -> BaseResponse[BulkUpsertResponse]:
        import asyncio

        from src.modules.queue_job.queue_job_schemas import CreateQueueJobSchema
        from src.modules.queue_job.queue_job_services import QueueJobServices
        from src.shared.constants.queue_keys import QueueKeys

        # để phù hợp với thứ tự cột trong file excel của user
        if employees.header_row is not None and employees.header_row >= 1:
            employees.header_row -= 1

        job_service = QueueJobServices(session=self.session, redis=self.redis)
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
            asyncio.create_task(job.bulk_upsert_employees_db(new_job.id))
            return BaseResponse.ok(
                BulkUpsertResponse(job_id=new_job.id),
                message="Bulk upsert employee thành công",
            )

        return BaseResponse.fail(message="Bulk upsert employee thất bại")

    async def read_import_file(self, file: ReadSheetFile) -> BaseResponse[Any]:
        from src.shared.base.base_client import BaseClient

        async with BaseClient() as client:
            response = await client.get(file.url)
            file_bytes = response.content

        # 2. Nhận diện file type
        file_type = self._detect_sheet_file_type(file.url, file_bytes)

        header_row_index = file.header_row - 1 if file.header_row else None
        fh = FileHandelHelper()

        # 3. Phân nhánh đọc file dựa trên type
        if file_type == "json":
            df = fh.read_json(file_bytes)
        elif file_type in ("excel", "csv"):
            df = fh.read_sheet_file(
                file_bytes=file_bytes,
                type=file_type,
                analytics_file=True,
                header_row=header_row_index,
            )
        else:
            return BaseResponse.fail(message="Định dạng file không được hỗ trợ")

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

    async def export_employees(
        self, payload: ExportEmployeeRequest
    ) -> StreamingResponse | None:
        employees = await self.crud.select(Employees).find_many()
        if not employees:
            return None
        mapped_employees = []
        if payload.file_type == "json":
            mapped_employees = [emp.model_dump(mode="json") for emp in employees]
        else:
            mapped_employees = [
                {
                    "Mã nhân viên": emp.id,
                    "Họ và tên": emp.name,
                    "Email": emp.email,
                    "Khoa": emp.department,
                    "Giới tính": emp.gender,
                    "Chức vụ": emp.position,
                    "Ngày vào công ty": (
                        emp.starting_date.strftime("%d/%m/%Y")
                        if emp.starting_date
                        else None
                    ),
                }
                for emp in employees
            ]

        fh = FileHandelHelper()

        file_ext = "xlsx" if payload.file_type == "excel" else payload.file_type
        headers = {
            "Content-Disposition": f'attachment; filename="employees.{file_ext}"'
        }

        match payload.file_type:
            case "excel":
                media_type = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            case "csv":
                media_type = "text/csv"

            case "json":
                media_type = "application/json"

            case _:
                return BaseResponse.fail(message="Định dạng file không được hỗ trợ")

        from io import BytesIO

        file_bytes = fh.export_file(
            mapped_employees,
            payload.file_type,
            config={"pretty": True} if payload.file_type == "json" else {},
        )

        file_stream = BytesIO(file_bytes)

        return StreamingResponse(file_stream, media_type=media_type, headers=headers)
