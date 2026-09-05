import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _resolve_log_level() -> int:
    """Trả về log level dựa theo biến môi trường `env`."""
    environment: str = os.getenv("env", "dev").strip().lower()
    return logging.DEBUG if environment == "dev" else logging.INFO


def _build_formatter(environment: str) -> logging.Formatter:
    """
    Dev  → formatter dễ đọc, có màu qua ANSI codes, hiển thị rõ PID và Worker ID.
    Prod → formatter JSON-style tích hợp thêm thông tin process cho log aggregator.
    """
    # Lấy thông tin ID của Worker từ Granian (trả về rỗng "" nếu chạy ở chế độ dev thường)
    worker_id = os.getenv("GRANIAN_WORKER_ID", "")
    worker_tag = f"[W:{worker_id}]" if worker_id else ""

    if environment == "dev":
        fmt = (
            "\033[36m%(asctime)s\033[0m "  # cyan – timestamp
            f"\033[35m[PID:%(process)d]{worker_tag}\033[0m "  # magenta – PID & Worker ID
            "\033[1m%(name)s\033[0m "  # bold – logger name
            "[%(levelname)s] "
            "%(message)s "
            "(\033[33m%(filename)s\033[0m:%(lineno)d)"  # yellow – source loc
        )
        datefmt = "%H:%M:%S"
    else:
        fmt = (
            '{"time": "%(asctime)s", '
            '"pid": %(process)d, '
            f'"worker_id": "{worker_id}", '
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
    """

    # Registry để tránh tạo lại handler nhiều lần cho cùng 1 logger name
    _configured: set[str] = set()

    def __init__(self, name: str | None = None) -> None:
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
    # Convenience shortcuts
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
# Factory helper
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Trả về :class:`logging.Logger` đã được cấu hình theo môi trường."""
    logger = logging.getLogger(name)
    if name not in BaseLogger._configured:
        BaseLogger._configure(logger)
        BaseLogger._configured.add(name)
    return logger
