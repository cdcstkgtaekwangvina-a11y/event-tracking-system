from typing import Any, Callable, TypeVar, cast
from pydantic import BaseModel

T = TypeVar("T", bound="BaseSchema")


class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}

    @classmethod
    def nameof(cls: type[T], selector: Callable[[T], Any]) -> str:

        class NameofProxy:
            def __getattr__(self, name: str) -> str:
                return name

        return str(selector(cast(Any, NameofProxy())))
