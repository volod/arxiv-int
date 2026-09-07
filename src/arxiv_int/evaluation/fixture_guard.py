"""Split-leakage, provenance, and replayable item-ledger checks."""

import hashlib
from collections.abc import Iterable, Mapping, Sequence

from arxiv_int.evaluation.bundle_layout import digest_bytes
from arxiv_int.evaluation.bundle_manifest import canonical_json
from arxiv_int.evaluation.eval_errors import FixtureCatalogError, SplitLeakError
from arxiv_int.evaluation.fixture_kinds import DEFAULT_BOOTSTRAP_SEED, SPLIT_FINAL, SPLIT_TUNING
from arxiv_int.evaluation.fixture_model import EvaluationItem, ItemLedger


def _content_key(item: EvaluationItem) -> str:
    payload = {
        "gold": dict(item.gold),
        "gold_ref": item.gold_ref,
        "item_kind": item.item_kind,
        "label": item.label,
        "query_text": item.query_text,
    }
    return digest_bytes(canonical_json(payload))


def require_provenance(items: Sequence[EvaluationItem]) -> None:
    """Refuse items that cannot name gold, dataset, and source evidence."""
    required = ("source", "evidence")
    seen: set[str] = set()
    for item in items:
        if item.item_id in seen:
            raise FixtureCatalogError(f"duplicate evaluation item_id {item.item_id!r}")
        seen.add(item.item_id)
        missing = [key for key in required if not item.provenance.get(key)]
        if missing or not item.gold_ref or not item.dataset_id:
            raise FixtureCatalogError(f"evaluation item {item.item_id} is missing provenance")


def detect_split_leakage(items: Sequence[EvaluationItem]) -> list[str]:
    """Return leakage findings when final items share identity or gold with tuning."""
    tuning = [item for item in items if item.split == SPLIT_TUNING]
    final = [item for item in items if item.split == SPLIT_FINAL]
    tuning_ids = {item.item_id for item in tuning}
    tuning_refs = {item.gold_ref for item in tuning}
    tuning_keys = {_content_key(item) for item in tuning}
    findings: list[str] = []
    for item in final:
        if item.item_id in tuning_ids:
            findings.append(f"item_id {item.item_id} appears in both splits")
        if item.gold_ref in tuning_refs:
            findings.append(f"gold_ref {item.gold_ref} leaks from tuning into final")
        if _content_key(item) in tuning_keys:
            findings.append(f"item {item.item_id} duplicates tuning gold content")
    return findings


def refuse_split_leakage(items: Sequence[EvaluationItem]) -> None:
    """Raise when the frozen set would mix tuning into final scoring."""
    findings = detect_split_leakage(items)
    if findings:
        raise SplitLeakError("; ".join(findings))


def item_ledger(
    items: Sequence[EvaluationItem], *, seed: int = DEFAULT_BOOTSTRAP_SEED
) -> ItemLedger:
    """Fingerprint a frozen item set for bootstrap replay."""
    require_provenance(items)
    refuse_split_leakage(items)
    ordered = tuple(sorted(items, key=lambda item: item.item_id))
    family_counts: dict[str, int] = {}
    rows: list[dict[str, object]] = []
    for item in ordered:
        family_counts[item.item_kind] = family_counts.get(item.item_kind, 0) + 1
        rows.append(
            {
                "gold": digest_bytes(canonical_json(dict(item.gold))),
                "gold_ref": item.gold_ref,
                "item_id": item.item_id,
                "item_kind": item.item_kind,
                "split": item.split,
            }
        )
    payload = {"items": rows, "seed": seed}
    return ItemLedger(
        fingerprint=digest_bytes(canonical_json(payload)),
        item_ids=tuple(item.item_id for item in ordered),
        family_counts=family_counts,
        seed=seed,
    )


def ledger_matches(first: ItemLedger, second: ItemLedger) -> bool:
    """Report whether two ledgers name the same frozen items and seed."""
    return first == second


def sha256_bytes(payload: bytes) -> str:
    """Return a SHA-256 hex digest of arbitrary bytes."""
    return hashlib.sha256(payload).hexdigest()


def mapping_fingerprint(values: Mapping[str, str]) -> str:
    """Fingerprint a string map used as an input identity."""
    return digest_bytes(canonical_json(dict(values)))


def collect_items(families: Iterable[Sequence[EvaluationItem]]) -> tuple[EvaluationItem, ...]:
    """Flatten family item lists in stable family-then-id order."""
    items = [item for family in families for item in family]
    return tuple(sorted(items, key=lambda item: (item.item_kind, item.item_id)))
