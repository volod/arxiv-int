"""Optional OWL RL reasoning over ontology assets."""

from pathlib import Path
from typing import Any

from arxiv_int.ontology.load import load_ontology_graphs
from arxiv_int.ontology.paths import require_graph_dependencies


def _owlrl() -> Any:
    import owlrl  # type: ignore[import-untyped]

    return owlrl


def expand_with_owlrl(ontology_root: Path | None = None) -> Any:
    """Return core+mappings expanded with OWL RL materialization via owlrl."""
    require_graph_dependencies()
    from rdflib import Graph

    owlrl = _owlrl()
    core, mappings, _shapes = load_ontology_graphs(ontology_root)
    graph = Graph()
    graph += core
    graph += mappings
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)
    return graph


def disjointness_inconsistent(
    individual_types: tuple[str, ...], ontology_root: Path | None = None
) -> bool:
    """Return True when declared disjoint classes are asserted on one individual."""
    require_graph_dependencies()
    from rdflib import URIRef
    from rdflib.namespace import OWL, RDF

    owlrl = _owlrl()
    expanded = expand_with_owlrl(ontology_root)
    probe = expanded.__class__()
    probe += expanded
    node = URIRef("urn:arxiv-int:probe:individual")
    for type_uri in individual_types:
        probe.add((node, RDF.type, URIRef(type_uri)))
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(probe)
    if (node, RDF.type, OWL.Nothing) in probe:
        return True
    types = {str(value) for value in probe.objects(node, RDF.type)}
    for left in types:
        for right in expanded.objects(URIRef(left), OWL.disjointWith):
            if str(right) in types:
                return True
    return False
