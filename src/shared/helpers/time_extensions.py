from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_now_vn() -> datetime:
    return datetime.now(VN_TZ)

def get_vn_time(time: Optional[datetime] = None, secs: int = 0) -> datetime:
    if time is None:
        time = datetime.now()
    time = time + timedelta(seconds=secs)
    return time.astimezone(VN_TZ)
