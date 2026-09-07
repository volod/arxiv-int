"""Named bounds for serialized logging, progress, and metric labels."""

from typing import Literal

SCHEMA_ID = "arxiv-int.observability.v1"
DEFAULT_QUEUE_MAXSIZE = 4096
DEFAULT_PROGRESS_INTERVAL_SEC = 30.0
DEFAULT_PROGRESS_COUNT_INTERVAL = 100
DEFAULT_STALL_TIMEOUT_SEC = 90.0
DEFAULT_SLOW_ETA_SEC = 3600.0
MAX_LABEL_VALUE_LEN = 64
MAX_SHARD_TOKEN_LEN = 16
MAX_DETAIL_CHARS = 240
METRIC_LABEL_NAMES = frozenset({"stage", "event", "worker_state", "device", "failure_class"})
FORBIDDEN_LABEL_NAMES = frozenset(
    {"run_id", "shard", "shard_id", "document_id", "path", "prompt", "text"}
)
WORKER_STATES = ("running", "slow", "stalled", "completed", "failed")
WorkerState = Literal["running", "slow", "stalled", "completed", "failed"]
WORKER_STATE_BY_NAME: dict[str, WorkerState] = {
    "running": "running",
    "slow": "slow",
    "stalled": "stalled",
    "completed": "completed",
    "failed": "failed",
}
LOG_FORMATS = ("console", "jsonl", "console+jsonl")
DEFAULT_LOG_FORMAT = "console+jsonl"
PROGRESS_LOG_NAME = "progress.jsonl"
CONSOLE_LOG_NAME = "console.log"
MANIFEST_NAME = "observability-manifest.json"
RESOURCE_EVENT = "pipeline.resource"
