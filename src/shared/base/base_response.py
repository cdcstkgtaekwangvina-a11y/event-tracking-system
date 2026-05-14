from fastapi import HTTPException
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    message: str
    success: bool
    data: Optional[T] = None
    status_code: int

    @classmethod
    def ok(cls, data: T, message="Success"):
        response_content = cls(
            message=message, success=True, data=data, status_code=200
        )
        return response_content.model_dump()

    @classmethod
    def created(cls, data: T, message="Created"):
        response_content = cls(
            message=message, success=True, data=data, status_code=201
        )
        return response_content.model_dump()

    @classmethod
    def no_content(cls, message="No Content"):
        response_content = cls(
            message=message, success=True, data=None, status_code=204
        )
        return response_content.model_dump()

    @classmethod
    def fail(cls, message="Bad Request", status_code=400, data=None):
        response_content = cls(
            message=message, success=False, data=data, status_code=status_code
        )
        raise HTTPException(
            status_code=status_code, detail=response_content.model_dump()
        )

    @classmethod
    def unauthorized(cls, message="Unauthorized", status_code=401, data=None):
        response_content = cls(
            message=message, success=False, data=data, status_code=status_code
        )
        raise HTTPException(
            status_code=status_code, detail=response_content.model_dump()
        )

    @classmethod
    def forbidden(cls, message="Forbidden", status_code=403, data=None):
        response_content = cls(
            message=message, success=False, data=data, status_code=status_code
        )
        raise HTTPException(
            status_code=status_code, detail=response_content.model_dump()
        )

    @classmethod
    def not_found(cls, message="Not Found", status_code=404, data=None):
        response_content = cls(
            message=message, success=False, data=data, status_code=status_code
        )
        raise HTTPException(
            status_code=status_code, detail=response_content.model_dump()
        )

    @classmethod
    def error(cls, message="Server Error", status_code=500, data=None):
        response_content = cls(
            message=message, success=False, data=data, status_code=status_code
        )
        raise HTTPException(
            status_code=status_code, detail=response_content.model_dump()
        )

    @classmethod
    def rate_limit(cls, message="Too Many Requests"):
        response_content = cls(
            message=message, success=False, data=None, status_code=429
        )
        raise HTTPException(status_code=429, detail=response_content.model_dump())
