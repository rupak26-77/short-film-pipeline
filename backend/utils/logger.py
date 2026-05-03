import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        if isinstance(record.args, dict):
            payload.update(record.args)
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


_CONFIGURED = False


def get_logger(name: str = "short-film-pipeline") -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger(name)
    if not _CONFIGURED:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(level=level)
        root = logging.getLogger()
        for h in root.handlers:
            h.setFormatter(_JsonFormatter())
        _CONFIGURED = True
    return logger


@contextmanager
def log_timed(logger: logging.Logger, module_name: str, stage: Optional[int] = None, **fields: Any):
    t0 = time.perf_counter()
    logger.info("module_start", {"module": module_name, "stage": stage, **fields})
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        logger.info("module_end", {"module": module_name, "stage": stage, "duration_sec": round(dt, 4), **fields})
