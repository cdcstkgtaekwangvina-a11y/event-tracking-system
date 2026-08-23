from collections.abc import Callable

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIRoute

from src.shared.base.base_request import BaseRequest


class BaseRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request):
            base_request = BaseRequest(request.scope, request.receive)

            return await original_route_handler(base_request)

        return custom_route_handler


class BaseRouter(APIRouter):
    version: str | None = None
    controller: str

    def __init__(
        self,
        controller: str,
        version: str | None = None,
        *args,
        **kwargs,
    ):
        kwargs.setdefault("route_class", BaseRoute)
        self.version = version
        self.controller = controller
        super().__init__(*args, **kwargs)

    def __get_path__(self, path: str | None = None) -> str:
        return (
            f"/{self.controller}/{path}"
            if path and len(path.strip()) > 0
            else f"/{self.controller}"
        )

    def __get_api_path__(self, path: str | None = None) -> str:
        if self.version and self.version != "" and len(self.version.strip()) > 0:
            return "/api" + f"/{self.version.strip()}{self.__get_path__(path)}"
        return "/api" + self.__get_path__(path)

    def get_api(
        self,
        path: str | None = None,
        response_class: type[Response] = JSONResponse,
        **kwargs,
    ):
        return super().get(
            self.__get_api_path__(path), response_class=response_class, **kwargs
        )

    def get(
        self,
        path: str | None = None,
        name: str | None = None,
        response_class=HTMLResponse,
        **kwargs,
    ):
        return super().get(
            self.__get_path__(path), name=name, response_class=response_class, **kwargs
        )

    def post_api(self, path: str | None = None, **kwargs):
        return super().post(
            self.__get_api_path__(path), response_class=JSONResponse, **kwargs
        )

    def post(
        self,
        path: str | None = None,
        name: str | None = None,
        response_class=HTMLResponse,
        **kwargs,
    ):
        return super().post(
            self.__get_path__(path), name=name, response_class=response_class, **kwargs
        )

    def put_api(self, path: str | None = None, **kwargs):
        return super().put(
            self.__get_api_path__(path), response_class=JSONResponse, **kwargs
        )

    def put(
        self,
        path: str | None = None,
        name: str | None = None,
        response_class=HTMLResponse,
        **kwargs,
    ):
        return super().put(
            self.__get_path__(path), name=name, response_class=response_class, **kwargs
        )

    def patch_api(self, path: str | None = None, **kwargs):
        return super().patch(
            self.__get_api_path__(path), response_class=JSONResponse, **kwargs
        )

    def patch(
        self,
        path: str | None = None,
        name: str | None = None,
        response_class=HTMLResponse,
        **kwargs,
    ):
        return super().patch(
            self.__get_path__(path), name=name, response_class=response_class, **kwargs
        )

    def delete_api(self, path: str | None = None, **kwargs):
        return super().delete(
            self.__get_api_path__(path), response_class=JSONResponse, **kwargs
        )

    def delete(
        self,
        path: str | None = None,
        name: str | None = None,
        response_class=HTMLResponse,
        **kwargs,
    ):
        return super().delete(
            self.__get_path__(path), name=name, response_class=response_class, **kwargs
        )
