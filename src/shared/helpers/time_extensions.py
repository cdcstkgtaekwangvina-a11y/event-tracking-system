from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
UTC_TZ = timezone.utc


def get_now_utc() -> datetime:
    """Trả về thời gian hiện tại theo UTC (timezone-aware) để lưu trữ DB"""
    return datetime.now(UTC_TZ)


def get_utc_time(time: Optional[datetime] = None, secs: int = 0) -> datetime:
    """Trả về thời gian theo UTC (có thể cộng thêm số giây secs)"""
    if time is None:
        time = datetime.now(UTC_TZ)
    elif time.tzinfo is None:
        time = time.replace(tzinfo=UTC_TZ)
    else:
        time = time.astimezone(UTC_TZ)
    if secs != 0:
        time = time + timedelta(seconds=secs)
    return time


def get_now_vn() -> datetime:
    """Trả về thời gian hiện tại theo giờ Việt Nam (UTC+7) - Dùng khi hiển thị / format"""
    return datetime.now(VN_TZ)


def get_vn_time(time: Optional[datetime] = None, secs: int = 0) -> datetime:
    """Chuyển đổi thời gian sang giờ Việt Nam (có thể cộng thêm secs)"""
    if time is None:
        time = datetime.now(VN_TZ)
    elif time.tzinfo is None:
        time = time.replace(tzinfo=UTC_TZ)
    time = time.astimezone(VN_TZ)
    if secs != 0:
        time = time + timedelta(seconds=secs)
    return time


def to_vn_time(time: Optional[datetime] = None) -> datetime:
    """Chuyển đổi thời gian sang giờ Việt Nam (Asia/Ho_Chi_Minh)"""
    return get_vn_time(time)

