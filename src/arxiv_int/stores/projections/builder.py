"""Kind-specific staging builds and shared quality gates."""

from pathlib import Path

from sqlalchemy import Connection

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.stores.projections.adapters.graph import (
    EDGE_COLUMNS,
    VERTEX_COLUMNS,
    build_relational_graph,
    edge_table,
    load_age_graph,
    sampled_parity,
    vertex_table,
    write_open_exports,
)
from arxiv_int.stores.projections.adapters.graph import (
    engine_name as graph_engine,
)
from arxiv_int.stores.projections.adapters.lexical import (
    build_lexical,
    lexical_table,
)
from arxiv_int.stores.projections.adapters.lexical import (
    engine_name as lexical_engine,
)
from arxiv_int.stores.projections.adapters.vector import (
    build_vector,
    vector_table,
)
from arxiv_int.stores.projections.adapters.vector import (
    engine_name as vector_engine,
)
from arxiv_int.stores.projections.ids import projection_id
from arxiv_int.stores.projections.inputs import expected_ids, require_sources, source_relation
from arxiv_int.stores.projections.model import (
    KIND_GRAPH,
    KIND_LEXICAL,
    KIND_VECTOR,
    SCHEMA_VERSION,
    KindBuild,
    ProjectionRequest,
)
from arxiv_int.stores.projections.quality import (
    RULE_CHECKSUM,
    RULE_ENGINE,
    RULE_PARITY,
    RULE_ROW_COUNT,
    assemble_result,
    check_result,
    evidence_maps,
    pass_fail,
)
from arxiv_int.stores.projections.reconcile import (
    checksum_for,
    counts_match,
    fetch_ids,
    fetch_maps,
    relation_exists,
)
from arxiv_int.stores.projections.registry import (
    mark_failed,
    record_validation,
    upsert_staging,
    validated_status,
    write_evidence_rows,
)

_ID_COLUMNS = {KIND_LEXICAL: "chunk_id", KIND_VECTOR: "embedding_id", KIND_GRAPH: "object_id"}


def build_kind(
    connection: Connection,
    request: ProjectionRequest,
    artifact_dir: Path,
    *,
    kind: str,
    version_id: str,
    age_enabled: bool,
) -> KindBuild:
    """Stage one kind, reconcile ids, and refuse activation on quality failure."""
    require_sources(connection, kind, version_id)
    ident = projection_id(kind, version_id)
    engine, engine_object, observed = _materialize(
        connection, kind, version_id, age_enabled, artifact_dir
    )
    expected = expected_ids(connection, kind, version_id)
    upsert_staging(
        connection,
        projection_id=ident,
        kind=kind,
        version_id=version_id,
        engine=engine,
        engine_object=engine_object,
        run_id=request.run_id,
        schema_version=SCHEMA_VERSION,
    )
    count_ok = counts_match(expected, observed)
    checksum = checksum_for(observed)
    expected_sum = checksum_for(expected)
    parity_ok, parity_reason = True, "row identity only"
    if kind == KIND_GRAPH:
        parity_ok, parity_reason = sampled_parity(
            connection, version_id, observed, age_enabled=age_enabled
        )
    engine_ok = bool(engine_object) and (
        kind != KIND_LEXICAL or relation_exists(connection, lexical_table(version_id))
    )
    quality = assemble_result(
        kind,
        (
            check_result(
                RULE_ROW_COUNT,
                status=pass_fail(count_ok, checked=len(observed)),
                checked_count=len(observed),
                failed_count=0 if count_ok else abs(len(expected) - len(observed)),
                reason=None if count_ok else "row count does not match derived input",
            ),
            check_result(
                RULE_CHECKSUM,
                status=pass_fail(checksum == expected_sum, checked=len(observed)),
                checked_count=len(observed),
                reason=None if checksum == expected_sum else "logical id checksum mismatch",
            ),
            check_result(
                RULE_PARITY,
                status=pass_fail(parity_ok, checked=len(observed)),
                checked_count=len(observed),
                reason=parity_reason,
            ),
            check_result(
                RULE_ENGINE,
                status=pass_fail(engine_ok, checked=1),
                checked_count=1,
                reason=None if engine_ok else "engine object is missing",
            ),
        ),
        checked_rows=len(observed),
        fingerprint_parts=(kind, version_id, checksum),
    )
    status = validated_status(quality.publishable)
    record_validation(
        connection,
        projection_id=ident,
        status=status,
        row_count=len(observed),
        checksum=checksum,
        quality_status=quality.status,
        input_fingerprint=sha256_text(f"{kind}|{version_id}|{checksum}"),
        last_committed_id=observed[-1] if observed else None,
    )
    write_evidence_rows(connection, ident, evidence_maps(quality))
    if not quality.publishable:
        mark_failed(connection, ident, quality.status)
    return KindBuild(
        kind=kind,
        projection_id=ident,
        version_id=version_id,
        status=status,
        engine=engine,
        engine_object=engine_object,
        row_count=len(observed),
        checksum=checksum,
        quality_status=quality.status,
        publishable=quality.publishable,
        logical_ids=observed,
        detail=quality.reason or quality.status,
    )


def _materialize(
    connection: Connection,
    kind: str,
    version_id: str,
    age_enabled: bool,
    artifact_dir: Path,
) -> tuple[str, str, tuple[str, ...]]:
    column = _ID_COLUMNS[kind]
    if kind == KIND_LEXICAL:
        engine_object = build_lexical(connection, version_id, source_relation(kind, version_id))
        observed = fetch_ids(connection, lexical_table(version_id), column)
        return lexical_engine(), engine_object, observed
    if kind == KIND_VECTOR:
        engine_object = build_vector(connection, version_id, source_relation(kind, version_id))
        observed = fetch_ids(connection, vector_table(version_id), column)
        return vector_engine(), engine_object, observed
    build_relational_graph(
        connection,
        version_id,
        source_relation(kind, version_id),
        source_relation(kind, version_id, edges=True),
    )
    vertices = fetch_maps(connection, vertex_table(version_id), VERTEX_COLUMNS)
    edges = fetch_maps(connection, edge_table(version_id), EDGE_COLUMNS)
    write_open_exports(artifact_dir, vertices, edges)
    engine_object = vertex_table(version_id)
    if age_enabled:
        engine_object = load_age_graph(connection, version_id)
    observed = fetch_ids(connection, vertex_table(version_id), column)
    return graph_engine(age_enabled), engine_object, observed
