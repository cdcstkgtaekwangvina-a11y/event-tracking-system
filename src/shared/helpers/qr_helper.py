import urllib.parse
from typing import Literal

from pydantic import Field

from src.shared.base.base_schema import BaseSchema


class CreateQRSchema(BaseSchema):
    data: str
    size: str = "200x200"
    ecc: Literal["L", "M", "Q", "H"] = "L"
    color: str = "0-0-0"
    bgcolor: str = "255-255-255"
    margin: int = Field(default=1, ge=0, lt=50)
    qzone: int = Field(default=0, gt=0, lt=100)
    format: Literal["png", "svg", "gif", "jpg", "jpeg", "eps"] = "png"


base_url = "https://api.qrserver.com/v1/create-qr-code/?"


def create_qr_url(schema: CreateQRSchema) -> str:
    data = urllib.parse.quote(schema.data)
    return f"{base_url}data={data}&size={schema.size}&ecc={schema.ecc}&color={schema.color}&bgcolor={schema.bgcolor}&margin={schema.margin}&qzone={schema.qzone}&format={schema.format}"
