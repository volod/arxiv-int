"""Two-phase stale prune plan and event contracts."""

from dataclasses import dataclass

from arxiv_int.interfaces.tokens import require_token
from arxiv_int.pipeline.run.reuse_index import ReuseEntry

PRUNE_SCHEMA = "arxiv-int.prune-event.v1"
PROTECTION_KINDS = frozenset(
    {"active", "pinned", "reviewed", "rollback", "ledger", "backup", "sole-recovery"}
)


@dataclass(frozen=True, slots=True)
class Protection:
    """One reason a derived attempt cannot be physically deleted."""

    directory: str
    kind: str
    detail: str

    def __post_init__(self) -> None:
        require_token(self.kind, "kind")
        if self.kind not in PROTECTION_KINDS:
            raise ValueError(f"unknown prune protection {self.kind!r}")


@dataclass(frozen=True, slots=True)
class PrunePlan:
    """Dry-run list of stale derived attempts; apply requires this fingerprint."""

    schema: str
    plan_id: str
    fingerprint: str
    entries: tuple[ReuseEntry, ...]
    eligible: tuple[ReuseEntry, ...]
    bytes: int
    blocked: tuple[Protection, ...]

    def __post_init__(self) -> None:
        if self.schema != PRUNE_SCHEMA:
            raise ValueError(f"unsupported prune-event schema {self.schema!r}")
        require_token(self.plan_id, "plan_id")
        require_token(self.fingerprint, "fingerprint")


@dataclass(frozen=True, slots=True)
class PruneEvent:
    """Recorded dry-run or apply outcome."""

    schema: str
    plan_id: str
    fingerprint: str
    status: str
    bytes_removed: int
    retained: tuple[str, ...]
    detail: str = ""

    def __post_init__(self) -> None:
        if self.schema != PRUNE_SCHEMA:
            raise ValueError(f"unsupported prune-event schema {self.schema!r}")
        if self.status not in {"planned", "applied", "refused"}:
            raise ValueError(f"unknown prune status {self.status!r}")
