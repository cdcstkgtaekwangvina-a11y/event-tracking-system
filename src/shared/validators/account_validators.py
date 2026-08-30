import re

USERNAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_@]{2,19}$"
USERNAME_ERROR_MESSAGE = (
    "Tên đăng nhập phải bắt đầu bằng chữ cái, dài 3-20 ký tự, không dấu, "
    "chỉ được chứa chữ cái, số và các ký tự _ @"
)


PASSWORD_PATTERN = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"
PASSWORD_ERROR_MESSAGE = (
    "Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, "
    "chữ số và ký tự đặc biệt (@$!%*?&)"
)


def validate_username(v: str) -> str:
    if not re.match(USERNAME_PATTERN, v):
        raise ValueError(USERNAME_ERROR_MESSAGE)
    return v


def validate_strong_password(v: str) -> str:
    v = v.strip()
    if not re.match(PASSWORD_PATTERN, v):
        raise ValueError(PASSWORD_ERROR_MESSAGE)
    return v
