"""Orchestrate ontology parse, binding, SHACL, and evolution gates."""

from dataclasses import dataclass
from pathlib import Path

from arxiv_int.contracts.catalog.canonical import load_canonical_model
from arxiv_int.ontology.evolution import check_ontology_evolution
from arxiv_int.ontology.generate import check_generation_drift, generate_ontology_bindings
from arxiv_int.ontology.load import load_ontology_catalog, load_ontology_graphs
from arxiv_int.ontology.paths import ontology_root_for, require_graph_dependencies
from arxiv_int.ontology.reason import disjointness_inconsistent
from arxiv_int.resources.paths import contracts_root
from arxiv_int.runtime.project_root import find_project_root


@dataclass(frozen=True)
class OntologyCheckReport:
    """Aggregated ontology gate findings."""

    findings: tuple[str, ...]
    checked_predicates: int
    checked_classes: int

    @property
    def ok(self) -> bool:
        return not self.findings


def _binding_findings(ontology_root: Path, project_root: Path) -> list[str]:
    catalog = load_ontology_catalog(ontology_root)
    canonical = load_canonical_model(contracts_root(project_root) / "canonical")
    findings: list[str] = []
    known_bindings = {field.binding for field in canonical.fields}
    for predicate in catalog.active_predicates():
        if not predicate.contract_binding:
            findings.append(f"{predicate.term_id}: missing contract binding")
            continue
        if predicate.contract_binding not in known_bindings:
            findings.append(
                f"{predicate.term_id}: contract binding "
                f"'{predicate.contract_binding}' is not in the canonical model"
            )
    return findings


def _parse_findings(ontology_root: Path) -> list[str]:
    findings: list[str] = []
    try:
        core, mappings, shapes = load_ontology_graphs(ontology_root)
    except Exception as error:
        return [f"ontology RDF parse failed: {error}"]
    if len(core) == 0:
        findings.append("ontology core graph is empty")
    if len(shapes) == 0:
        findings.append("ontology shapes graph is empty")
    if len(mappings) == 0:
        findings.append("ontology mappings graph is empty")
    return findings


def _reasoner_findings(ontology_root: Path) -> list[str]:
    natural = "https://arxiv-int.local/ns/class/NaturalPerson"
    legal = "https://arxiv-int.local/ns/class/LegalEntity"
    if not disjointness_inconsistent((natural, legal), ontology_root=ontology_root):
        return [
            "owlrl reasoner did not detect NaturalPerson/LegalEntity disjointness on one individual"
        ]
    if disjointness_inconsistent((natural,), ontology_root=ontology_root):
        return ["owlrl reasoner falsely flagged a single NaturalPerson type as inconsistent"]
    return []


def check_ontology(
    ontology_root: Path | None = None,
    *,
    project_root: Path | None = None,
    refresh_generated: bool = False,
) -> OntologyCheckReport:
    """Run ontology acceptance gates and return an aggregated report."""
    require_graph_dependencies()
    root = ontology_root if ontology_root is not None else ontology_root_for(project_root)
    resolved_project = find_project_root(project_root if project_root is not None else root.parent)
    findings: list[str] = []
    findings.extend(_parse_findings(root))
    if findings:
        return OntologyCheckReport(
            findings=tuple(findings), checked_predicates=0, checked_classes=0
        )
    catalog = load_ontology_catalog(root)
    if refresh_generated:
        generate_ontology_bindings(root)
    findings.extend(check_generation_drift(root))
    findings.extend(_binding_findings(root, resolved_project))
    findings.extend(check_ontology_evolution(root))
    findings.extend(_reasoner_findings(root))
    return OntologyCheckReport(
        findings=tuple(findings),
        checked_predicates=len(catalog.predicates),
        checked_classes=len(catalog.classes),
    )
