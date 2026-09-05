from fastapi import Depends, HTTPException, Request, status

from src.shared.services.redis_services import RedisServices


class RateLimit:
    def __init__(self, request_per_windows: int = 60, windows_time: int = 60):
        self.redis_service = RedisServices()
        self.request_per_windows = request_per_windows
        self.windows_time = windows_time

    def __get_client_ip(self, request: Request) -> str:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        return request.client.host if request.client else "127.0.0.1"

    async def __core_limit(self, request: Request, is_global: bool = False) -> bool:
        client_ip = self.__get_client_ip(request)

        endpoint = request.scope.get("endpoint")
        if is_global:
            func_name = "global"
        elif endpoint:
            func_name = f"{endpoint.__module__}.{endpoint.__qualname__}"
        else:
            func_name = request.url.path

        rate_key = f"ratelimit:{client_ip}:{func_name}"

        # Batch cả 2 lệnh vào 1 lượt gửi TCP
        async with self.redis_service.client.pipeline(transaction=True) as pipe:
            pipe.incr(rate_key)
            # nx=True chỉ chạy trên Redis 7.0+. Nếu dùng Redis cũ hơn, hãy dùng Lua script hoặc set expire khi rq_count == 1
            pipe.expire(rate_key, self.windows_time, nx=True)
            results = await pipe.execute()

        rq_count = results[0]

        if rq_count > self.request_per_windows:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Quá nhiều thao tác! Vui lòng thử lại sau.",
            )

        return True

    async def __call__(self, request: Request) -> bool:
        return await self.__core_limit(request, is_global=False)

    async def global_limit(self, request: Request) -> bool:
        return await self.__core_limit(request, is_global=True)


# Dependency cho từng Route riêng biệt
def rate_limit(request_per_windows: int = 60, windows_time: int = 60):
    return Depends(
        RateLimit(request_per_windows=request_per_windows, windows_time=windows_time)
    )


# Dependency toàn cục (Global Rate Limit)
def global_rate_limit(request_per_windows: int = 300, windows_time: int = 60):
    limiter = RateLimit(
        request_per_windows=request_per_windows, windows_time=windows_time
    )
    return Depends(limiter.global_limit)
