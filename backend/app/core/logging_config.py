"""Logging with rotation.

Without rotation a single app.log grows forever and eventually fills the disk.
RotatingFileHandler keeps app.log under ~5 MB; when it fills up it is renamed to
app.log.1, app.log.1 -> app.log.2 ... and anything beyond `backupCount` is deleted.
Worst case disk usage = (backupCount + 1) * maxBytes = 30 MB.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(log_dir: str, level: int = logging.INFO) -> None:
    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return  # already configured (uvicorn --reload imports twice)
    root.setLevel(level)

    formatter = logging.Formatter(FORMAT)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # The ES client logs every HTTP request at INFO - far too chatty.
    logging.getLogger("elastic_transport").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
