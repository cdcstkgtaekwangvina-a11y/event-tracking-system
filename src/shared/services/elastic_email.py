import os
from enum import Enum
from typing import Any

from dotenv import find_dotenv, load_dotenv

from src.shared.base.base_client import BaseClient
from src.shared.base.base_email_service import BaseEmailService
from src.shared.base.base_schema import BaseSchema

load_dotenv(find_dotenv())

BASE_URL = "https://api.elasticemail.com"
SEND_EMAIL_PATH = "/v4/emails"
GET_EMAIL_PATH = "/v4/emails/{msgid}/view"
GET_EMAIL_STATUS_PATH = "/v4/emails/{transactionid}/status"
GET_TEMPLATES_PATH = "/v4/templates"


class EmailRecipient(BaseSchema):
    Email: str
    Fields: dict[str, Any] | None = None


class BodyPart(BaseSchema):
    ContentType: str = "HTML"
    Content: str = ""
    Charset: str = "utf-8"


class MessageAttachment(BaseSchema):
    BinaryContent: str
    Name: str
    ContentType: str | None = None
    Size: int | None = None


class UtmModel(BaseSchema):
    Source: str | None = None
    Medium: str | None = None
    Campaign: str | None = None
    Content: str | None = None


class EmailContent(BaseSchema):
    # Body: list[BodyPart] | None = None
    Merge: dict[str, Any] | None = None
    Attachments: list[MessageAttachment] | None = None
    Headers: dict[str, str] | None = None
    Postback: str | None = None
    EnvelopeFrom: str | None = None
    From: str | None = None
    ReplyTo: str | None = None
    Subject: str | None = None
    TemplateName: str | None = None
    AttachFiles: list[str] | None = None
    Utm: UtmModel | None = None


class EmailOptions(BaseSchema):
    TimeOffset: int | None = None
    PoolName: str | None = None
    ChannelName: str | None = None
    Encoding: str | None = "UserProvided"
    TrackOpens: bool | str | None = None
    TrackClicks: bool | str | None = None


class SendMailRequest(BaseSchema):
    Recipients: list[EmailRecipient]
    Content: EmailContent
    Options: EmailOptions | None = None


class SendMailResponse(BaseSchema):
    TransactionID: str
    MessageID: str


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


class TemplateScope(str, Enum):
    PERSONAL = "Personal"
    GLOBAL = "Global"


class TemplateType(str, Enum):
    RAW_HTML = "RawHTML"
    DRAG_DROP_EDITOR = "DragDropEditor"
    LANDING_PAGE_EDITOR = "LandingPageEditor"
    TEMPLATE_EDITOR = "TemplateEditor"
    FORM_TEMPLATE = "FormTemplate"
    LANDING_PAGE_TEMPLATE = "LandingPageTemplate"
    PAYMENT_CONFIRMATION_TEMPLATE = "PaymentConfirmationTemplate"
    LANDING_PAGE_PRODUCT_TEMPLATE = "LandingPageProductTemplate"
    LANDING_PAGE_CHECKOUT_TEMPLATE = "LandingPageCheckoutTemplate"
    LANDING_PAGE_PAYMENT_CONFIRMATION_TEMPLATE = (
        "LandingPagePaymentConfirmationTemplate"
    )
    LANDING_PAGE_NEWSLETTER_PRODUCT_TEMPLATE = "LandingPageNewsletterProductTemplate"
    LANDING_PAGE_NEWSLETTER_PAYMENT_CONFIRMATION_TEMPLATE = (
        "LandingPageNewsletterPaymentConfirmationTemplate"
    )
    NEWSLETTER_SUBSCRIPTION_CANCELLATION_TEMPLATE = (
        "NewsletterSubscriptionCancellationTemplate"
    )


class GetTemplatesRequest(BaseSchema):
    scopeType: list[TemplateScope] = [TemplateScope.PERSONAL]
    templateTypes: list[TemplateType] | None = None
    limit: int = 500
    offset: int = 0


class ElasticEmail(BaseClient, BaseEmailService):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ELASTIC_EMAIL_API_KEY", "")
        headers = {
            "X-ElasticEmail-ApiKey": self.api_key,
            "Content-Type": "application/json",
        }
        super().__init__(base_url=BASE_URL, headers=headers)

    async def send_email(
        self, req: SendMailRequest, jinja_data: dict[str, Any] = {}
    ) -> SendMailResponse:
        body = BodyPart(
            ContentType="HTML", Content=self.__get_email_template(data=jinja_data)
        )
        payload = req.model_dump(exclude_none=True)
        if not payload.get("Content", None):
            raise Exception("Content is required")
        if not req.Content.TemplateName:
            payload["Content"]["Body"] = [body.model_dump()]
        response = await self.post(path=SEND_EMAIL_PATH, json=payload)
        return SendMailResponse(**response.json())

    async def get_email(self, message_id: str) -> dict[str, Any]:
        response = await self.get(path=GET_EMAIL_PATH.format(msgid=message_id))
        return response.json()

    async def get_status_email(self, transaction_id: str) -> EmailStatusResponse:
        response = await self.get(
            path=GET_EMAIL_STATUS_PATH.format(transactionid=transaction_id)
        )
        return EmailStatusResponse(**response.json())

    async def get_templates(
        self, req: GetTemplatesRequest | None = None
    ) -> list[dict[str, Any]] | dict[str, Any]:
        if req is None:
            req = GetTemplatesRequest()
        params = req.model_dump(exclude_none=True)
        response = await self.get(path=GET_TEMPLATES_PATH, params=params)
        return response.json()


elastic_email = ElasticEmail()
