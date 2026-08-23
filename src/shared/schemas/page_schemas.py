from src.shared.base.base_schema import BaseSchema


class PageSchema(BaseSchema):
    id: str
    name: str
    icon: str
    path: str
    include_roles: list[str] | None = []
