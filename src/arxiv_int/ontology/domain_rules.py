"""Domain investigation semantic rules beyond generic domain/range checks."""

from dataclasses import dataclass

from arxiv_int.ontology.catalog import OntologyCatalog
from arxiv_int.ontology.validate import FactAssertion, validate_assertions

_CREATION_STATUSES = frozenset({"produced", "partial", "empty", "failed"})
_SUPPLY_STAGES = frozenset({"quoted", "ordered", "invoiced", "shipped", "received", "paid"})
_MATCH_STATES = frozenset({"matched", "partial", "duplicate", "disputed", "unmatched", "candidate"})
_ANCHOR_KINDS = frozenset({"table", "cell", "container", "span"})
_DIRECTIONS = frozenset({"forward", "reverse", "undirected"})

_PART_OF = "pred.part-of"
_REFERENCES = "pred.references"
_OWNS_EXPLICIT = "pred.owns-explicit"
_OWNS_CANDIDATE = "pred.owns-candidate"
_ALLOCATES = "pred.allocates-to"
_SIMILAR = "pred.amount-date-similar-to"
_SAME_NAME = "pred.same-name-as"
_SHIPPED = "pred.shipped-as"


@dataclass(frozen=True)
class BomLine:
    """One BOM hierarchy row used for cycle and alternative checks."""

    line_id: str
    parent_id: str
    child_id: str
    predicate: str
    quantity: float | None = None
    unit: str | None = None
    alternative_group_id: str | None = None
    is_mandatory: bool = True


@dataclass(frozen=True)
class AllocationRow:
    """One invoice/payment allocation candidate or match."""

    row_id: str
    match_state: str
    invoice_currency: str
    payment_currency: str
    amount: float | None = None
    allocated_amount: float | None = None
    predicate: str = _ALLOCATES


@dataclass(frozen=True)
class ArtifactRegistryRow:
    """One domain artifact registry creation record."""

    artifact_id: str
    artifact_type: str
    creation_status: str
    failure_reason: str | None = None


def _pred_key(value: str) -> str:
    if value.startswith("pred."):
        return value
    item_term = value.rsplit("/", 1)[-1]
    # camelCase local name to kebab term id
    chars: list[str] = []
    for index, char in enumerate(item_term):
        if char.isupper() and index:
            chars.append("-")
            chars.append(char.lower())
        else:
            chars.append(char.lower())
    return f"pred.{''.join(chars)}"


def _pair_keys(assertions: tuple[FactAssertion, ...], predicate: str) -> set[tuple[str, str]]:
    wanted = _pred_key(predicate)
    pairs: set[tuple[str, str]] = set()
    for item in assertions:
        if _pred_key(item.predicate) != wanted or item.object_id is None:
            continue
        pairs.add((item.subject_id, item.object_id))
    return pairs


def _conflicting_pair_findings(
    assertions: tuple[FactAssertion, ...],
    left: str,
    right: str,
    message: str,
) -> list[str]:
    overlap = _pair_keys(assertions, left) & _pair_keys(assertions, right)
    return [f"{subject}->{obj}: {message}" for subject, obj in sorted(overlap)]


def detect_bom_cycles(lines: tuple[BomLine, ...] | list[BomLine]) -> list[str]:
    """Return findings when part-of edges form a cycle."""
    edges = [
        (line.parent_id, line.child_id) for line in lines if _pred_key(line.predicate) == _PART_OF
    ]
    graph: dict[str, set[str]] = {}
    for parent, child in edges:
        graph.setdefault(child, set()).add(parent)
        graph.setdefault(parent, set())
    findings: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(node: str, stack: list[str]) -> None:
        if node in visiting:
            cycle = " -> ".join([*stack[stack.index(node) :], node])
            findings.append(f"BOM cycle detected: {cycle}")
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph.get(node, ()):
            walk(nxt, [*stack, node])
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        walk(node, [])
    return findings


def alternative_quantity_findings(lines: tuple[BomLine, ...] | list[BomLine]) -> list[str]:
    """Refuse summing mandatory alternatives in one alternative group."""
    grouped: dict[str, list[BomLine]] = {}
    for line in lines:
        if not line.alternative_group_id:
            continue
        grouped.setdefault(line.alternative_group_id, []).append(line)
    findings: list[str] = []
    for group_id, members in sorted(grouped.items()):
        mandatory = [item for item in members if item.is_mandatory]
        if len(mandatory) > 1 and all(item.quantity is not None for item in mandatory):
            findings.append(
                f"alternative group '{group_id}' treats multiple alternatives as mandatory "
                "quantities; alternatives must not be summed"
            )
    return findings


