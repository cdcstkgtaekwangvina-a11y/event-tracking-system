import asyncio
import os
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from httpx import Response
from sqlmodel import and_, case, col, select, update

from database.models.app_db import get_session_factory
from database.models.employees import Employees
from database.models.events_employees import EVENT_EMPLOYEE_STATUS, EventsEmployees
from database.models.queue_jobs import JobStatus, QueueJob, QueueJobLogs
from src.shared.base.base_bg_task import BaseBackgroundTask
from src.shared.base.base_logger import get_logger
from src.shared.base.base_queue import queue_job, queue_service
from src.shared.constants.queue_keys import QueueKeys
from src.shared.helpers.time_extensions import get_now_utc
from src.shared.services.aws_ses import (
    EmailContent as AwsEmailContent,
    EmailRecipient as AwsEmailRecipient,
    SendBulkEmailResponse,
    SendMailRequest as AwsSendMailRequest,
    aws_ses,
)
from src.shared.services.elastic_email import (
    EmailContent as ElasticEmailContent,
    EmailRecipient as ElasticEmailRecipient,
    EmailStatusResponse,
    FailedRecipient as ElasticFailedRecipient,
    SendMailRequest as ElasticSendMailRequest,
    SendMailResponse,
    elastic_email,
)

load_dotenv()
logger = get_logger(__name__)

DELAY_TIME = 2
MAX_TRIES = 500


