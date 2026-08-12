import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    ENV: str = os.getenv("env", "dev")
    DB_USER: str = os.environ["DB_USER"]
    DB_PASSWORD: str = os.environ["DB_PASSWORD"]
    DB_HOST: str = os.environ["DB_HOST"]
    DB_PORT: int = int(os.environ["DB_PORT"])
    DB_NAME: str = os.environ["DB_NAME"]
    DB_PARAMS: str = os.getenv("DB_PARAMS", "")

    def db_url(self, is_config: bool = False) -> str:
        url = f"postgresql+asyncpg://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?{self.DB_PARAMS}"
        if is_config:
            url = url.replace("%", "%%")
        return url
