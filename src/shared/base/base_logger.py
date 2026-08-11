import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _resolve_log_level() -> int:
    """Trả về log level dựa theo biến môi trường `env`."""
    environment: str = os.getenv("env", "dev").strip().lower()
    return logging.DEBUG if environment == "dev" else logging.INFO


def _build_formatter(environment: str) -> logging.Formatter:
    """
    Dev  → formatter dễ đọc, có màu qua ANSI codes.
    Prod → formatter JSON-style cho log aggregator.
    """
    if environment == "dev":
        fmt = (
            "\033[36m%(asctime)s\033[0m "          # cyan  – timestamp
            "\033[1m%(name)s\033[0m "               # bold  – logger name
            "[%(levelname)s] "
            "%(message)s "
            "(\033[33m%(filename)s\033[0m:%(lineno)d)"  # yellow – source loc
        )
        datefmt = "%H:%M:%S"
    else:
        fmt = (
            '{"time": "%(asctime)s", '
            '"logger": "%(name)s", '
            '"level": "%(levelname)s", '
            '"message": "%(message)s", '
            '"file": "%(filename)s", '
            '"line": %(lineno)d}'
        )
        datefmt = "%Y-%m-%dT%H:%M:%S%z"

    return logging.Formatter(fmt=fmt, datefmt=datefmt)


class BaseLogger:
    """
    Wrapper nhẹ quanh :class:`logging.Logger` chuẩn của Python.

    Mỗi class kế thừa (hoặc bất kỳ module nào) chỉ cần:

    .. code-block:: python

        class EmployeeService(BaseLogger):
            def __init__(self):
                super().__init__()          # logger lấy tên class tự động
                # hoặc
                super().__init__("my.custom.name")

            def do_something(self):
                self.logger.info("Done")
                self.logger.debug("detail …")

    Khi ``env=dev``  → level DEBUG, formatter dễ đọc (có màu).
    Khi ``env=prod`` → level INFO,  formatter JSON (phù hợp log collector).
    """

    # Registry để tránh tạo lại handler nhiều lần cho cùng 1 logger name
    _configured: set[str] = set()

    def __init__(self, name: Optional[str] = None) -> None:
        logger_name = name or self.__class__.__name__
        self.logger: logging.Logger = logging.getLogger(logger_name)

        if logger_name not in BaseLogger._configured:
            self._configure(self.logger)
            BaseLogger._configured.add(logger_name)

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    @staticmethod
    def _configure(logger: logging.Logger) -> None:
        environment = os.getenv("env", "dev").strip().lower()
        level = _resolve_log_level()

        logger.setLevel(level)
        # Không propagate lên root logger để tránh duplicate logs
        logger.propagate = False

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            handler.setFormatter(_build_formatter(environment))
            logger.addHandler(handler)

    # ------------------------------------------------------------------
    # Convenience shortcuts (optional – dùng self.logger trực tiếp cũng OK)
    # ------------------------------------------------------------------

    def log_debug(self, msg: str, *args, **kwargs) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def log_info(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(msg, *args, **kwargs)

    def log_warning(self, msg: str, *args, **kwargs) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def log_error(self, msg: str, *args, **kwargs) -> None:
        self.logger.error(msg, *args, **kwargs)

    def log_critical(self, msg: str, *args, **kwargs) -> None:
        self.logger.critical(msg, *args, **kwargs)

    def log_exception(self, msg: str, *args, **kwargs) -> None:
        """Log error kèm traceback hiện tại (dùng bên trong except block)."""
        self.logger.exception(msg, *args, **kwargs)


# ---------------------------------------------------------------------------
# Factory helper – dùng khi KHÔNG kế thừa (e.g. trong module-level code)
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """
    Trả về :class:`logging.Logger` đã được cấu hình theo môi trường.

    Dùng ở những nơi không muốn kế thừa ``BaseLogger``:

    .. code-block:: python

        from src.shared.base.base_logger import get_logger

        logger = get_logger(__name__)
        logger.info("module loaded")
    """
    logger = logging.getLogger(name)
    if name not in BaseLogger._configured:
        BaseLogger._configure(logger)
        BaseLogger._configured.add(name)
    return logger
