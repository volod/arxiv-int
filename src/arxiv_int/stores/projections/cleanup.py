"""Plan and optionally drop retired or failed projection engine objects."""

from collections.abc import Mapping

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from arxiv_int.stores.projections.adapters.graph import drop_graph_objects
from arxiv_int.stores.projections.adapters.lexical import drop_lexical
from arxiv_int.stores.projections.adapters.vector import drop_vector
from arxiv_int.stores.projections.database_lock import lock_projection_catalog
from arxiv_int.stores.projections.ids import evidence_id, sanitize_version_id
from arxiv_int.stores.projections.model import KIND_GRAPH, KIND_LEXICAL, KIND_VECTOR
from arxiv_int.stores.projections.registry import cleanup_candidates, mark_dropped
from arxiv_int.stores.projections.tables import CLEANUP


def plan_cleanup(
    connection: Connection, *, kinds: tuple[str, ...] | None = None
) -> tuple[dict[str, str], ...]:
    """Record drop plans for failed or retired versions that are not active."""
    lock_projection_catalog(connection)
    planned = tuple(
        item for item in cleanup_candidates(connection) if kinds is None or item["kind"] in kinds
    )
    for item in planned:
        statement = insert(CLEANUP).values(
            cleanup_id=evidence_id(item["projection_id"], "cleanup"),
            projection_id=item["projection_id"],
            engine_object=item["engine_object"],
            status="planned",
        )
        statement = statement.on_conflict_do_update(
            index_elements=["cleanup_id"],
            set_={"engine_object": item["engine_object"], "status": "planned"},
        )
        connection.execute(statement)
    return planned


def apply_cleanup(
    connection: Connection, planned: tuple[Mapping[str, str], ...], *, age_enabled: bool
) -> tuple[dict[str, str], ...]:
    """Drop planned engine objects and mark metadata dropped."""
    lock_projection_catalog(connection)
    eligible = {item["projection_id"] for item in cleanup_candidates(connection)}
    executed: list[dict[str, str]] = []
    for item in planned:
        if item["projection_id"] not in eligible:
            continue
        kind = item["kind"]
        version_id = sanitize_version_id(item["projection_id"].split(":", 1)[-1])
        if kind == KIND_LEXICAL:
            drop_lexical(connection, version_id)
        elif kind == KIND_VECTOR:
            drop_vector(connection, version_id)
        elif kind == KIND_GRAPH:
            drop_graph_objects(connection, version_id, age_enabled=age_enabled)
        mark_dropped(connection, item["projection_id"])
        executed.append({**dict(item), "status": "executed"})
    return tuple(executed)
