"""Coverage-oriented ontology helper regressions."""

import shutil
from pathlib import Path

import pytest

pytest.importorskip("rdflib")
pytest.importorskip("pyshacl")
pytest.importorskip("owlrl")

from arxiv_int.ontology import load as load_mod
from arxiv_int.ontology.catalog import OntologyCatalog, OntologyClass, OntologyPredicate
from arxiv_int.ontology.check import check_ontology
from arxiv_int.ontology.evolution import (
    ONTOLOGY_ADDITIVE,
    ONTOLOGY_IDENTICAL,
    check_ontology_evolution,
    classify_ontology_evolution,
    load_evolution_baseline,
    ontology_snapshot,
    version_policy_errors,
    write_evolution_baseline,
)
from arxiv_int.ontology.generate import check_generation_drift, generate_ontology_bindings
from arxiv_int.ontology.load import load_ontology_catalog
from arxiv_int.ontology.paths import ontology_root_for, require_graph_dependencies
from arxiv_int.ontology.shacl import assertions_to_graph, run_shacl
from arxiv_int.ontology.validate import FactAssertion, validate_assertions
from tests.ontology import ontology_root, project_root


def test_catalog_lookups_and_subclass_closure() -> None:
    catalog = load_ontology_catalog(ontology_root())
    assert catalog.predicate_by_uri_or_term("missing") is None
    assert catalog.class_by_uri_or_term("missing") is None
    natural = catalog.class_by_uri_or_term("class.natural-person")
    assert natural is not None
    closure = catalog.subclass_closure(natural.uri)
    assert natural.uri in closure
    assert "https://arxiv-int.local/ns/class/Object" in closure
    assert catalog.class_by_uri_or_term(natural.uri) is natural


def test_ontology_root_for_and_graph_dependency_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    require_graph_dependencies()
    monkeypatch.setattr(
        "arxiv_int.ontology.paths.find_project_root",
        lambda explicit=None: tmp_path,
    )
    assert ontology_root_for(None) == (tmp_path / "ontology").resolve()
    assert ontology_root_for(tmp_path) == (tmp_path / "ontology").resolve()

    def _missing(name: str) -> None:
        raise ImportError(name)

    monkeypatch.setattr("arxiv_int.ontology.paths.importlib.import_module", _missing)
    with pytest.raises(RuntimeError, match="graph extra"):
        require_graph_dependencies()


def test_generation_drift_and_refresh(tmp_path: Path) -> None:
    copy = shutil.copytree(ontology_root(), tmp_path / "ontology")
    (copy / "generated" / "ontology.bindings.json").unlink()
    findings = check_generation_drift(copy)
    assert any("missing generated" in item for item in findings)
    generate_ontology_bindings(copy)
    assert check_generation_drift(copy) == []
    report = check_ontology(copy, project_root=project_root(), refresh_generated=True)
    assert report.ok


def test_evolution_version_policy_and_baseline_roundtrip(tmp_path: Path) -> None:
    copy = shutil.copytree(ontology_root(), tmp_path / "ontology")
    baseline = load_evolution_baseline(copy)
    current = ontology_snapshot(load_ontology_catalog(copy))
    assert classify_ontology_evolution(baseline, current)[0] == ONTOLOGY_IDENTICAL
    assert version_policy_errors(ONTOLOGY_IDENTICAL, "1.0.0", "1.1.0")
    assert version_policy_errors(ONTOLOGY_ADDITIVE, "1.0.0", "2.0.0")
    assert version_policy_errors(ONTOLOGY_ADDITIVE, "1.0.0", "1.0.0")
    (copy / "evolution" / "baseline.json").unlink()
    assert check_ontology_evolution(copy)
    write_evolution_baseline(copy)
    assert check_ontology_evolution(copy) == []
    (copy / "evolution" / "baseline.json").write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        load_evolution_baseline(copy)


def test_binding_and_parse_failure_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    copy = shutil.copytree(ontology_root(), tmp_path / "ontology")
    (copy / "core.ttl").write_text("@prefix broken\n", encoding="utf-8")
    report = check_ontology(copy, project_root=project_root())
    assert not report.ok
    assert any("parse failed" in item for item in report.findings)

    catalog = OntologyCatalog(
        ontology_id="urn:test",
        version="1.0.0",
        classes={},
        predicates={
            "https://example.test/p": OntologyPredicate(
                uri="https://example.test/p",
                term_id="pred.example",
                status="active",
                kind="object",
                contract_binding="missing.binding",
                labels={},
                domains=(),
                ranges=(),
                functional=False,
                deprecated=False,
                successor=None,
                quantity_kind=None,
                canonical_unit=None,
            )
        },
        semantic_matches={},
    )
    monkeypatch.setattr(
        "arxiv_int.ontology.check.load_ontology_catalog",
        lambda root=None: catalog,
    )
    monkeypatch.setattr("arxiv_int.ontology.check._parse_findings", lambda root: [])
    monkeypatch.setattr("arxiv_int.ontology.check.check_generation_drift", lambda root: [])
    monkeypatch.setattr("arxiv_int.ontology.check.check_ontology_evolution", lambda root: [])
    monkeypatch.setattr("arxiv_int.ontology.check._reasoner_findings", lambda root: [])
    report = check_ontology(ontology_root(), project_root=project_root())
    assert any("not in the canonical model" in item for item in report.findings)


def test_validate_and_shacl_edge_branches() -> None:
    catalog = load_ontology_catalog(ontology_root())
    findings = validate_assertions(
        catalog,
        [
            FactAssertion(
                "obj-1",
                ("unknown-type",),
                "pred.identified-by",
                literal_value="x",
                literal_datatype=None,
            )
        ],
    )
    assert findings
    graph = assertions_to_graph(
        [
            FactAssertion(
                "doc-1",
                ("https://arxiv-int.local/ns/class/Document",),
                "https://arxiv-int.local/ns/pred/mentions",
                object_id="obj-1",
                object_types=("https://arxiv-int.local/ns/class/Object",),
            )
        ],
        catalog=catalog,
    )
    ok, _ = run_shacl(graph, ontology_root=ontology_root())
    assert ok
    empty = OntologyCatalog("urn:x", "1.0.0", {}, {}, {})
    assert empty.active_predicates() == ()
    assert (
        OntologyClass(
            uri="u",
            term_id="class.x",
            status="active",
            labels={},
            parents=(),
            disjoint_with=(),
        ).term_id
        == "class.x"
    )


def test_status_helper_for_deprecated_without_ai_status() -> None:
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import OWL, RDF

    catalog = load_ontology_catalog(ontology_root())
    deprecated = catalog.predicate_by_term_id("pred.same-as")
    assert deprecated is not None and deprecated.deprecated
    graph = Graph()
    subject = URIRef("https://example.test/Term")
    graph.add((subject, RDF.type, OWL.Class))
    graph.add((subject, OWL.deprecated, Literal(True)))
    assert load_mod._status(graph, subject) == "deprecated"
