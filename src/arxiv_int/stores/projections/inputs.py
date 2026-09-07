"""Read isolated dbt projection inputs used by engine adapters."""

from sqlalchemy import Connection

from arxiv_int.stores.projections.ids import derived_relation
from arxiv_int.stores.projections.model import KIND_GRAPH, KIND_LEXICAL, KIND_VECTOR
from arxiv_int.stores.projections.reconcile import fetch_ids, relation_exists

MODEL_LEXICAL = "proj_lexical_rows"
MODEL_VECTOR = "proj_vector_rows"
MODEL_VERTICES = "proj_graph_vertices"
MODEL_EDGES = "proj_graph_edges"
LOGICAL_COLUMNS = {
    KIND_LEXICAL: "chunk_id",
    KIND_VECTOR: "embedding_id",
    KIND_GRAPH: "object_id",
}


def source_relation(kind: str, version_id: str, *, edges: bool = False) -> str:
    """Return the derived input table for one kind."""
    if kind == KIND_LEXICAL:
        return derived_relation(MODEL_LEXICAL, version_id)
    if kind == KIND_VECTOR:
        return derived_relation(MODEL_VECTOR, version_id)
    if edges:
        return derived_relation(MODEL_EDGES, version_id)
    return derived_relation(MODEL_VERTICES, version_id)


def expected_ids(connection: Connection, kind: str, version_id: str) -> tuple[str, ...]:
    """Return logical ids from the dbt input for one kind."""
    column = LOGICAL_COLUMNS[kind]
    return fetch_ids(connection, source_relation(kind, version_id), column)


def require_sources(connection: Connection, kind: str, version_id: str) -> None:
    """Refuse to build when the described dbt input relation is missing."""
    names = [source_relation(kind, version_id)]
    if kind == KIND_GRAPH:
        names.append(source_relation(kind, version_id, edges=True))
    missing = [name for name in names if not relation_exists(connection, name)]
    if missing:
        raise LookupError("missing derived projection input: " + ", ".join(missing))
