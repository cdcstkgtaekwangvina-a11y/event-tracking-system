import asyncio
from typing import Any, Self

from httpx import (
    AsyncClient,
    ConnectError,
    ConnectTimeout,
    HTTPStatusError,
    ReadTimeout,
    Response,
)


class BaseClient:
    def __init__(
        self,
        client: AsyncClient | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        follow_redirects: bool = True,
        auto_close: bool = False,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        self.auto_close = auto_close
        self._is_external_client = client is not None

        if self._is_external_client and client is not None:
            self._client = client
        else:
            self.base_url = base_url or ""
            self.timeout = timeout
            self.follow_redirects = follow_redirects
            self.extra_kwargs = kwargs
            self._client = self._build_client()
            self.max_retries = max_retries

    def _build_client(self) -> AsyncClient:
        return AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=self.follow_redirects,
            **self.extra_kwargs,
        )

    @property
    def client(self) -> AsyncClient:
        if not self._is_external_client and self._client.is_closed:
            self._client = self._build_client()
        return self._client

    async def request(
        self, method: str, path: str = "", max_retries: int | None = None, **kwargs: Any
    ) -> Response:
        retries = max_retries if max_retries is not None else self.max_retries
        retries = max(1, retries)

        try:
            for attempt in range(retries):
                try:
                    response = await self.client.request(method, path, **kwargs)
                    response.raise_for_status()
                    return response
                except (
                    ConnectError,
                    ReadTimeout,
                    ConnectTimeout,
                    HTTPStatusError,
                ) as exc:
                    if (
                        isinstance(exc, HTTPStatusError)
                        and exc.response.status_code < 500
                    ):
                        raise exc
                    if attempt == retries - 1:
                        raise exc
                    await asyncio.sleep(2**attempt)
            raise RuntimeError("Kết thúc vòng lặp mà không trả về response")
        finally:
            if self.auto_close:
                await self.close()

    async def get(self, path: str = "", **kwargs: Any) -> Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str = "", **kwargs: Any) -> Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str = "", **kwargs: Any) -> Response:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str = "", **kwargs: Any) -> Response:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str = "", **kwargs: Any) -> Response:
        return await self.request("DELETE", path, **kwargs)

    async def close(self) -> None:
        if not self._is_external_client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
