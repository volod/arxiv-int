"""Resolve and describe the active ParadeDB lexical projection."""

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import Connection, select, text
from sqlalchemy.exc import SQLAlchemyError

from arxiv_int.stores.projections.adapters.lexical import (
    TOKENIZER_FINGERPRINT,
    lexical_index,
    lexical_table,
)
from arxiv_int.stores.projections.adapters.lexical_search import (
    BUILD_ACTIVITY_SQL,
    INDEX_SIZE_SQL,
)
from arxiv_int.stores.projections.model import KIND_LEXICAL, STATUS_ACTIVE
from arxiv_int.stores.projections.profiles import projection_input_fingerprint
from arxiv_int.stores.projections.tables import ACTIVE, PROJECTIONS

BUILD_QUERY_PATTERN = "%using bm25%"


class LexicalUnavailableError(RuntimeError):
    """Raised when no validated lexical projection is active."""


class LexicalQueryError(RuntimeError):
    """Raised when the engine refuses a lexical query or diagnostic."""


@dataclass(frozen=True, slots=True)
class LexicalTarget:
    """The active covering table, its BM25 index, and its load identity."""

    projection_id: str
    version_id: str
    table: str
    index: str
    row_count: int
    checksum: str
    status: str
    tokenizer_fingerprint: str = TOKENIZER_FINGERPRINT

    def as_json_dict(self) -> dict[str, object]:
        """Return a secret-free description of the active projection."""
        return {
            "checksum": self.checksum,
            "index": self.index,
            "projectionId": self.projection_id,
            "rowCount": self.row_count,
            "status": self.status,
            "table": self.table,
            "tokenizerFingerprint": self.tokenizer_fingerprint,
            "versionId": self.version_id,
        }


def active_target(connection: Connection) -> LexicalTarget:
    """Return the active lexical projection, or refuse with an actionable reason."""
    statement = (
        select(
            PROJECTIONS.c.projection_id,
            PROJECTIONS.c.version_id,
            PROJECTIONS.c.status,
            PROJECTIONS.c.row_count,
            PROJECTIONS.c.checksum,
            PROJECTIONS.c.input_fingerprint,
        )
        .select_from(
            ACTIVE.join(PROJECTIONS, ACTIVE.c.projection_id == PROJECTIONS.c.projection_id)
        )
        .where(ACTIVE.c.kind == KIND_LEXICAL)
    )
    try:
        row = connection.execute(statement).first()
    except SQLAlchemyError as error:
        raise LexicalUnavailableError(
            "cannot read the projection registry; apply store revisions first "
            f"({_driver_detail(error)})"
        ) from error
    if row is None:
        raise LexicalUnavailableError(
            "no active lexical projection; run the load-lexical stage or "
            "'arxiv-int store projections-build --kind lexical --activate'"
        )
    version_id = str(row.version_id)
    target = LexicalTarget(
        projection_id=str(row.projection_id),
        version_id=version_id,
        table=lexical_table(version_id),
        index=lexical_index(version_id),
        row_count=int(row.row_count or 0),
        checksum=str(row.checksum or ""),
        status=str(row.status),
    )
    if target.status != STATUS_ACTIVE:
        raise LexicalUnavailableError(
            f"lexical projection {target.projection_id} is {target.status}, not active"
        )
    expected = projection_input_fingerprint(KIND_LEXICAL, version_id, target.checksum)
    if str(row.input_fingerprint or "") != expected:
        raise LexicalUnavailableError(
            f"lexical projection {target.projection_id} was built under a different tokenizer "
            f"profile than {TOKENIZER_FINGERPRINT}; rebuild it with "
            "'arxiv-int store projections-build --kind lexical --activate'"
        )
    return target


def index_size(connection: Connection, target: LexicalTarget) -> Mapping[str, int]:
    """Return covering-table and BM25 index byte sizes for capacity diagnostics."""
    row = connection.execute(
        text(INDEX_SIZE_SQL),
        {"index_ref": f"search.{target.index}", "table_ref": target.table},
    ).first()
    if row is None:
        return {"index_bytes": 0, "table_bytes": 0}
    return {"index_bytes": int(row.index_bytes), "table_bytes": int(row.table_bytes)}


def concurrent_builds(connection: Connection) -> tuple[Mapping[str, object], ...]:
    """Return in-flight BM25 index builds so a rebuild stays observable."""
    rows = connection.execute(text(BUILD_ACTIVITY_SQL), {"pattern": BUILD_QUERY_PATTERN}).fetchall()
    return tuple(
        {
            "pid": int(row.pid),
            "state": str(row.state or "unknown"),
            "wait": f"{row.wait_event_type or 'none'}:{row.wait_event or 'none'}",
            "elapsedSeconds": round(float(row.elapsed_seconds or 0.0), 3),
        }
        for row in rows
    )


def _driver_detail(error: SQLAlchemyError) -> str:
    """Return one short actionable line from a driver error."""
    message = str(getattr(error, "orig", None) or error).strip()
    return message.splitlines()[0][:200] if message else error.__class__.__name__
