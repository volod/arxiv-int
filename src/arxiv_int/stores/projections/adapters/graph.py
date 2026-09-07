"""AGE Cypher, recursive-SQL reference, and open graph exports."""

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from arxiv_int.stores.projections.ids import (
    age_graph_name,
    cypher_string,
    qualified_table,
    require_ident,
)
from arxiv_int.stores.projections.model import ENGINE_AGE, ENGINE_RECURSIVE_SQL, KIND_GRAPH
from arxiv_int.stores.projections.paths import export_dir
from arxiv_int.stores.projections.reconcile import fetch_maps, one_hop_sql, sample_starts

VERTEX_COLUMNS = ("object_id", "object_type", "preferred_label", "review_state")
EDGE_COLUMNS = (
    "fact_id",
    "subject_object_id",
    "predicate_id",
    "object_object_id",
    "document_id",
    "status",
)


def vertex_table(version_id: str) -> str:
    """Return the relational vertex table used by AGE and recursive SQL."""
    return qualified_table(KIND_GRAPH, version_id, suffix="vertices")


def edge_table(version_id: str) -> str:
    """Return the relational edge table used by AGE and recursive SQL."""
    return qualified_table(KIND_GRAPH, version_id, suffix="edges")


def drop_graph_objects(connection: Connection, version_id: str, *, age_enabled: bool) -> None:
    """Drop versioned graph tables and an AGE graph when present."""
    if age_enabled:
        with _age_autocommit(connection) as age:
            _drop_age_graph(age, age_graph_name(version_id))
    connection.execute(text(f"DROP TABLE IF EXISTS {edge_table(version_id)}"))
    connection.execute(text(f"DROP TABLE IF EXISTS {vertex_table(version_id)}"))


def _copy_table(connection: Connection, source: str, target: str, columns: tuple[str, ...]) -> None:
    schema, _, table = source.partition(".")
    require_ident(schema)
    require_ident(table)
    selected = ", ".join(require_ident(name) for name in columns)
    connection.execute(text(f"DROP TABLE IF EXISTS {target}"))
    connection.execute(text(f"CREATE TABLE {target} AS SELECT {selected} FROM {schema}.{table}"))


def build_relational_graph(
    connection: Connection, version_id: str, vertices: str, edges: str
) -> None:
    """Materialize compact vertex and edge tables without duplicating large text."""
    _copy_table(connection, vertices, vertex_table(version_id), VERTEX_COLUMNS)
    connection.execute(text(f"ALTER TABLE {vertex_table(version_id)} ADD PRIMARY KEY (object_id)"))
    _copy_table(connection, edges, edge_table(version_id), EDGE_COLUMNS)
    connection.execute(text(f"ALTER TABLE {edge_table(version_id)} ADD PRIMARY KEY (fact_id)"))


def load_age_graph(connection: Connection, version_id: str) -> str:
    """Create a versioned AGE graph from in-memory relational rows."""
    name = age_graph_name(version_id)
    vertices = fetch_maps(connection, vertex_table(version_id), VERTEX_COLUMNS)
    edges = fetch_maps(connection, edge_table(version_id), EDGE_COLUMNS)
    with _age_autocommit(connection) as age:
        _drop_age_graph(age, name)
        age.exec_driver_sql(f"SELECT * FROM create_graph('{name}')")
        for vertex in vertices:
            ident = cypher_string(str(vertex["object_id"]))
            kind = cypher_string(str(vertex.get("object_type") or "Object"))
            label = cypher_string(str(vertex.get("preferred_label") or ""))
            _cypher(
                age,
                name,
                f"CREATE (:Object {{id: '{ident}', type: '{kind}', label: '{label}'}})",
                "v agtype",
            )
        for edge in edges:
            src = cypher_string(str(edge["subject_object_id"]))
            dst = cypher_string(str(edge["object_object_id"]))
            pred = cypher_string(str(edge.get("predicate_id") or "FACT"))
            fact = cypher_string(str(edge["fact_id"]))
            _cypher(
                age,
                name,
                f"MATCH (a:Object {{id: '{src}'}}), (b:Object {{id: '{dst}'}}) "
                f"CREATE (a)-[:FACT {{id: '{fact}', predicate: '{pred}'}}]->(b)",
                "e agtype",
            )
    return name


def cypher_one_hop(
    connection: Connection, version_id: str, start_id: str
) -> tuple[tuple[str, str], ...]:
    """Return one-hop Cypher paths from a start vertex."""
    name = age_graph_name(version_id)
    ident = cypher_string(start_id)
    with _age_autocommit(connection) as age:
        rows = age.exec_driver_sql(
            f"SELECT * FROM cypher('{name}', $$ "
            f"MATCH (a:Object {{id: '{ident}'}})-[:FACT]->(b:Object) "
            "RETURN a.id, b.id "
            "$$) AS (src agtype, dst agtype)"
        ).all()
    return tuple((_agtype_text(row[0]), _agtype_text(row[1])) for row in rows)


