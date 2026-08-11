from fastapi import HTTPException
from typing import TypeVar, Generic, Optional, Any
from typing_extensions import Self
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

T = TypeVar("T")


class BaseResponse(JSONResponse, Generic[T]):
    message: str
    success: bool
    data: Optional[T] = None
    status_code: int

    def __init__(
        self,
        status_code: int,
        success: bool,
        message: str,
        data: Optional[T] = None,
        **kwargs,
    ):
        content = {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": jsonable_encoder(data) if data is not None else None,
        }

        super().__init__(status_code=status_code, content=content, **kwargs)

    @classmethod
    def ok(cls, data: Any = None, message: str = "Success") -> Self:
        return cls(status_code=200, success=True, message=message, data=data)

    @classmethod
    def created(cls, data: Any, message="Created") -> Self:
        return cls(message=message, success=True, data=data, status_code=201)

    @classmethod
    def no_content(cls, message="No Content") -> Self:
        return cls(message=message, success=True, data=None, status_code=204)

    @classmethod
    def fail(cls, message="Bad Request", status_code=400, data=None) -> Self:
        response_content = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
        }
        raise HTTPException(status_code=status_code, detail=response_content)

    @classmethod
    def unauthorized(cls, message="Unauthorized", status_code=401, data=None) -> Self:
        response_content = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
        }
        raise HTTPException(status_code=status_code, detail=response_content)

    @classmethod
    def forbidden(cls, message="Forbidden", status_code=403, data=None) -> Self:
        response_content = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
        }
        raise HTTPException(status_code=status_code, detail=response_content)

    @classmethod
    def not_found(cls, message="Not Found", status_code=404, data=None) -> Self:
        response_content = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
        }
        raise HTTPException(status_code=status_code, detail=response_content)

    @classmethod
    def error(cls, message="Server Error", status_code=500, data=None) -> Self:
        response_content = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
        }
        raise HTTPException(status_code=status_code, detail=response_content)

    @classmethod
    def rate_limit(cls, message="Too Many Requests") -> Self:
        response_content = {
            "success": False,
            "status_code": 429,
            "message": message,
            "data": None,
        }
        raise HTTPException(status_code=429, detail=response_content)
