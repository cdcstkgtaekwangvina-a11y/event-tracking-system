import random
from .time_extensions import get_now_vn

class RandomHelpers:
    characters: str = ""
    prefix: str = ""
    length: int = 6
    def __init__(self, characters: str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-@', prefix: str = "", length: int = 6):
        self.characters = characters
        self.prefix = prefix
        self.length = length

    def ignore_char(self, chars: str):
        for char in chars:
            self.characters = self.characters.replace(char, '')
            
    @classmethod
    def generate_random_string(cls, override_length: int, override_prefix: str = "") -> str:
        prefix = override_prefix if override_prefix else cls.prefix
        length = override_length if override_length else cls.length
        return prefix + ''.join(random.choice(cls.characters) for _ in range(length))
    
    @classmethod
    def generate_random_number_string(cls, override_length: int, override_prefix: str = "") -> str:
        prefix = override_prefix if override_prefix else cls.prefix
        length = override_length if override_length else cls.length
        return prefix + ''.join(random.choice('0123456789') for _ in range(length))

    @classmethod
    def random_string_with_timestamp(cls, override_length: int, override_prefix: str = "") -> str:
        timestamp = get_now_vn().strftime("%Y%m%d%H%M%S")
        random_string = cls.generate_random_string(override_length, override_prefix)
        return f"{random_string}_{timestamp}"
    
    @classmethod
    def random_number_string_with_timestamp(cls, override_length: int, override_prefix: str = "") -> str:
        timestamp = get_now_vn().strftime("%Y%m%d%H%M%S")
        random_string = cls.generate_random_number_string(override_length, override_prefix)
        return f"{random_string}_{timestamp}"