from datetime import datetime
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_now_vn() -> datetime:
    return datetime.now(VN_TZ)
