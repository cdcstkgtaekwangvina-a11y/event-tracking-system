import inspect
from fastapi import Depends
from fastapi.dependencies.utils import get_dependant
from asyncio import iscoroutinefunction
from functools import wraps
from typing import Type, TypeVar, Callable

T = TypeVar("T")


def compile_route(route, cls, old_endpoint):
    sig = inspect.signature(old_endpoint)
    new_params = [p for p in sig.parameters.values() if p.name != "self"]

    cbv_param = inspect.Parameter(
        "__cbv_instance__", inspect.Parameter.KEYWORD_ONLY, default=Depends(cls)
    )

    if iscoroutinefunction(old_endpoint):

        @wraps(old_endpoint)
        async def wrapper(*args, __cbv_instance__=Depends(cls), **kwargs):
            return await old_endpoint(__cbv_instance__, *args, **kwargs)
    else:

        @wraps(old_endpoint)
        def wrapper(*args, __cbv_instance__=Depends(cls), **kwargs):
            return old_endpoint(__cbv_instance__, *args, **kwargs)

    setattr(wrapper, "__signature__", sig.replace(parameters=new_params + [cbv_param]))

    if "self" in wrapper.__annotations__:
        del wrapper.__annotations__["self"]
    wrapper.__annotations__["__cbv_instance__"] = cls

    route.endpoint = wrapper
    route.dependant = get_dependant(path=route.path_format, call=wrapper)


def clean_cbv(router) -> Callable[[Type[T]], Type[T]]:
    def decorator(cls: Type[T]) -> Type[T]:
        # Dùng list(router.routes) để sao chép danh sách, tránh side-effect khi lặp
        for route in list(router.routes):
            old_endpoint = route.endpoint
            try:
                sig = inspect.signature(old_endpoint)
                # Chỉ xử lý các hàm thuộc về Class hiện tại (vẫn còn tham số self)
                if "self" in sig.parameters:
                    compile_route(route, cls, old_endpoint)
            except (ValueError, TypeError):
                continue
        return cls

    return decorator
