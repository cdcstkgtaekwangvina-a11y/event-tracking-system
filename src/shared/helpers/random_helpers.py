import random

from .time_extensions import get_now_utc


class RandomHelpers:
    characters: str = ""
    prefix: str = ""
    length: int = 6

    def __init__(
        self,
        characters: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-@",
        prefix: str = "",
        length: int = 6,
    ):
        self.characters = characters
        self.prefix = prefix
        self.length = length

    def ignore_char(self, chars: str):
        for char in chars:
            self.characters = self.characters.replace(char, "")

    @classmethod
    def generate_random_string(
        cls, override_length: int | None = None, override_prefix: str = ""
    ) -> str:
        prefix = override_prefix if override_prefix else cls.prefix
        length = override_length if override_length else cls.length
        return prefix + "".join(random.choice(cls.characters) for _ in range(length))

    @classmethod
    def generate_random_number_string(
        cls, override_length: int | None = None, override_prefix: str = ""
    ) -> str:
        prefix = override_prefix if override_prefix else cls.prefix
        length = override_length if override_length else cls.length
        return prefix + "".join(random.choice("0123456789") for _ in range(length))

    @classmethod
    def random_string_with_timestamp(
        cls, override_length: int | None = None, override_prefix: str = ""
    ) -> str:
        timestamp = get_now_utc().strftime("%Y%m%d%H%M%S")
        random_string = cls.generate_random_string(override_length, override_prefix)
        return f"{random_string}_{timestamp}"

    @classmethod
    def random_number_string_with_timestamp(
        cls, override_length: int | None = None, override_prefix: str = ""
    ) -> str:
        timestamp = get_now_utc().strftime("%Y%m%d%H%M%S")
        random_string = cls.generate_random_number_string(
            override_length, override_prefix
        )
        return f"{random_string}_{timestamp}"

    @classmethod
    def generate_password(cls, override_length: int | None = None) -> str:
        """Tạo mật khẩu ngẫu nhiên thỏa mãn PASSWORD_PATTERN.

        Điều kiện: ít nhất 1 chữ hoa, 1 chữ thường, 1 số, 1 ký tự đặc biệt
        (@$!%*?&) và độ dài tối thiểu 8.
        """
        import secrets
        import string

        length = override_length if override_length else 12
        if length < 8:
            length = 8

        lower = string.ascii_lowercase
        upper = string.ascii_uppercase
        digits = string.digits
        special = "@$!%*?&"
        all_chars = lower + upper + digits + special

        # Đảm bảo đủ 4 nhóm ký tự
        password = [
            secrets.choice(lower),
            secrets.choice(upper),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        # Điền reste ngẫu nhiên
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))

        # Xáo trộn để không bị đoán vị trí
        password_list = list(password)
        for i in range(len(password_list) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_list[i], password_list[j] = password_list[j], password_list[i]

        return ''.join(password_list)
