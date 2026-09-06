"""SHACL validation and RDF graph helpers for ontology fixtures."""

from pathlib import Path
from typing import Any

from arxiv_int.ontology.catalog import OntologyCatalog
from arxiv_int.ontology.load import load_ontology_catalog, load_ontology_graphs
from arxiv_int.ontology.paths import require_graph_dependencies
from arxiv_int.ontology.validate import FactAssertion


def _class_uri(catalog: OntologyCatalog, type_key: str) -> str:
    item = catalog.class_by_uri_or_term(type_key)
    if item is not None:
        return item.uri
    return type_key


def _predicate_uri(catalog: OntologyCatalog, predicate_key: str) -> str:
    item = catalog.predicate_by_uri_or_term(predicate_key)
    if item is not None:
        return item.uri
    return predicate_key


def assertions_to_graph(
    assertions: tuple[FactAssertion, ...] | list[FactAssertion],
    *,
    catalog: OntologyCatalog | None = None,
    ontology_root: Path | None = None,
) -> Any:
    """Serialize application assertions into an RDF instance graph."""
    require_graph_dependencies()
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDF, XSD

    resolved = catalog if catalog is not None else load_ontology_catalog(ontology_root)
    graph = Graph()
    for assertion in assertions:
        subject = URIRef(f"urn:arxiv-int:node:{assertion.subject_id}")
        for type_key in assertion.subject_types:
            graph.add((subject, RDF.type, URIRef(_class_uri(resolved, type_key))))
        predicate_ref = URIRef(_predicate_uri(resolved, assertion.predicate))
        if assertion.object_id is not None:
            obj = URIRef(f"urn:arxiv-int:node:{assertion.object_id}")
            for type_key in assertion.object_types:
                graph.add((obj, RDF.type, URIRef(_class_uri(resolved, type_key))))
            graph.add((subject, predicate_ref, obj))
        elif assertion.literal_value is not None:
            datatype = assertion.literal_datatype or str(XSD.string)
            graph.add((subject, predicate_ref, Literal(assertion.literal_value, datatype=datatype)))
    return graph


def run_shacl(
    data_graph: Any,
    *,
    ontology_root: Path | None = None,
) -> tuple[bool, list[str]]:
    """Validate ``data_graph`` with the pinned shapes using pySHACL."""
    require_graph_dependencies()
    from pyshacl import validate

    _core, _mappings, shapes = load_ontology_graphs(ontology_root)
    conforms, _graph, text = validate(
        data_graph,
        shacl_graph=shapes,
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        inplace=False,
    )
    findings: list[str] = []
    if not conforms:
        for line in str(text).splitlines():
            stripped = line.strip()
            if stripped:
                findings.append(stripped)
        if not findings:
            findings.append("SHACL validation failed")
    return bool(conforms), findings


def validate_assertions_with_shacl(
    assertions: tuple[FactAssertion, ...] | list[FactAssertion],
    *,
    ontology_root: Path | None = None,
    catalog: OntologyCatalog | None = None,
) -> tuple[bool, list[str]]:
    """Build an RDF graph from assertions and validate it with SHACL."""
    graph = assertions_to_graph(assertions, catalog=catalog, ontology_root=ontology_root)
    return run_shacl(graph, ontology_root=ontology_root)
