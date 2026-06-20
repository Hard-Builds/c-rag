import contextvars
import logging
import os
import sys

from app.core.config import settings

request_id_ctx_var = contextvars.ContextVar("request_id", default="-")


class TraceIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()  # type: ignore[attr-defined]
        return True


class RelativePathFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.relative_filename = self._rel(record.pathname)  # type: ignore[attr-defined]
        return super().format(record)

    @staticmethod
    def _rel(filepath: str) -> str:
        if "site-packages" in filepath:
            return "site-packages/" + "/".join(
                filepath.split("site-packages/")[-1].split("/")[-2:]
            )
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.relpath(filepath, root)


class AppLogger:
    _logger: logging.Logger

    @classmethod
    def setup_logging(cls) -> None:
        log_level = settings.LOG_LEVEL.upper()
        root = logging.getLogger("app")
        root.setLevel(log_level)
        root.propagate = False
        handler = logging.StreamHandler(sys.stdout)
        fmt = RelativePathFormatter(
            "[%(asctime)s] [%(levelname)s] [%(request_id)s] "
            "[%(relative_filename)s:%(funcName)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        handler.addFilter(TraceIdLogFilter())
        root.addHandler(handler)
        cls._logger = root

    @classmethod
    def get_logger(cls) -> logging.Logger:
        if not hasattr(cls, "_logger"):
            cls.setup_logging()
        return cls._logger


logger = AppLogger.get_logger()
