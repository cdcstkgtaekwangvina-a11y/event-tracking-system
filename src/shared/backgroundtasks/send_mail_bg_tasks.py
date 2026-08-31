import asyncio
import os
from datetime import date, datetime
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from sqlmodel import and_, case, col, select, update

from database.models.app_db import get_session_factory
from database.models.employees import Employees
from database.models.events_employees import EVENT_EMPLOYEE_STATUS, EventsEmployees
from database.models.queue_jobs import JobStatus, QueueJob, QueueJobLogs
from src.shared.base.base_queue import queue_job, queue_service
from src.shared.constants.queue_keys import QueueKeys
from src.shared.helpers.random_helpers import get_now_vn
from src.shared.services.elastic_email import (
    EmailContent,
    EmailRecipient,
    EmailStatusResponse,
    SendMailRequest,
    SendMailResponse,
    elastic_email,
)

load_dotenv()

DELAY_TIME = 2
MAX_TRIES = 500


@queue_service.register_class
class SendMailBgTasks:
    async def __update_queue_job(
        self,
        job_id: UUID,
        logs: QueueJobLogs | None = None,
        status: JobStatus | None = None,
        meta: dict[str, Any] | None = None,
        overall_log: str | None = None,
        progress: int | None = None,
        finished_at: datetime | None = None,
    ):
        async with get_session_factory()() as session:
            values: dict[str, Any] = {}

            if logs is not None:
                values["logs"] = logs.model_dump(mode="json")

            if status is not None:
                values["status"] = status.value

            if meta is not None:
                values["meta"] = meta

            if overall_log is not None:
                values["overall_log"] = overall_log

            if progress is not None:
                values["progress"] = progress

            if finished_at is not None:
                values["finished_at"] = finished_at

            await session.exec(
                update(QueueJob).where(col(QueueJob.id) == job_id).values(values)
            )

            await session.commit()
        return

    async def __update_fail_job(self, job_id: UUID, logs: QueueJobLogs):
        await self.__update_queue_job(
            job_id, logs, JobStatus.FAILED, finished_at=get_now_vn()
        )
        return

    def parse_datetime(self, value: Any) -> tuple[str, str]:
        if value is None:
            return "", ""

        # 1. Nếu là chuỗi, cố gắng parse theo định dạng VN/Custom
        if isinstance(value, str):
            value = value.strip()
            try:
                # Thử parse định dạng đầy đủ: "dd/mm/yyyy hh:mm:ss" hoặc "dd/mm/yyyy hh:mm"
                if " " in value:
                    # Kiểm tra số lượng dấu hai chấm để khớp số giây
                    if value.count(":") == 1:
                        value = datetime.strptime(value, "%d/%m/%Y %H:%M")
                    else:
                        value = datetime.strptime(value, "%d/%m/%Y %H:%M:%S")
                else:
                    # Thử parse nếu chỉ có ngày: "dd/mm/yyyy"
                    value = datetime.strptime(value, "%d/%m/%Y")
            except ValueError:
                return "", ""

        # 2. Kiểm tra nếu là đối tượng datetime hoặc date hợp lệ để xuất chuỗi chuẩn
        if isinstance(value, (datetime, date)):
            date_str = value.strftime("%Y-%m-%d")

            # Nếu là datetime -> lấy giờ; nếu chỉ là date -> mặc định "00:00:00"
            time_str = (
                value.strftime("%H:%M:%S")
                if isinstance(value, datetime)
                else "00:00:00"
            )

            return date_str, time_str

        return "", ""

    async def __check_status_email(
        self, value: SendMailResponse
    ) -> EmailStatusResponse:
        """Name of status: submitted, complete, in_progress"""
        response: EmailStatusResponse
        for i in range(MAX_TRIES):
            response = await elastic_email.get_status_email(value.TransactionID)
            if response.Status == "complete":
                break
            await asyncio.sleep(DELAY_TIME)
        return response

    @queue_job(QueueKeys.BULK_SEND_EMAIL.value)
    async def bulk_send_email(
        self,
        job_id: UUID,
    ):
        async with get_session_factory()() as session:
            query_job = await session.exec(
                select(QueueJob).where(
                    and_(
                        QueueJob.id == job_id,
                        QueueJob.status == JobStatus.RUNNING.value,
                    )
                )
            )
            job = query_job.first()
            if not job:
                return

            job_logs = (
                QueueJobLogs(**job.logs)
                if job.logs
                else QueueJobLogs(errors=[], logs=[])
            )

            next_payload = job.next_payload
            if not next_payload:
                if job_logs.errors is None:
                    job_logs.errors = []
                job_logs.errors.append(
                    {"global_error": "Không có thông tin để gửi mail"}
                )
                await self.__update_fail_job(job_id, job_logs)
                return

            subject = next_payload.get("subject", None)
            send_all = next_payload.get("send_all", False)
            employees = next_payload.get("employees", [])
            event = next_payload.get("event", None)
            event_id = next_payload.get("event_id", None)
            template_name = next_payload.get("template_name", None)

            if (
                (not send_all and len(employees) == 0)
                or event is None
                or event_id is None
            ):
                if job_logs.errors is None:
                    job_logs.errors = []

                if not send_all and len(employees) == 0:
                    job_logs.errors.append(
                        {"global_error": "Không có khách mời để gửi mail"}
                    )

                if event is None or event_id is None:
                    job_logs.errors.append(
                        {"global_error": "Không có thông tin sự kiện"}
                    )
                await self.__update_fail_job(job_id, job_logs)
                return

            employee_stmt = (
                select(Employees)
                .join(
                    EventsEmployees,
                    col(EventsEmployees.employee_id) == col(Employees.id),
                )
                .where(
                    and_(
                        col(EventsEmployees.event_id) == event_id,
                        col(Employees.email).is_not(None),
                    )
                )
            )
            if send_all:
                employee_stmt = employee_stmt.where(col(Employees.email).is_not(None))
            else:
                employee_stmt = employee_stmt.where(
                    and_(
                        col(Employees.id).in_(employees),
                        col(Employees.email).is_not(None),
                    )
                )

            employee_exec = await session.exec(employee_stmt)
            employees = employee_exec.all()

        if not employees or len(employees) == 0:
            if job_logs.errors is None:
                job_logs.errors = []
            job_logs.errors.append(
                {"global_error": "Không có khách mời nào phù hợp để gửi mail"}
            )

            await self.__update_fail_job(job_id, job_logs)
            return

        recipients = [
            EmailRecipient(
                Email=e.email or "",
                Fields={
                    "name": e.name,
                    "department": e.department,
                    "email": e.email,
                    "position": e.position,
                    "user_id": e.id,
                    "qr_code_url": e.qr_url,
                },
            )
            for e in employees
        ]

        start_date_part, start_time_part = self.parse_datetime(
            event.get("start_at", "")
        )
        end_date_part, end_time_part = self.parse_datetime(event.get("end_at", ""))
        event_dict = {
            "event_name": event.get("name"),
            "event_date": start_date_part
            if start_date_part == end_date_part
            else f"{start_date_part} - {end_date_part}",
            "event_time": f"{start_time_part} - {end_time_part}",
            "event_location": event.get("location"),
            "url_map": event.get("url_map"),
            "event_description": event.get("description"),
            "event_image": event.get("url_image"),
        }
        content = EmailContent(
            Merge=event_dict,
            Subject=subject,
            TemplateName=template_name,
            From=os.getenv("ELASTIC_EMAIL_FROM", "[EMAIL_ADDRESS]"),
        )
        send_email = await elastic_email.send_email(
            SendMailRequest(Content=content, Recipients=recipients),
            jinja_data=event_dict,
        )
        meta_data = {"post_response": send_email.model_dump(mode="json")}
        await self.__update_queue_job(job_id=job_id, meta=meta_data)

        send_email_status = await self.__check_status_email(send_email)
        meta_data["transaction_response"] = send_email_status.model_dump(mode="json")

        failed_email: set[str] = set()

        if send_email_status and send_email_status.Failed:
            if job_logs.errors is None:
                job_logs.errors = []

            for failed in send_email_status.Failed:
                job_logs.errors.append(failed.model_dump(mode="json"))
                if failed.Address:
                    failed_email.add(failed.Address.lower())

        success_emps = []
        failed_emps = []
        all_emp_ids = []

        for e in employees:
            all_emp_ids.append(e.id)
            if e.email and e.email.lower() in failed_email:
                failed_emps.append(e.id)
            else:
                success_emps.append(e.id)

        now = get_now_vn()

        update_emp_event = (
            update(EventsEmployees)
            .where(
                and_(
                    col(EventsEmployees.event_id) == event_id,
                    col(EventsEmployees.employee_id).in_(all_emp_ids),
                )
            )
            .values(
                status=case(
                    (
                        col(EventsEmployees.employee_id).in_(failed_emps),
                        EVENT_EMPLOYEE_STATUS.SEND_FAIL.value,
                    ),
                    else_=EVENT_EMPLOYEE_STATUS.SENT.value,
                ),
                send_at=now,
            )
        )

        update_job = (
            update(QueueJob)
            .where(col(QueueJob.id) == job_id)
            .values(
                job_id=job_id,
                logs=job_logs,
                overall_log=f"Đã hoàn thành có {len(success_emps)}/{send_email_status.RecipientsCount} thành công, {send_email_status.FailedCount} thất bại",
                meta=meta_data,
            )
        )

        async with session.begin():
            await session.exec(update_emp_event)
            await session.exec(update_job)

        return