def allocation_findings(rows: tuple[AllocationRow, ...] | list[AllocationRow]) -> list[str]:
    """Separate similarity from settlement and enforce currency/amount rules."""
    findings: list[str] = []
    for row in rows:
        if row.match_state not in _MATCH_STATES:
            findings.append(f"{row.row_id}: unknown match_state '{row.match_state}'")
        if _pred_key(row.predicate) == _SIMILAR and row.match_state == "matched":
            findings.append(
                f"{row.row_id}: amount/date similarity cannot produce matched settlement"
            )
        if _pred_key(row.predicate) == _ALLOCATES and row.invoice_currency != row.payment_currency:
            findings.append(
                f"{row.row_id}: allocation currencies differ "
                f"({row.payment_currency} vs {row.invoice_currency})"
            )
        if (
            row.allocated_amount is not None
            and row.amount is not None
            and row.allocated_amount > row.amount
        ):
            findings.append(f"{row.row_id}: allocated_amount exceeds applicable amount")
    return findings


def registry_findings(
    rows: tuple[ArtifactRegistryRow, ...] | list[ArtifactRegistryRow],
) -> list[str]:
    """Validate creation statuses and failed/empty semantics."""
    findings: list[str] = []
    for row in rows:
        if row.creation_status not in _CREATION_STATUSES:
            findings.append(f"{row.artifact_id}: unknown creation_status '{row.creation_status}'")
        if row.creation_status == "failed" and not row.failure_reason:
            findings.append(f"{row.artifact_id}: failed status requires failure_reason")
        if row.creation_status == "empty" and row.failure_reason:
            findings.append(
                f"{row.artifact_id}: empty is a valid negative result and must not carry "
                "failure_reason"
            )
    return findings


def supply_stage_findings(stage: str, *, claims_delivery: bool) -> list[str]:
    """Invoice/order stages do not prove delivery."""
    findings: list[str] = []
    if stage not in _SUPPLY_STAGES:
        findings.append(f"unknown supply stage '{stage}'")
    if stage in {"quoted", "ordered", "invoiced"} and claims_delivery:
        findings.append(
            f"stage '{stage}' cannot claim delivery; use shipped or received with evidence"
        )
    return findings


def validate_domain_assertions(
    catalog: OntologyCatalog,
    assertions: tuple[FactAssertion, ...] | list[FactAssertion],
    *,
    bom_lines: tuple[BomLine, ...] | list[BomLine] = (),
    allocations: tuple[AllocationRow, ...] | list[AllocationRow] = (),
    registry_rows: tuple[ArtifactRegistryRow, ...] | list[ArtifactRegistryRow] = (),
    allow_deprecated: bool = False,
) -> list[str]:
    """Run foundation ontology checks plus domain investigation distinctions."""
    items = tuple(assertions)
    findings = validate_assertions(catalog, items, allow_deprecated=allow_deprecated)
    findings.extend(
        _conflicting_pair_findings(items, _PART_OF, _REFERENCES, "references is not part-of")
    )
    findings.extend(
        _conflicting_pair_findings(
            items, _OWNS_EXPLICIT, _OWNS_CANDIDATE, "candidate ownership is not explicit"
        )
    )
    findings.extend(
        _conflicting_pair_findings(
            items, _ALLOCATES, _SIMILAR, "amount/date similarity is not payment allocation"
        )
    )
    findings.extend(
        _conflicting_pair_findings(
            items,
            _SAME_NAME,
            "pred.alias-of",
            "same-name association is not identity",
        )
    )
    findings.extend(detect_bom_cycles(bom_lines))
    findings.extend(alternative_quantity_findings(bom_lines))
    findings.extend(allocation_findings(allocations))
    findings.extend(registry_findings(registry_rows))
    return findings


def validate_anchor_kind(anchor_kind: str) -> list[str]:
    if anchor_kind in _ANCHOR_KINDS:
        return []
    return [f"unknown anchor_kind '{anchor_kind}'"]


def validate_direction(direction: str) -> list[str]:
    if direction in _DIRECTIONS:
        return []
    return [f"unknown direction '{direction}'"]
