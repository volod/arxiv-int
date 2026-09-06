"""Load ontology Turtle assets into a structured catalog."""

import pathlib
from typing import Any

from arxiv_int.contracts._yaml import load_mapping
from arxiv_int.ontology.catalog import OntologyCatalog, OntologyClass, OntologyPredicate
from arxiv_int.ontology.paths import ontology_root_for, require_graph_dependencies

AI = "https://arxiv-int.local/ns/ontology#"
OWL = "http://www.w3.org/2002/07/owl#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
SKOS = "http://www.w3.org/2004/02/skos/core#"


def load_manifest(ontology_root: pathlib.Path) -> dict[str, Any]:
    """Load ``manifest.yaml`` from an ontology root."""
    return load_mapping(ontology_root / "manifest.yaml")


def _literal_map(graph: Any, subject: Any, predicate: Any) -> dict[str, str]:
    labels: dict[str, str] = {}
    for value in graph.objects(subject, predicate):
        language = getattr(value, "language", None) or "und"
        labels[str(language)] = str(value)
    return labels


def _uri_values(graph: Any, subject: Any, predicate: Any) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in graph.objects(subject, predicate)}))


def _status(graph: Any, subject: Any) -> str:
    from rdflib import Literal, URIRef

    status_uri = URIRef(f"{AI}status")
    status_values = [str(value) for value in graph.objects(subject, status_uri)]
    if status_values:
        return status_values[0]
    deprecated = URIRef(f"{OWL}deprecated")
    if any(value == Literal(True) for value in graph.objects(subject, deprecated)):
        return "deprecated"
    return "active"


def _load_graph(ontology_root: pathlib.Path, relative: str) -> Any:
    from rdflib import Graph

    path = (ontology_root / relative).resolve()
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def _class_entries(graph: Any) -> dict[str, OntologyClass]:
    from rdflib import URIRef

    rdf_type = URIRef(f"{RDF}type")
    owl_class = URIRef(f"{OWL}Class")
    rdfs_label = URIRef(f"{RDFS}label")
    sub_class = URIRef(f"{RDFS}subClassOf")
    disjoint = URIRef(f"{OWL}disjointWith")
    term_id = URIRef(f"{AI}termId")
    classes: dict[str, OntologyClass] = {}
    for subject in graph.subjects(rdf_type, owl_class):
        uri = str(subject)
        term_values = [str(value) for value in graph.objects(subject, term_id)]
        if not term_values:
            continue
        classes[uri] = OntologyClass(
            uri=uri,
            term_id=term_values[0],
            status=_status(graph, subject),
            labels=_literal_map(graph, subject, rdfs_label),
            parents=_uri_values(graph, subject, sub_class),
            disjoint_with=_uri_values(graph, subject, disjoint),
        )
    return classes


def _predicate_kind(graph: Any, subject: Any) -> str:
    from rdflib import URIRef

    rdf_type = URIRef(f"{RDF}type")
    types = {str(value) for value in graph.objects(subject, rdf_type)}
    if f"{OWL}DatatypeProperty" in types:
        return "datatype"
    return "object"


def _predicate_entries(graph: Any) -> dict[str, OntologyPredicate]:
    from rdflib import Literal, URIRef

    rdf_type = URIRef(f"{RDF}type")
    object_property = URIRef(f"{OWL}ObjectProperty")
    datatype_property = URIRef(f"{OWL}DatatypeProperty")
    functional = URIRef(f"{OWL}FunctionalProperty")
    deprecated = URIRef(f"{OWL}deprecated")
    rdfs_label = URIRef(f"{RDFS}label")
    domain = URIRef(f"{RDFS}domain")
    range_ = URIRef(f"{RDFS}range")
    term_id = URIRef(f"{AI}termId")
    binding = URIRef(f"{AI}contractBinding")
    successor = URIRef(f"{AI}successor")
    quantity = URIRef(f"{AI}quantityKind")
    unit = URIRef(f"{AI}canonicalUnit")
    predicates: dict[str, OntologyPredicate] = {}
    subjects = set(graph.subjects(rdf_type, object_property)) | set(
        graph.subjects(rdf_type, datatype_property)
    )
    for subject in subjects:
        uri = str(subject)
        term_values = [str(value) for value in graph.objects(subject, term_id)]
        binding_values = [str(value) for value in graph.objects(subject, binding)]
        if not term_values or not binding_values:
            continue
        successors = [str(value) for value in graph.objects(subject, successor)]
        quantity_values = [str(value) for value in graph.objects(subject, quantity)]
        unit_values = [str(value) for value in graph.objects(subject, unit)]
        predicates[uri] = OntologyPredicate(
            uri=uri,
            term_id=term_values[0],
            status=_status(graph, subject),
            kind=_predicate_kind(graph, subject),
            contract_binding=binding_values[0],
            labels=_literal_map(graph, subject, rdfs_label),
            domains=_uri_values(graph, subject, domain),
            ranges=_uri_values(graph, subject, range_),
            functional=(subject, rdf_type, functional) in graph,
            deprecated=any(value == Literal(True) for value in graph.objects(subject, deprecated)),
            successor=successors[0] if successors else None,
            quantity_kind=quantity_values[0] if quantity_values else None,
            canonical_unit=unit_values[0] if unit_values else None,
        )
    return predicates


def _semantic_matches(graph: Any) -> dict[str, tuple[str, ...]]:
    from rdflib import URIRef

    matches: dict[str, set[str]] = {}
    for predicate_name in ("exactMatch", "relatedMatch", "closeMatch"):
        predicate = URIRef(f"{SKOS}{predicate_name}")
        for subject, _, obj in graph.triples((None, predicate, None)):
            matches.setdefault(str(subject), set()).add(str(obj))
    return {key: tuple(sorted(value)) for key, value in sorted(matches.items())}


def load_ontology_graphs(ontology_root: pathlib.Path | None = None) -> tuple[Any, Any, Any]:
    """Parse core, mappings, and shapes graphs."""
    require_graph_dependencies()
    root = ontology_root if ontology_root is not None else ontology_root_for()
    manifest = load_manifest(root)
    assets = manifest.get("assets") or {}
    core = _load_graph(root, str(assets.get("core", "core.ttl")))
    mappings = _load_graph(root, str(assets.get("mappings", "mappings.ttl")))
    shapes = _load_graph(root, str(assets.get("shapes", "shapes.shacl.ttl")))
    return core, mappings, shapes


def load_ontology_catalog(ontology_root: pathlib.Path | None = None) -> OntologyCatalog:
    """Load and index ontology assets under ``ontology_root``."""
    require_graph_dependencies()
    root = ontology_root if ontology_root is not None else ontology_root_for()
    manifest = load_manifest(root)
    core, mappings, _shapes = load_ontology_graphs(root)
    merged = core + mappings
    return OntologyCatalog(
        ontology_id=str(manifest.get("ontologyId", "")),
        version=str(manifest.get("version", "")),
        classes=_class_entries(merged),
        predicates=_predicate_entries(merged),
        semantic_matches=_semantic_matches(merged),
    )
