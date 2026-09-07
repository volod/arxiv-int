"""JSONL logging handler for structured run logs."""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.observability.constants import CONSOLE_LOG_NAME, SCHEMA_ID


class JsonlFileHandler(logging.Handler):
    """Write one redacted JSON object per log record."""

    def __init__(self, path: Path, run_id: str, stage: str) -> None:
        super().__init__()
        self._path = path
        self._run_id = run_id
        self._stage = stage
        path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        payload = {
            "event": "log",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": self._run_id,
            "schema": SCHEMA_ID,
            "stage": self._stage,
            "ts": datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def stage_log_handlers(
    logs: Path, run_id: str, stage: str, log_format: str
) -> tuple[logging.Handler, ...]:
    """Build console and/or JSONL handlers for one stage session."""
    handlers: list[logging.Handler] = []
    if "console" in log_format:
        formatter = logging.Formatter("%(message)s")
        log_file = logging.FileHandler(logs / CONSOLE_LOG_NAME, encoding="utf-8")
        log_file.setFormatter(formatter)
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        handlers.extend((log_file, stream))
    if "jsonl" in log_format:
        handlers.append(JsonlFileHandler(logs / "events.jsonl", run_id, stage))
    return tuple(handlers)
