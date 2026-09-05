import os
from datetime import datetime
from typing import Any, Literal

from src.shared.base.base_email_service import BaseEmailService


class SendEmailAuth(BaseEmailService):
    def __init__(
        self, default_email_service: Literal["aws_ses", "elastic_email"] | None = None
    ):
        self.default_email_service = default_email_service or os.getenv(
            "DEFAULT_EMAIL_SERVICE", "aws_ses"
        )

    async def __send_elastic_email(
        self,
        to_email: str,
        jinja_dict: dict[str, Any] = {},
        subject: str = "Event Tracking System",
    ) -> bool:
        from src.shared.services.elastic_email import (
            ElasticEmail,
            EmailContent,
            EmailRecipient,
            SendMailRequest,
            SendMailResponse,
        )

        from_email = (
            os.getenv("ELASTIC_EMAIL_FROM") or os.getenv("AWS_SES_FROM", "")
        ).strip("\"' ")
        elastic_email = ElasticEmail()
        sent = await elastic_email.send_email(
            req=SendMailRequest(
                Recipients=[EmailRecipient(Email=to_email)],
                Content=EmailContent(
                    Subject=subject,
                    From=from_email,
                ),
            ),
            jinja_data=jinja_dict,
            template="verify_auth",
        )
        if isinstance(sent, SendMailResponse):
            return True
        return False

    async def __send_aws_ses(
        self,
        to_email: str,
        jinja_dict: dict[str, Any] = {},
        subject: str = "Event Tracking System",
    ) -> bool:
        from src.shared.services.aws_ses import (
            AwsSes,
            EmailContent,
            EmailRecipient,
            SendBulkEmailResponse,
            SendMailRequest,
            SendMailResponse,
        )

        from_email = (
            os.getenv("AWS_SES_FROM")
            or os.getenv("AWS_SES_FROM_EMAIL")
            or os.getenv("ELASTIC_EMAIL_FROM", "")
        ).strip("\"' ")
        aws_ses = AwsSes()
        sent = await aws_ses.send_bulk_email(
            req=SendMailRequest(
                Recipients=[EmailRecipient(Email=to_email)],
                Content=EmailContent(
                    Subject=subject,
                    From=from_email,
                ),
            ),
            jinja_data=jinja_dict,
            template="verify_auth",
        )

        if (
            isinstance(sent, (SendBulkEmailResponse, SendMailResponse))
            and sent.BulkEmailEntryResults
        ):
            return any(r.Status == "SUCCESS" for r in sent.BulkEmailEntryResults)
        return False

    async def _core_send_email(
        self,
        to_email: str,
        jinja_dict: dict[str, Any] = {},
        subject: str = "Event Tracking System",
    ) -> bool:
        if self.default_email_service == "aws_ses":
            send_email = await self.__send_aws_ses(
                to_email=to_email, jinja_dict=jinja_dict, subject=subject
            )
            if not send_email:
                return await self.__send_elastic_email(
                    to_email=to_email, jinja_dict=jinja_dict, subject=subject
                )
            return send_email

        else:
            send_email = await self.__send_elastic_email(
                to_email=to_email, jinja_dict=jinja_dict, subject=subject
            )
            if not send_email:
                return await self.__send_aws_ses(
                    to_email=to_email, jinja_dict=jinja_dict, subject=subject
                )
            return send_email

    async def send_reset_password_email(
        self, to_email: str, new_password: str, user: dict[str, Any] = {}
    ):
        return await self._core_send_email(
            to_email=to_email,
            jinja_dict={**user, "password": new_password},
            subject="Đặt lại mật khẩu - Event Tracking System",
        )

    async def send_otp_email(
        self, to_email: str, otp: str, expired_at: datetime, user: dict[str, Any] = {}
    ):
        return await self._core_send_email(
            to_email=to_email,
            jinja_dict={**user, "otp": otp, "expired_at": expired_at},
            subject="Mã xác thực OTP - Event Tracking System",
        )


send_email_auth = SendEmailAuth()
