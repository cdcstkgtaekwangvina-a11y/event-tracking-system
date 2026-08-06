import json
from collections.abc import Callable
from typing import Any, TypeVar, cast

from pydantic import BaseModel, field_validator, model_validator

T = TypeVar("T", bound="BaseSchema")


def _unpack_json_value(value: Any) -> Any:
    if isinstance(value, str):
        s = value.strip()
        if (s.startswith("[") and s.endswith("]")) or (
            s.startswith("{") and s.endswith("}")
        ):
            try:
                return json.loads(s)
            except Exception:
                return value
        return value

    if isinstance(value, list):
        if len(value) == 1 and isinstance(value[0], str):
            unpacked = _unpack_json_value(value[0])
            if unpacked != value[0]:
                return unpacked
        return [_unpack_json_value(item) for item in value]

    return value


class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}

    @classmethod
    def nameof(cls: type[T], selector: Callable[[T], Any]) -> str:

        class NameofProxy:
            def __getattr__(self, name: str) -> str:
                return name

        return str(selector(cast(Any, NameofProxy())))

    @model_validator(mode="before")
    @classmethod
    def _auto_parse_query_json(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        has_potential_json = False
        for v in data.values():
            if isinstance(v, list):
                has_potential_json = True
                break
            if isinstance(v, str):
                s = v.strip()
                if (s.startswith("[") and s.endswith("]")) or (
                    s.startswith("{") and s.endswith("}")
                ):
                    has_potential_json = True
                    break

        if not has_potential_json:
            return data

        return {key: _unpack_json_value(value) for key, value in data.items()}
