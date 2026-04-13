from __future__ import annotations

import logging
from typing import Any


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    serialized_fields = " ".join(f"{key}={value}" for key, value in sorted(fields.items()))
    logger.log(level, "%s %s", event, serialized_fields)
