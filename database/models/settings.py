from sqlmodel import Field
from typing import Optional, Dict, Any
from sqlalchemy.dialects.postgresql import JSONB
from database.models.base_model import PrimaryModel


class Settings(PrimaryModel[str], table=True):
    __tablename__ = "settings"
    id: str = Field(max_length=500, primary_key=True)
    value: Optional[Dict[str, Any]] = Field(default={}, sa_type=JSONB)
    description: Optional[str] = Field(default=None, nullable=True)
