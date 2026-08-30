from fastapi import Depends, HTTPException, Request, status

from src.shared.services.redis_services import RedisServices


class RateLimit:
    def __init__(self, request_per_windows: int = 60, windows_time: int = 60):
        self.redis_service = RedisServices()
        self.request_per_windows = request_per_windows
        self.windows_time = windows_time

    def __cache_key(self, ip: str) -> str:
        return f"rate_limit:{ip}"

    def __get_client_ip(self, request: Request) -> str | None:
        # Trust direct socket host by default.
        # Only parse x-forwarded-for if behind a trusted reverse proxy (e.g. Nginx, Cloudflare)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        return request.client.host if request.client else None

    async def __call__(self, request: Request) -> bool:
        client_ip = self.__get_client_ip(request)

        if not client_ip:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể xác định IP của bạn",
            )

        cache_key = self.__cache_key(client_ip)

        # Batch both commands into a single TCP round-trip
        async with self.redis_service.client.pipeline(transaction=True) as pipe:
            pipe.incr(cache_key)
            pipe.expire(cache_key, self.windows_time, nx=True)
            results = await pipe.execute()

        rq_count = results[0]

        if rq_count > self.request_per_windows:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Quá nhiều thao tác! Vui lòng thử lại sau.",
            )

        return True


def rate_limit(request_per_windows: int = 60, windows_time: int = 60):
    return Depends(
        RateLimit(request_per_windows=request_per_windows, windows_time=windows_time)
    )