@queue_service.register_class
class SendEventMailBgTasks(BaseBackgroundTask):
    def __init__(self):
        self.default_email_service = (
            "aws_ses"
            if os.getenv("DEFAULT_EMAIL_SERVICE", "").strip().lower() == "aws_ses"
            else "elastic_email"
        )

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

    async def __update_fail_job(
        self, job_id: UUID, logs: QueueJobLogs, meta: dict[str, Any] | None = None
    ):
        await self.__update_queue_job(
            job_id, logs, JobStatus.FAILED, finished_at=get_now_utc(), meta=meta
        )
        return

    def parse_datetime(self, value: Any) -> tuple[str, str]:
        if value is None:
            return "", ""

        # 1. Nếu là chuỗi, cố gắng parse theo ISO hoặc định dạng VN/Custom
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return "", ""
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                try:
                    if " " in value:
                        if value.count(":") == 1:
                            value = datetime.strptime(value, "%d/%m/%Y %H:%M")
                        else:
                            value = datetime.strptime(value, "%d/%m/%Y %H:%M:%S")
                    else:
                        value = datetime.strptime(value, "%d/%m/%Y")
                except ValueError:
                    return "", ""

        # 2. Xử lý object datetime / date trực tiếp theo UTC
        if isinstance(value, (datetime, date)):
            date_str = value.strftime("%Y-%m-%d")
            time_str = (
                value.strftime("%H:%M:%S")
                if isinstance(value, datetime)
                else "00:00:00"
            )
            return date_str, time_str

        return "", ""

    async def __check_status_elastic_email(
        self, value: SendMailResponse
    ) -> EmailStatusResponse:
        """Name of status: submitted, complete, in_progress"""
        response = EmailStatusResponse()
        for _ in range(MAX_TRIES):
            response = await elastic_email.get_status_email(value.TransactionID)
            if response.Status == "complete":
                break
            await asyncio.sleep(DELAY_TIME)
        return response

    async def __check_status_aws_ses(
        self, value: SendBulkEmailResponse, employees: Sequence[Employees]
    ) -> EmailStatusResponse:
        """Process results returned from AWS SES SendBulkEmail"""
        response = EmailStatusResponse(
            RecipientsCount=len(employees),
            ID=value.BulkEmailEntryResults[0].MessageId
            if value.BulkEmailEntryResults
            else None,
        )
        failed_list: list[ElasticFailedRecipient] = []
        sent_list: list[str] = []
        delivered_list: list[str] = []
        msg_ids: list[str] = []

        for idx, entry_res in enumerate(value.BulkEmailEntryResults):
            emp_email = (
                employees[idx].email
                if idx < len(employees) and employees[idx].email
                else ""
            )
            if entry_res.Status == "SUCCESS" and emp_email:
                sent_list.append(emp_email)
                delivered_list.append(emp_email)
                if entry_res.MessageId:
                    msg_ids.append(entry_res.MessageId)
            else:
                failed_list.append(
                    ElasticFailedRecipient(
                        Address=emp_email,
                        Error=entry_res.Error or entry_res.Status,
                        ErrorCode=entry_res.Status,
                        Category="AWS_SES_ERROR",
                    )
                )

        response.Sent = sent_list
        response.SentCount = len(sent_list)
        response.Delivered = delivered_list
        response.DeliveredCount = len(delivered_list)
        response.Failed = failed_list
        response.FailedCount = len(failed_list)
        response.MessageIDs = msg_ids
        response.Status = (
            "complete"
            if response.FailedCount == 0
            else ("failed" if response.SentCount == 0 else "complete")
        )
        return response

    async def __send_via_elastic_email(
        self,
        employees: Sequence[Employees],
        event_dict: dict[str, Any],
        subject: str | None,
        template_name: str | None,
    ) -> tuple[
        SendMailResponse | None, EmailStatusResponse | None, dict[str, Any], str | None
    ]:
        """Attempt to send email via Elastic Email service"""
        recipients = [
            ElasticEmailRecipient(
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
        from_email = os.getenv("ELASTIC_EMAIL_FROM", "[EMAIL_ADDRESS]")
        content = ElasticEmailContent(
            Merge=event_dict,
            Subject=subject,
            TemplateName=template_name,
            From=from_email,
        )

        try:
            send_res = await elastic_email.send_email(
                ElasticSendMailRequest(Content=content, Recipients=recipients),
                jinja_data=event_dict,
            )
        except Exception as exc:
            logger.error(f"Elastic Email exception: {exc}")
            return None, None, {"elastic_email_error": str(exc)}, str(exc)

        if isinstance(send_res, Response):
            err_msg = (
                f"Elastic Email returned HTTP {send_res.status_code}: {send_res.text}"
            )
            logger.error(err_msg)
            return None, None, {"elastic_email_response": send_res.text}, err_msg

        if not isinstance(send_res, SendMailResponse):
            err_msg = "Elastic Email response invalid format"
            return None, None, {"elastic_email_response": str(send_res)}, err_msg

        meta = {"elastic_email_post_response": send_res.model_dump(mode="json")}
        status_res = await self.__check_status_elastic_email(send_res)
        meta["elastic_email_status_response"] = status_res.model_dump(mode="json")
        return send_res, status_res, meta, None

    async def __send_via_aws_ses(
        self,
        employees: Sequence[Employees],
        event_dict: dict[str, Any],
        subject: str | None,
        template_name: str | None,
    ) -> tuple[
        SendBulkEmailResponse | None,
        EmailStatusResponse | None,
        dict[str, Any],
        str | None,
    ]:
        """Attempt to send email via AWS SES service"""
        recipients = [
            AwsEmailRecipient(
                Email=e.email or "",
                Fields={
                    "name": e.name,
                    "department": e.department,
                    "email": e.email,
                    "position": e.position,
                    "user_id": str(e.id),
                    "qr_code_url": e.qr_url,
                },
            )
            for e in employees
        ]
        from_email = (
            os.getenv("AWS_SES_FROM")
            or os.getenv("AWS_SES_FROM_EMAIL")
            or os.getenv("ELASTIC_EMAIL_FROM", "[EMAIL_ADDRESS]")
        )
        content = AwsEmailContent(
            Merge=event_dict,
            Subject=subject,
            TemplateName=template_name,
            From=from_email,
        )

        try:
            send_res = await aws_ses.send_email(
                AwsSendMailRequest(Content=content, Recipients=recipients),
                jinja_data=event_dict,
            )
        except Exception as exc:
            logger.error(f"AWS SES exception: {exc}")
            return None, None, {"aws_ses_error": str(exc)}, str(exc)

        if isinstance(send_res, dict) and "error" in send_res:
            err_msg = f"AWS SES error: {send_res.get('error')}"
            logger.error(err_msg)
            return None, None, {"aws_ses_response": send_res}, err_msg

        if not isinstance(send_res, SendBulkEmailResponse):
            err_msg = "AWS SES response invalid format"
            return None, None, {"aws_ses_response": str(send_res)}, err_msg

        # Check if all entries failed
        all_failed = all(
            entry.Status != "SUCCESS" for entry in send_res.BulkEmailEntryResults
        )
        if all_failed and len(send_res.BulkEmailEntryResults) > 0:
            err_msg = f"AWS SES all entries rejected: {send_res.BulkEmailEntryResults[0].Error or send_res.BulkEmailEntryResults[0].Status}"
            return (
                None,
                None,
                {"aws_ses_response": send_res.model_dump(mode="json")},
                err_msg,
            )

        meta = {"aws_ses_post_response": send_res.model_dump(mode="json")}
        status_res = await self.__check_status_aws_ses(send_res, employees)
        meta["aws_ses_status_response"] = status_res.model_dump(mode="json")
        return send_res, status_res, meta, None

    @queue_job(QueueKeys.BULK_SEND_EVENT_EMAIL.value)
    async def bulk_send_event_email(
        self,
        job_id: UUID,
    ):
        async with get_session_factory()() as session:
            job = await self.get_job(session, job_id)
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
            if not send_all:
                employee_stmt = employee_stmt.where(col(Employees.id).in_(employees))

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

        # Determine order of services to attempt
        if self.default_email_service == "aws_ses":
            services_to_try = ["aws_ses", "elastic_email"]
        else:
            services_to_try = ["elastic_email", "aws_ses"]

        used_service: str | None = None
        send_email_status: EmailStatusResponse | None = None
        meta_data: dict[str, Any] = {
            "default_service": self.default_email_service,
            "tried_services": [],
        }

        for service_name in services_to_try:
            meta_data["tried_services"].append(service_name)
            logger.info(f"Đang gửi email thông qua {service_name} cho job {job_id}...")

            if service_name == "aws_ses":
                send_res, status_res, service_meta, err = await self.__send_via_aws_ses(
                    employees=employees,
                    event_dict=event_dict,
                    subject=subject,
                    template_name=template_name,
                )
            else:
                (
                    send_res,
                    status_res,
                    service_meta,
                    err,
                ) = await self.__send_via_elastic_email(
                    employees=employees,
                    event_dict=event_dict,
                    subject=subject,
                    template_name=template_name,
                )

            meta_data.update(service_meta)

            if err is not None or status_res is None:
                if job_logs.errors is None:
                    job_logs.errors = []
                job_logs.errors.append(
                    {
                        "service": service_name,
                        "error": err or f"Gửi qua {service_name} thất bại",
                    }
                )
                logger.warning(
                    f"Gửi qua {service_name} thất bại: {err}. Chuyển sang dịch vụ tiếp theo nếu có..."
                )
                continue

            # Success with this service
            used_service = service_name
            send_email_status = status_res
            meta_data["used_service"] = used_service
            logger.info(f"Gửi email thành công qua {service_name} cho job {job_id}")
            break

        await self.__update_queue_job(job_id=job_id, meta=meta_data)

        # Both services failed
        if not used_service or not send_email_status:
            if job_logs.errors is None:
                job_logs.errors = []
            job_logs.errors.append(
                {
                    "global_error": "Cả hai dịch vụ gửi email (AWS SES và Elastic Email) đều thất bại"
                }
            )
            await self.__update_fail_job(job_id, job_logs, meta=meta_data)
            return

        failed_email: set[str] = set()
        if send_email_status.Failed:
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

        now = get_now_utc()

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
                status=JobStatus.SUCCESS.value,
                logs=job_logs.model_dump(mode="json"),
                overall_log=f"Đã hoàn thành qua {used_service}: {len(success_emps)}/{send_email_status.RecipientsCount} thành công, {send_email_status.FailedCount} thất bại",
                meta=meta_data,
                finished_at=now,
                progress=100,
            )
        )

        async with get_session_factory()() as new_session:
            async with new_session.begin():
                await new_session.exec(update_emp_event)
                await new_session.exec(update_job)

        return
