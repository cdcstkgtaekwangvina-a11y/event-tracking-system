from collections.abc import Callable
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone, tzinfo
from urllib.parse import unquote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.shared.base.base_logger import get_logger

DEFAULT_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
logger = get_logger(__name__)
# ContextVar để lưu trữ timezone của request hiện tại
current_timezone_ctx: ContextVar[tzinfo] = ContextVar(
    "current_timezone_ctx", default=DEFAULT_TIMEZONE
)


def get_current_timezone() -> tzinfo:
    """Lấy timezone của request hiện tại (mặc định Asia/Ho_Chi_Minh nếu không xác định)"""
    return current_timezone_ctx.get()


def parse_timezone(tz_str: str | None) -> tzinfo:
    """Chuyển chuỗi timezone (IANA name, offset +/-HH:MM hoặc số giờ) thành tzinfo"""
    if not tz_str:
        return DEFAULT_TIMEZONE

    tz_str = unquote(tz_str).strip()

    # 1. Thử parse tên IANA timezone: e.g. "Asia/Ho_Chi_Minh", "UTC", "America/New_York"
    try:
        return ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, ValueError) as e:
        logger.error(f"Không thể parse timezone: {e}")

    # 2. Thử parse dạng offset: "+07:00", "-05:00", "+0700", "+7", "-5", "7"
    try:
        clean_tz = tz_str.replace("UTC", "").replace("GMT", "").strip()
        if ":" in clean_tz:
            parts = clean_tz.split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            if hours < 0:
                minutes = -minutes
            return timezone(timedelta(hours=hours, minutes=minutes))
        elif clean_tz.lstrip("+-").isdigit():
            hours = int(clean_tz)
            return timezone(timedelta(hours=hours))
    except Exception as e:
        logger.exception(f"Không thể parse timezone: {e}")

    return DEFAULT_TIMEZONE


def to_user_timezone(
    dt: datetime | None, target_tz: tzinfo | None = None
) -> datetime | None:
    """Chuyển đổi một đối tượng datetime (UTC) sang timezone của người dùng"""
    if dt is None:
        return None
    tz = target_tz or get_current_timezone()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


class TimezoneMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Lấy timezone từ Header > Cookie > Query Param
        tz_header = (
            request.headers.get("x-timezone")
            or request.headers.get("timezone")
            or request.cookies.get("user_timezone")
            or request.cookies.get("timezone")
            or request.query_params.get("timezone")
            or request.query_params.get("tz")
        )

        user_tz = parse_timezone(tz_header)

        # Gán vào request state và context var
        request.state.timezone = user_tz
        token = current_timezone_ctx.set(user_tz)

        try:
            response = await call_next(request)
            return response
        finally:
            current_timezone_ctx.reset(token)
