"""Source coverage and structural balance gates for the compiled taxonomy.

Coverage: every item of every source snapshot maps to exactly one class, and every crosswalk id
names a known source item. Balance: taxonomy leaves sit at one depth, every parent has a bounded
number of children, and no domain holds more than the configured share of leaves.
"""

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from arxiv_int.classification.vocabulary.model import Scheme, SchemeClass
from arxiv_int.classification.vocabulary.outcomes import NAMESPACE_TAXONOMY
from arxiv_int.classification.vocabulary.policy import BalancePolicy, SourceSnapshot
from arxiv_int.classification.vocabulary.validate import Finding, error

SHARE_DIGITS = 4


def _owners(classes: Sequence[SchemeClass]) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = defaultdict(list)
    for item in classes:
        for reference in item.crosswalk:
            owners[reference].append(item.class_id)
    return owners


def _source_findings(source: SourceSnapshot, owners: Mapping[str, list[str]]) -> list[Finding]:
    found = [
        error("coverage-missing", None, f"{source.source_id} item {ref} maps to no class")
        for ref in sorted(set(source.items) - set(owners))
    ]
    found.extend(
        error("coverage-duplicate", owners[ref][0], f"{ref} maps to {len(owners[ref])} classes")
        for ref in sorted(set(source.items))
        if len(owners.get(ref, ())) > 1
    )
    return found


def coverage(
    classes: Sequence[SchemeClass], sources: Sequence[SourceSnapshot]
) -> tuple[list[Finding], list[dict[str, Any]]]:
    """Return coverage findings and per-source mapped counts."""
    owners = _owners(classes)
    found: list[Finding] = []
    stats: list[dict[str, Any]] = []
    for source in sources:
        found.extend(_source_findings(source, owners))
        items = set(source.items)
        mapped = len(items & set(owners))
        stats.append({"items": len(items), "mapped": mapped, "sourceId": source.source_id})
    known = {ref for source in sources for ref in source.items}
    found.extend(
        error("crosswalk-unknown", owner[0], f"{ref} is in no source snapshot")
        for ref, owner in sorted(owners.items())
        if ref not in known
    )
    return found, stats


def _depth_findings(scheme: Scheme, leaves: Sequence[SchemeClass], depth: int) -> list[Finding]:
    return [
        error("unbalanced-depth", leaf.class_id, f"leaf at depth {scheme.depth(leaf.class_id)}")
        for leaf in leaves
        if scheme.depth(leaf.class_id) != depth
    ]


def _fan_out_findings(fan_out: Mapping[str | None, int], policy: BalancePolicy) -> list[Finding]:
    return [
        error("unbalanced-branching", parent, f"{count} children")
        for parent, count in sorted(fan_out.items(), key=lambda pair: str(pair[0]))
        if not policy.min_children <= count <= policy.max_children
    ]


def _share_findings(
    shares: Mapping[str, float], per_domain: Mapping[str, int], limit: float
) -> list[Finding]:
    total = sum(per_domain.values())
    return [
        error("unbalanced-domain", domain, f"{per_domain[domain]}/{total} leaves")
        for domain, share in sorted(shares.items())
        if share > limit
    ]


def balance(scheme: Scheme, policy: BalancePolicy) -> tuple[list[Finding], dict[str, Any]]:
    """Return balance findings and the structure statistics recorded in the manifest."""
    taxonomy = [item for item in scheme.classes.values() if item.namespace == NAMESPACE_TAXONOMY]
    fan_out: dict[str | None, int] = dict(Counter(item.parent_id for item in taxonomy))
    leaves = [item for item in taxonomy if item.class_id not in fan_out]
    per_domain = Counter(scheme.path(leaf.class_id)[0] for leaf in leaves)
    total = len(leaves)
    shares = {domain: count / total for domain, count in per_domain.items()} if total else {}
    found = [
        *_depth_findings(scheme, leaves, policy.leaf_depth),
        *_fan_out_findings(fan_out, policy),
        *_share_findings(shares, per_domain, policy.max_domain_leaf_share),
    ]
    depth = Counter(scheme.depth(item.class_id) for item in taxonomy)
    stats = {
        "classesPerDepth": {str(level): count for level, count in sorted(depth.items())},
        "fanOutMax": max(fan_out.values(), default=0),
        "fanOutMin": min(fan_out.values(), default=0),
        "leafDepth": policy.leaf_depth,
        "leaves": total,
        "leavesPerDomain": dict(sorted(per_domain.items())),
        "maxDomainLeafShare": round(max(shares.values(), default=0.0), SHARE_DIGITS),
    }
    return found, stats
