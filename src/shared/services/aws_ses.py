import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import find_dotenv, load_dotenv
from pydantic import field_validator

from src.shared.base.base_email_service import BaseEmailService
from src.shared.base.base_logger import get_logger
from src.shared.base.base_schema import BaseSchema

load_dotenv(find_dotenv())
logger = get_logger(__name__)


# ==========================================
# Schema Definitions
# ==========================================


class MessageTag(BaseSchema):
    Name: str
    Value: str


class EmailRecipient(BaseSchema):
    Email: str
    Fields: dict[str, Any] | None = None
    Cc: list[str] | None = None
    Bcc: list[str] | None = None


class MessageAttachment(BaseSchema):
    FileName: str
    RawContent: str  # Base64 encoded or string
    ContentType: str | None = None
    ContentDescription: str | None = None
    ContentDisposition: str | None = None
    ContentId: str | None = None
    ContentTransferEncoding: str | None = None


class BulkEmailDestination(BaseSchema):
    ToAddresses: list[str]
    CcAddresses: list[str] | None = None
    BccAddresses: list[str] | None = None


class ReplacementTemplate(BaseSchema):
    ReplacementTemplateData: str | None = None

    @field_validator("ReplacementTemplateData", mode="before")
    @classmethod
    def _serialize_replacement_data(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        return str(v)


_ReplacementTemplate = ReplacementTemplate


class ReplacementEmailContent(BaseSchema):
    ReplacementTemplate: _ReplacementTemplate | None = None


_ReplacementEmailContent = ReplacementEmailContent


class BulkEmailEntry(BaseSchema):
    Destination: BulkEmailDestination
    ReplacementEmailContent: _ReplacementEmailContent | None = None
    ReplacementHeaders: list[dict[str, str]] | None = None
    ReplacementTags: list[MessageTag] | None = None


class TemplateContent(BaseSchema):
    Subject: str | None = None
    Html: str | None = None
    Text: str | None = None


_TemplateContent = TemplateContent


class EmailTemplate(BaseSchema):
    TemplateName: str | None = None
    TemplateArn: str | None = None
    TemplateData: str | None = None
    TemplateContent: _TemplateContent | None = None
    Headers: list[dict[str, str]] | None = None
    Attachments: list[MessageAttachment] | None = None

    @field_validator("TemplateData", mode="before")
    @classmethod
    def _serialize_template_data(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        return str(v)


class BulkEmailContent(BaseSchema):
    Template: EmailTemplate | None = None


class TrackingOptions(BaseSchema):
    ClickTrackingEnabled: str | None = None
    OpenTrackingEnabled: str | None = None


class ConfigurationOverrides(BaseSchema):
    Tracking: TrackingOptions | None = None


_ConfigurationOverrides = ConfigurationOverrides


class SendBulkEmailRequest(BaseSchema):
    BulkEmailEntries: list[BulkEmailEntry]
    DefaultContent: BulkEmailContent
    DefaultEmailTags: list[MessageTag] | None = None
    FromEmailAddress: str | None = None
    FromEmailAddressIdentityArn: str | None = None
    ReplyToAddresses: list[str] | None = None
    FeedbackForwardingEmailAddress: str | None = None
    FeedbackForwardingEmailAddressIdentityArn: str | None = None
    ConfigurationSetName: str | None = None
    ConfigurationOverrides: _ConfigurationOverrides | None = None
    EndpointId: str | None = None
    TenantName: str | None = None


# Simplified request models (matching ElasticEmail workflow)
class UtmModel(BaseSchema):
    Source: str | None = None
    Medium: str | None = None
    Campaign: str | None = None
    Content: str | None = None


class EmailContent(BaseSchema):
    Merge: dict[str, Any] | None = None
    Attachments: list[MessageAttachment] | None = None
    Headers: dict[str, str] | None = None
    From: str | None = None
    ReplyTo: str | None = None
    Subject: str | None = None
    TemplateName: str | None = None
    TemplateArn: str | None = None
    Html: str | None = None
    Text: str | None = None
    Utm: UtmModel | None = None


class EmailOptions(BaseSchema):
    ConfigurationSetName: str | None = None
    TrackOpens: bool | str | None = None
    TrackClicks: bool | str | None = None
    Tags: list[MessageTag] | None = None


class SendMailRequest(BaseSchema):
    Recipients: list[EmailRecipient]
    Content: EmailContent
    Options: EmailOptions | None = None


class BulkEmailStatus(str, Enum):
    SUCCESS = "SUCCESS"
    MESSAGE_REJECTED = "MESSAGE_REJECTED"
    MAIL_FROM_DOMAIN_NOT_VERIFIED = "MAIL_FROM_DOMAIN_NOT_VERIFIED"
    CONFIGURATION_SET_NOT_FOUND = "CONFIGURATION_SET_NOT_FOUND"
    TEMPLATE_NOT_FOUND = "TEMPLATE_NOT_FOUND"
    ACCOUNT_SUSPENDED = "ACCOUNT_SUSPENDED"
    ACCOUNT_SENDING_PAUSED = "ACCOUNT_SENDING_PAUSED"
    ACCOUNT_DAILY_QUOTA_EXCEEDED = "ACCOUNT_DAILY_QUOTA_EXCEEDED"
    INVALID_SENDING_POOL_NAME = "INVALID_SENDING_POOL_NAME"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    FAILED = "FAILED"


class BulkEmailEntryResult(BaseSchema):
    Status: str | None = None
    Error: str | None = None
    MessageId: str | None = None


class SendBulkEmailResponse(BaseSchema):
    BulkEmailEntryResults: list[BulkEmailEntryResult] = []


# Single/Legacy alias
class SendMailResponse(BaseSchema):
    BulkEmailEntryResults: list[BulkEmailEntryResult] = []
    MessageIDs: list[str] = []


# Insights Models
class BounceDetails(BaseSchema):
    BounceType: str | None = None
    BounceSubType: str | None = None
    DiagnosticCode: str | None = None


class ComplaintDetails(BaseSchema):
    ComplaintSubType: str | None = None
    ComplaintFeedbackType: str | None = None


class InsightEventDetails(BaseSchema):
    Bounce: BounceDetails | None = None
    Complaint: ComplaintDetails | None = None


class InsightEvent(BaseSchema):
    Timestamp: float | int | datetime | str | None = None
    Type: str | None = None
    Details: InsightEventDetails | None = None


class EmailInsightDestination(BaseSchema):
    Destination: str | None = None
    Isp: str | None = None
    Events: list[InsightEvent] = []


class MessageInsightsResponse(BaseSchema):
    MessageId: str | None = None
    FromEmailAddress: str | None = None
    Subject: str | None = None
    EmailTags: list[MessageTag] = []
    Insights: list[EmailInsightDestination] = []


class FailedRecipient(BaseSchema):
    Address: str | None = None
    Error: str | None = None
    ErrorCode: str | None = None
    Category: str | None = None


class EmailStatusResponse(BaseSchema):
    ID: str | None = None
    Status: str | None = None
    RecipientsCount: int = 0
    Failed: list[FailedRecipient] = []
    FailedCount: int = 0
    Sent: list[str] = []
    SentCount: int = 0
    Delivered: list[str] = []
    DeliveredCount: int = 0
    Pending: list[str] = []
    PendingCount: int = 0
    Opened: list[str] = []
    OpenedCount: int = 0
    Clicked: list[str] = []
    ClickedCount: int = 0
    Unsubscribed: list[str] = []
    UnsubscribedCount: int = 0
    AbuseReports: list[str] = []
    AbuseReportsCount: int = 0
    MessageIDs: list[str] = []


# ==========================================
# AWS SES Service Implementation
# ==========================================


class AwsSes(BaseEmailService):
    """
    AWS Simple Email Service (SES) v2 client using aioboto3.
    Provides identical interface and workflows to ElasticEmail.
    """

    def __init__(
        self,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        region_name: str | None = None,
        default_from_email: str | None = None,
        configuration_set_name: str | None = None,
    ):
        self.access_key = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key = aws_secret_access_key or os.getenv(
            "AWS_SECRET_ACCESS_KEY", ""
        )
        self.session_token = aws_session_token or os.getenv("AWS_SESSION_TOKEN", None)
        self.region = (
            region_name
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        )
        self.default_from_email = (
            default_from_email
            or os.getenv("AWS_SES_FROM_EMAIL")
            or os.getenv("AWS_SES_FROM")
            or os.getenv("ELASTIC_EMAIL_FROM", "")
        )
        self.configuration_set_name = configuration_set_name or os.getenv(
            "AWS_SES_CONFIGURATION_SET", None
        )
        self._session = aioboto3.Session()

    @asynccontextmanager
    async def _get_client(self) -> AsyncGenerator[Any, None]:
        """
        Creates an asynchronous AWS SES v2 client session.
        """
        client_kwargs: dict[str, Any] = {
            "region_name": self.region,
        }
        if self.access_key:
            client_kwargs["aws_access_key_id"] = self.access_key
        if self.secret_key:
            client_kwargs["aws_secret_access_key"] = self.secret_key
        if self.session_token:
            client_kwargs["aws_session_token"] = self.session_token

        client_context: Any = self._session.client("sesv2", **client_kwargs)
        async with client_context as client:
            yield client

    # --------------------------------------------------------------------------
    # Email Sending Methods
    # --------------------------------------------------------------------------
    async def send_bulk_email(
        self,
        req: SendBulkEmailRequest | SendMailRequest,
        jinja_data: dict[str, Any] = {},
    ) -> SendBulkEmailResponse | dict[str, Any]:
        """
        Sends email in bulk via AWS SES v2 send_bulk_email API.
        Supports both direct SES v2 format and simplified ElasticEmail-compatible format.
        """
        try:
            if isinstance(req, SendBulkEmailRequest):
                payload = req.model_dump(exclude_none=True)
            else:
                from_email = req.Content.From or self.default_from_email
                if not from_email:
                    raise ValueError("FromEmailAddress is required")

                rendered_html = req.Content.Html or ""
                if not req.Content.TemplateName:
                    rendered_html = self._get_email_template(data=jinja_data, email_service="aws_ses")

                default_template_data = (
                    json.dumps(req.Content.Merge)
                    if req.Content.Merge is not None
                    else "{}"
                )

                template_content = None
                if not req.Content.TemplateName:
                    template_content = TemplateContent(
                        Subject=req.Content.Subject or "",
                        Html=rendered_html,
                        Text=req.Content.Text or "",
                    )

                default_content = BulkEmailContent(
                    Template=EmailTemplate(
                        TemplateName=req.Content.TemplateName,
                        TemplateArn=req.Content.TemplateArn,
                        TemplateData=default_template_data,
                        TemplateContent=template_content,
                        Attachments=req.Content.Attachments,
                    )
                )

                bulk_entries: list[BulkEmailEntry] = []
                for recipient in req.Recipients:
                    replacement_content = None
                    if recipient.Fields is not None:
                        replacement_content = ReplacementEmailContent(
                            ReplacementTemplate=ReplacementTemplate(
                                ReplacementTemplateData=json.dumps(recipient.Fields)
                            )
                        )

                    entry = BulkEmailEntry(
                        Destination=BulkEmailDestination(
                            ToAddresses=[recipient.Email],
                            CcAddresses=recipient.Cc,
                            BccAddresses=recipient.Bcc,
                        ),
                        ReplacementEmailContent=replacement_content,
                    )
                    bulk_entries.append(entry)

                config_overrides = None
                config_set = (
                    req.Options.ConfigurationSetName
                    if req.Options and req.Options.ConfigurationSetName
                    else self.configuration_set_name
                )
                if req.Options and (
                    req.Options.TrackOpens is not None
                    or req.Options.TrackClicks is not None
                ):
                    config_overrides = ConfigurationOverrides(
                        Tracking=TrackingOptions(
                            OpenTrackingEnabled=str(req.Options.TrackOpens).upper()
                            if req.Options.TrackOpens is not None
                            else None,
                            ClickTrackingEnabled=str(req.Options.TrackClicks).upper()
                            if req.Options.TrackClicks is not None
                            else None,
                        )
                    )

                bulk_request = SendBulkEmailRequest(
                    FromEmailAddress=from_email,
                    ReplyToAddresses=[req.Content.ReplyTo]
                    if req.Content.ReplyTo
                    else None,
                    DefaultContent=default_content,
                    BulkEmailEntries=bulk_entries,
                    ConfigurationSetName=config_set,
                    ConfigurationOverrides=config_overrides,
                    DefaultEmailTags=req.Options.Tags if req.Options else None,
                )
                payload = bulk_request.model_dump(exclude_none=True)

            async with self._get_client() as client:
                response = await client.send_bulk_email(**payload)
                return SendBulkEmailResponse(**response)

        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error(f"AWS SES send_bulk_email failed: {exc}")
            if isinstance(exc, ClientError):
                error_info = exc.response.get("Error", {})
                return {
                    "error": error_info.get("Message", str(exc)),
                    "code": error_info.get("Code", "ClientError"),
                }
            return {"error": str(exc), "code": "UnknownError"}

    async def send_email(
        self,
        req: SendMailRequest,
        jinja_data: dict[str, Any] = {},
    ) -> SendBulkEmailResponse | dict[str, Any]:
        """
        Alias for send_bulk_email to provide 100% API compatibility with ElasticEmail.
        """
        return await self.send_bulk_email(req=req, jinja_data=jinja_data)

    # --------------------------------------------------------------------------
    # Message Insights and Status Tracking
    # --------------------------------------------------------------------------
    async def get_message_insights(
        self, message_id: str
    ) -> MessageInsightsResponse | dict[str, Any]:
        """
        Retrieves detailed delivery insights and events for a specific MessageId
        via AWS SES v2 get_message_insights API.
        """
        clean_msg_id = message_id.strip("<>")
        try:
            async with self._get_client() as client:
                response = await client.get_message_insights(MessageId=clean_msg_id)
                return MessageInsightsResponse(**response)
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error(
                f"AWS SES get_message_insights failed for {clean_msg_id}: {exc}"
            )
            if isinstance(exc, ClientError):
                error_info = exc.response.get("Error", {})
                return {
                    "error": error_info.get("Message", str(exc)),
                    "code": error_info.get("Code", "ClientError"),
                }
            return {"error": str(exc), "code": "UnknownError"}

    async def get_status_email(self, message_id: str) -> EmailStatusResponse:
        """
        Unified status helper returning standard EmailStatusResponse from SES Message Insights.
        """
        res = await self.get_message_insights(message_id=message_id)
        if isinstance(res, dict):
            return EmailStatusResponse(
                ID=message_id,
                Status="failed",
                RecipientsCount=1,
                FailedCount=1,
                Failed=[
                    FailedRecipient(
                        Error=res.get("error", "Unknown error"),
                        ErrorCode=res.get("code", "500"),
                    )
                ],
            )

        status_response = EmailStatusResponse(
            ID=res.MessageId or message_id,
            MessageIDs=[res.MessageId] if res.MessageId else [message_id],
        )

        for insight in res.Insights:
            recipient_email = insight.Destination or ""
            status_response.RecipientsCount += 1

            events = insight.Events or []
            event_types = {e.Type.upper() for e in events if e.Type}

            if "BOUNCE" in event_types or "COMPLAINT" in event_types:
                bounce_err = ""
                for ev in events:
                    if ev.Details and ev.Details.Bounce:
                        bounce_err = (
                            ev.Details.Bounce.DiagnosticCode
                            or ev.Details.Bounce.BounceSubType
                            or "Bounce"
                        )
                    elif ev.Details and ev.Details.Complaint:
                        bounce_err = (
                            ev.Details.Complaint.ComplaintFeedbackType or "Complaint"
                        )

                status_response.Failed.append(
                    FailedRecipient(
                        Address=recipient_email,
                        Error=bounce_err or "Delivery Failed",
                        Category="Bounce/Complaint",
                    )
                )
                status_response.FailedCount += 1
            elif "DELIVERY" in event_types:
                status_response.Delivered.append(recipient_email)
                status_response.DeliveredCount += 1
                status_response.Sent.append(recipient_email)
                status_response.SentCount += 1
            elif "SEND" in event_types:
                status_response.Sent.append(recipient_email)
                status_response.SentCount += 1
            else:
                status_response.Pending.append(recipient_email)
                status_response.PendingCount += 1

            if "OPEN" in event_types:
                status_response.Opened.append(recipient_email)
                status_response.OpenedCount += 1

            if "CLICK" in event_types:
                status_response.Clicked.append(recipient_email)
                status_response.ClickedCount += 1

        if status_response.FailedCount > 0 and status_response.DeliveredCount == 0:
            status_response.Status = "failed"
        elif (
            status_response.DeliveredCount + status_response.FailedCount
            >= status_response.RecipientsCount
            and status_response.RecipientsCount > 0
        ):
            status_response.Status = "complete"
        elif status_response.SentCount > 0:
            status_response.Status = "in_progress"
        else:
            status_response.Status = "submitted"

        return status_response

    # --------------------------------------------------------------------------
    # Template Management Methods
    # --------------------------------------------------------------------------
    async def get_templates(
        self, next_token: str | None = None, page_size: int = 50
    ) -> dict[str, Any]:
        """
        Lists email templates available in AWS SES v2.
        """
        kwargs: dict[str, Any] = {"PageSize": page_size}
        if next_token:
            kwargs["NextToken"] = next_token

        try:
            async with self._get_client() as client:
                return await client.list_email_templates(**kwargs)
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error(f"AWS SES get_templates failed: {exc}")
            return {"error": str(exc)}

    async def get_template(self, template_name: str) -> dict[str, Any]:
        """
        Gets template details for a specific template name.
        """
        try:
            async with self._get_client() as client:
                return await client.get_email_template(TemplateName=template_name)
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error(f"AWS SES get_template failed for {template_name}: {exc}")
            return {"error": str(exc)}


aws_ses = AwsSes()
