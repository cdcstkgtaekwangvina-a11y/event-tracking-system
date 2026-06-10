from src.shared.base.base_schema import BaseSchema


class UserSelect(BaseSchema):
    id: str
    name: str
    username: str
    email: str
    role: str
