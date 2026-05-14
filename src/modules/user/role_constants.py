from enum import Enum

class ROLE(str, Enum):
    COMMON = "common"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"