def sampled_parity(
    connection: Connection, version_id: str, vertex_ids: Sequence[str], *, age_enabled: bool
) -> tuple[bool, str]:
    """Compare sampled recursive SQL paths to Cypher when AGE is enabled."""
    starts = sample_starts(vertex_ids)
    if not starts:
        return True, "no vertices to sample"
    edges = edge_table(version_id)
    for start in starts:
        reference = one_hop_sql(connection, edges, start, depth=1)
        if not age_enabled:
            continue
        observed = cypher_one_hop(connection, version_id, start)
        if sorted(reference) != sorted(observed):
            return False, f"SQL/Cypher mismatch starting at {start}"
    if age_enabled:
        return True, "sampled SQL and Cypher paths match"
    return True, "recursive SQL reference recorded; AGE disabled"


def write_open_exports(
    artifact_dir: Path, vertices: Sequence[dict[str, Any]], edges: Sequence[dict[str, Any]]
) -> tuple[Path, Path, Path]:
    """Write GraphML, JSON-LD, and Turtle exports that do not require AGE."""
    destination = export_dir(artifact_dir)
    destination.mkdir(parents=True, exist_ok=True)
    graphml = destination / "graph.graphml"
    jsonld = destination / "graph.jsonld"
    turtle = destination / "graph.ttl"
    graphml.write_text(_graphml(vertices, edges), encoding="utf-8")
    jsonld.write_text(_jsonld(vertices, edges), encoding="utf-8")
    turtle.write_text(_turtle(vertices, edges), encoding="utf-8")
    return graphml, jsonld, turtle


def engine_name(age_enabled: bool) -> str:
    """Return AGE or recursive SQL according to the compatibility gate."""
    return ENGINE_AGE if age_enabled else ENGINE_RECURSIVE_SQL


@contextmanager
def _age_autocommit(connection: Connection) -> Iterator[Connection]:
    session = connection.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        session.execute(text("LOAD 'age'"))
        session.execute(text('SET search_path = ag_catalog, "$user", public'))
        yield session
    finally:
        session.close()


def _drop_age_graph(session: Connection, name: str) -> None:
    require_ident(name)
    exists = session.execute(
        text("SELECT EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = :name)"),
        {"name": name},
    ).scalar()
    if exists:
        session.exec_driver_sql(f"SELECT * FROM drop_graph('{name}', true)")


def _cypher(session: Connection, graph: str, body: str, columns: str) -> None:
    session.exec_driver_sql(f"SELECT * FROM cypher('{graph}', $$ {body} $$) AS ({columns})")


def _agtype_text(value: object) -> str:
    return str(value).strip().strip('"')


def _graphml(vertices: Sequence[dict[str, Any]], edges: Sequence[dict[str, Any]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '<graph id="G" edgedefault="directed">',
    ]
    for vertex in vertices:
        ident = str(vertex["object_id"])
        lines.append(f'<node id="{ident}"/>')
    for edge in edges:
        lines.append(
            f'<edge id="{edge["fact_id"]}" source="{edge["subject_object_id"]}" '
            f'target="{edge["object_object_id"]}"/>'
        )
    lines.extend(["</graph>", "</graphml>", ""])
    return "\n".join(lines)


def _jsonld(vertices: Sequence[dict[str, Any]], edges: Sequence[dict[str, Any]]) -> str:
    nodes = [
        {
            "@id": f"urn:arxiv-int:object:{item['object_id']}",
            "@type": str(item.get("object_type") or "Object"),
            "label": item.get("preferred_label"),
        }
        for item in vertices
    ]
    rels = [
        {
            "@id": f"urn:arxiv-int:fact:{item['fact_id']}",
            "subject": f"urn:arxiv-int:object:{item['subject_object_id']}",
            "predicate": item.get("predicate_id"),
            "object": f"urn:arxiv-int:object:{item['object_object_id']}",
        }
        for item in edges
    ]
    payload = {
        "@context": {"label": "http://www.w3.org/2000/01/rdf-schema#label"},
        "@graph": nodes + rels,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _turtle(vertices: Sequence[dict[str, Any]], edges: Sequence[dict[str, Any]]) -> str:
    lines = ["@prefix kg: <urn:arxiv-int:kg:> .", ""]
    for item in vertices:
        ident = str(item["object_id"]).replace(":", "_")
        label = str(item.get("preferred_label") or ident).replace('"', '\\"')
        lines.append(f'kg:{ident} a kg:Object ; kg:label "{label}" .')
    for item in edges:
        src = str(item["subject_object_id"]).replace(":", "_")
        dst = str(item["object_object_id"]).replace(":", "_")
        pred = str(item.get("predicate_id") or "FACT").replace(":", "_")
        lines.append(f"kg:{src} kg:{pred} kg:{dst} .")
    lines.append("")
    return "\n".join(lines)
