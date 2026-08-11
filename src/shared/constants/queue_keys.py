from enum import Enum


class QueueKeys(str, Enum):
    BULK_UPSERT_EMPLOYEES = "bulk_upsert_employees_task"
