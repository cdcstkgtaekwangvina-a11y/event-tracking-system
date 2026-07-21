import io
import math
import os
from datetime import date, datetime
from typing import cast
from uuid import UUID

import httpx
import polars as pl

from database.models.app_db import get_session_factory
from database.models.employees import Employees
from database.models.queue_jobs import JobStatus, QueueJob, QueueJobLogs
from src.modules.employees.employee_schemas import BulkUpsertResponse
from src.shared.base.base_queue import queue_job, queue_service
from src.shared.constants.queue_keys import QueueKeys
from src.shared.helpers.random_helpers import get_now_vn

MAX_DETAILED_ERRORS = 500


@queue_service.register_class
class EmployeeBackgroundTask:
    def __init__(self):
        self.BATCH_SIZE = 1000

    async def _download_and_parse_file(
        self, file_url: str, header_row: int | None = None
    ) -> pl.DataFrame:
        """Tải file từ URL với Timeout 60s, tự động nhận diện định dạng."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(file_url)
            response.raise_for_status()
            file_bytes = response.content

        content_type = response.headers.get("content-type", "").lower()
        url_path = file_url.split("?")[0]
        _, ext = os.path.splitext(url_path.lower())

        if "spreadsheetml" in content_type or ext == ".xlsx":
            read_options = (
                {"header_row": header_row} if header_row is not None else None
            )
            return pl.read_excel(io.BytesIO(file_bytes), read_options=read_options)

        elif "csv" in content_type or ext == ".csv":
            csv_kwargs = {}
            if header_row is not None:
                csv_kwargs["skip_rows"] = header_row
            return pl.read_csv(io.BytesIO(file_bytes), **csv_kwargs)

        elif "json" in content_type or ext == ".json":
            return pl.read_json(io.BytesIO(file_bytes))
        else:
            raise ValueError(
                f"Định dạng file không được hỗ trợ (Content-Type: {content_type}, Ext: {ext}). "
                f"Hệ thống chỉ chấp nhận file .csv, .xlsx, hoặc .json"
            )

    @queue_job(QueueKeys.BULK_UPSERT_EMPLOYEES.value)
    async def bulk_upsert_employees_db(
        self,
        job_id: UUID,
    ) -> BulkUpsertResponse | None:

        async with get_session_factory()() as session:
            job = await session.get(QueueJob, job_id)
            if not job:
                return

            job_logs = (
                QueueJobLogs(**job.logs)
                if job.logs
                else QueueJobLogs(errors=[], logs=[])
            )

            # 1. Validate payload
            next_payload = job.next_payload
            file_url = next_payload.get("file_url") if next_payload else None

            if not next_payload or not file_url:
                job.status = JobStatus.FAILED
                job.finished_at = get_now_vn()
                cast(list, job_logs.errors).append(
                    {
                        "global_error": "Dữ liệu payload trống hoặc thiếu đường dẫn file_url"
                    }
                )
                job.logs = job_logs.model_dump()
                await session.commit()
                return

            # 2. Cập nhật RUNNING
            job.status = JobStatus.RUNNING
            await session.commit()

            try:
                column_map = next_payload.get("column_map")
                header_row = next_payload.get("header_row")

                df = await self._download_and_parse_file(
                    file_url, header_row=header_row
                )

                if column_map:
                    valid_map = {k: v for k, v in column_map.items() if k in df.columns}
                    if valid_map:
                        df = df.rename(valid_map)

                total_records = len(df)
                base_row_offset = (header_row if header_row is not None else 0) + 2
                successful_rows_count = 0

                # 3. Vòng lặp Batching
                for i in range(0, total_records, self.BATCH_SIZE):
                    chunk_df = df.slice(i, self.BATCH_SIZE)
                    chunk_dicts = chunk_df.to_dicts()

                    batch_errors = []
                    validated_chunk_data = []

                    # Bước A: Ép kiểu & Chuẩn hóa
                    for idx, data in enumerate(chunk_dicts):
                        row_number = i + idx + base_row_offset
                        try:
                            # Parse ID
                            if (
                                "id" in data
                                and data["id"] is not None
                                and str(data["id"]).strip() != ""
                            ):
                                try:
                                    data["id"] = int(float(str(data["id"]).strip()))
                                except (ValueError, TypeError):
                                    raise ValueError(
                                        f"Trường 'id' không đúng định dạng số nguyên: {data['id']}"
                                    )
                            else:
                                data["id"] = None

                            # 🔥 FIX 2: Tối ưu parse date linh hoạt hơn (cắt bỏ phần T00:00:00 nếu có)
                            if (
                                "starting_date" in data
                                and data["starting_date"] is not None
                            ):
                                raw_date = data["starting_date"]

                                if isinstance(raw_date, str):
                                    raw_date = (
                                        raw_date.strip().split("T")[0].split(" ")[0]
                                    )
                                    if raw_date == "" or raw_date.lower() in (
                                        "null",
                                        "none",
                                    ):
                                        data["starting_date"] = None
                                    else:
                                        try:
                                            if "-" in raw_date:
                                                data["starting_date"] = (
                                                    datetime.strptime(
                                                        raw_date, "%Y-%m-%d"
                                                    ).date()
                                                )
                                            elif "/" in raw_date:
                                                data["starting_date"] = (
                                                    datetime.strptime(
                                                        raw_date, "%d/%m/%Y"
                                                    ).date()
                                                )
                                            else:
                                                data["starting_date"] = (
                                                    date.fromisoformat(raw_date)
                                                )
                                        except ValueError:
                                            raise ValueError(
                                                f"Trường 'starting_date' không đúng định dạng ngày: {raw_date}"
                                            )
                                elif isinstance(raw_date, datetime):
                                    data["starting_date"] = raw_date.date()

                            validated_chunk_data.append((row_number, data))

                        except Exception as parse_err:
                            batch_errors.append(
                                {
                                    "row": row_number,
                                    "employee_id": str(data.get("id"))
                                    if data.get("id")
                                    else "N/A",
                                    "reason": str(parse_err),
                                }
                            )

                    # Bước B: Check Existing IDs
                    incoming_ids = [
                        d["id"]
                        for _, d in validated_chunk_data
                        if d.get("id") is not None
                    ]

                    existing_ids = set()
                    if incoming_ids:
                        from sqlmodel import col

                        from src.shared.base.base_crud import BaseCrud

                        crud = BaseCrud(session=session, model=Employees)
                        existing_employees = (
                            await crud.select(Employees)
                            .where(col(Employees.id).in_(incoming_ids))
                            .find_many(soft_delete=False)
                        )
                        existing_ids = {e.id for e in existing_employees}

                    # Bước C: Upsert với Savepoint
                    for row_number, data in validated_chunk_data:
                        try:
                            async with session.begin_nested():
                                emp = Employees(**data)
                                if emp.id in existing_ids:
                                    await session.merge(emp)
                                else:
                                    session.add(emp)
                                await session.flush()
                                successful_rows_count += 1
                        except Exception as db_err:
                            batch_errors.append(
                                {
                                    "row": row_number,
                                    "employee_id": str(data.get("id"))
                                    if data.get("id")
                                    else "N/A",
                                    "reason": str(db_err),
                                }
                            )
                            continue

                    # 4. Cập nhật Progress & Logs
                    processed_count = min(i + self.BATCH_SIZE, total_records)
                    job.progress = math.floor((processed_count / total_records) * 100)

                    # 🔥 FIX 3: Khống chế kích thước errors log tối đa MAX_DETAILED_ERRORS dòng
                    if batch_errors:
                        current_errors_count = len(job_logs.errors or [])
                        if current_errors_count < MAX_DETAILED_ERRORS:
                            allowed_slots = MAX_DETAILED_ERRORS - current_errors_count
                            cast(list, job_logs.errors).extend(
                                batch_errors[:allowed_slots]
                            )

                        job.logs = job_logs.model_dump()

                    session.add(job)
                    await session.commit()

                    # 🔥 FIX 4: Giải phóng bộ nhớ RAM an toàn cho Batch tiếp theo mà không lỡ expunge `job`
                    session.expire_all()

                # 5. Tổng kết sau khi chạy xong tất cả các batch
                total_failed = total_records - successful_rows_count

                cast(list, job_logs.logs).append(
                    {
                        "total": total_records,
                        "success": successful_rows_count,
                        "failed": total_failed,
                    }
                )

                if total_records > 0 and successful_rows_count == 0:
                    job.status = JobStatus.FAILED
                    cast(list, job_logs.errors).append(
                        {
                            "global_error": f"Toàn bộ {total_records} bản ghi đều bị lỗi. Không có dữ liệu nào được nhập."
                        }
                    )
                elif total_failed > 0:
                    job.status = getattr(
                        JobStatus, "PARTIAL_SUCCESS", JobStatus.SUCCESS
                    )
                else:
                    job.status = JobStatus.SUCCESS

                job.progress = 100
                job.finished_at = get_now_vn()
                job.logs = job_logs.model_dump()
                await session.commit()

            except Exception as global_err:
                job.status = JobStatus.FAILED
                job.finished_at = get_now_vn()
                cast(list, job_logs.errors).append({"global_error": str(global_err)})
                job.logs = job_logs.model_dump()

                await session.commit()
                raise global_err
