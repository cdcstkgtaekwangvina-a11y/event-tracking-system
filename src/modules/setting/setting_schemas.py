from src.shared.base.base_schema import BaseSchema
from pydantic import Field


class FileConfigSchema(BaseSchema):
    max_size_file: int = Field(gt=0)
