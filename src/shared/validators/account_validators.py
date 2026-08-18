import re

USERNAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_.-@]{2,19}$"
USERNAME_ERROR_MESSAGE = (
    "Tên đăng nhập phải bắt đầu bằng chữ cái, dài 3-20 ký tự, không dấu, "
    "chỉ được chứa chữ cái, số và các ký tự _ . - @"
)


def validate_username(v: str) -> str:
    if not re.match(USERNAME_PATTERN, v):
        raise ValueError(USERNAME_ERROR_MESSAGE)
    return v


def validate_strong_password(v: str) -> str:
    v = v.strip()
    if len(v) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")

    if not re.search(r"[A-Z]", v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái viết hoa")

    if not re.search(r"[a-z]", v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái viết thường")

    if not re.search(r"\d", v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số")

    if not re.search(r"[@$!%*?&]", v):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt (@$!%*?&)")

    return v
