"""Legal run, stage, shard, and lease transitions plus bounded retry classes."""

from typing import Literal, cast

RunStatus = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
    "quarantined",
    "superseded",
    "stale",
    "pruned",
]
StageStatus = RunStatus
ShardStatus = RunStatus
LeaseStatus = Literal["acquired", "released", "expired", "failed"]
ManifestStatus = Literal["staging", "accepted", "rejected"]
FailureClass = Literal["transient", "permanent"]

RUN_STATUSES: frozenset[str] = frozenset(
    {
        "pending",
        "running",
        "succeeded",
        "failed",
        "quarantined",
        "superseded",
        "stale",
        "pruned",
    }
)
LEASE_STATUSES: frozenset[str] = frozenset({"acquired", "released", "expired", "failed"})
MANIFEST_STATUSES: frozenset[str] = frozenset({"staging", "accepted", "rejected"})

LEDGER_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"running", "failed", "stale", "pruned"}),
    "running": frozenset({"succeeded", "failed", "quarantined", "stale"}),
    "succeeded": frozenset({"superseded", "stale", "pruned", "quarantined"}),
    "failed": frozenset({"stale", "pruned", "superseded"}),
    "quarantined": frozenset({"stale", "pruned", "superseded"}),
    "superseded": frozenset({"stale", "pruned"}),
    "stale": frozenset({"pruned", "superseded"}),
    "pruned": frozenset(),
}
LEASE_TRANSITIONS: dict[str, frozenset[str]] = {
    "acquired": frozenset({"released", "expired", "failed"}),
    "released": frozenset(),
    "expired": frozenset(),
    "failed": frozenset(),
}
MANIFEST_TRANSITIONS: dict[str, frozenset[str]] = {
    "staging": frozenset({"accepted", "rejected"}),
    "accepted": frozenset(),
    "rejected": frozenset(),
}

TRANSIENT_CODES: frozenset[str] = frozenset(
    {"timeout", "lease-expired", "connection", "busy", "interrupted"}
)
PERMANENT_CODES: frozenset[str] = frozenset(
    {"validation", "quality", "illegal-input", "checksum", "activation"}
)
DEFAULT_MAX_TRANSIENT_ATTEMPTS = 3


class IllegalTransitionError(ValueError):
    """Raised when a ledger row would move to a forbidden status."""


def allowed_targets(kind: str, current: str) -> frozenset[str]:
    """Return legal next statuses for a ledger kind."""
    table = _table_for(kind)
    try:
        return table[current]
    except KeyError as error:
        raise IllegalTransitionError(f"unknown {kind} status {current!r}") from error


def require_transition(kind: str, current: str, target: str) -> None:
    """Refuse a status change that the state machine does not allow."""
    if current == target:
        return
    allowed = allowed_targets(kind, current)
    if target not in allowed:
        raise IllegalTransitionError(f"illegal {kind} transition {current!r} -> {target!r}")


def as_shard_status(value: str) -> ShardStatus:
    """Parse a stored shard or run status token."""
    if value not in RUN_STATUSES:
        raise ValueError(f"unknown shard status {value!r}")
    return cast(ShardStatus, value)


def as_lease_status(value: str) -> LeaseStatus:
    """Parse a stored reuse-lease status token."""
    if value not in LEASE_STATUSES:
        raise ValueError(f"unknown lease status {value!r}")
    return cast(LeaseStatus, value)


def classify_failure(code: str) -> FailureClass:
    """Map a bounded error code onto a retry class."""
    if code in TRANSIENT_CODES:
        return "transient"
    if code in PERMANENT_CODES:
        return "permanent"
    raise ValueError(f"unknown failure code {code!r}")


def can_retry(failure_class: FailureClass, attempt: int, max_attempts: int) -> bool:
    """Return whether another attempt is allowed for this failure class."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if failure_class == "permanent":
        return False
    return attempt < max_attempts


def _table_for(kind: str) -> dict[str, frozenset[str]]:
    if kind in {"run", "stage", "shard"}:
        return LEDGER_TRANSITIONS
    if kind == "lease":
        return LEASE_TRANSITIONS
    if kind == "manifest":
        return MANIFEST_TRANSITIONS
    raise ValueError(f"unknown ledger kind {kind!r}")
