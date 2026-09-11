"""Validate gold classification labels against a frozen scheme and freeze evaluation splits.

Labels name a primary class (or a taxonomy code that resolves to its nearest scheme class, with
the truncation recorded) and optional alternates. Splits are deterministic per top-level stratum;
items sharing a content hash (or gold reference) form one group, so duplicates never leak across
splits.
"""

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from arxiv_int.classification.vocabulary.model import Scheme
from arxiv_int.classification.vocabulary.outcomes import EXCEPTIONAL_OUTCOMES
from arxiv_int.classification.vocabulary.policy import SchemePolicy

ITEM_KIND = "classification"
EVALUATION_CONTRACT_VERSION = "1.0.0"


class LabelError(ValueError):
    """Raised when a label file cannot be frozen as a leakage-free set."""


@dataclass(frozen=True, slots=True)
class GoldLabel:
    """One resolved gold label."""

    item_id: str
    gold_ref: str
    group_key: str
    primary: str
    alternates: tuple[str, ...]
    path: tuple[str, ...]
    stratum: str
    truncated_from: str | None
    split: str | None


def read_labels(path: Path) -> list[dict[str, Any]]:
    """Read one JSONL label file."""
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise LabelError(f"label line {number} is not a JSON object")
            records.append(record)
    return records


def _primary(record: Mapping[str, Any], scheme: Scheme) -> tuple[str, str | None]:
    class_id = record.get("primary")
    code = record.get("primary_code")
    if (class_id is None) == (code is None):
        raise LabelError("give exactly one of primary or primary_code")
    if isinstance(class_id, str):
        if class_id not in scheme.classes:
            raise LabelError(f"primary {class_id} is not in the scheme")
        return class_id, None
    resolution = scheme.resolve_code(str(code))
    if resolution is None:
        raise LabelError(f"primary_code {code} has no class in the scheme")
    return resolution.class_id, (str(code) if resolution.truncated else None)


def _alternates(record: Mapping[str, Any], scheme: Scheme, primary: str) -> tuple[str, ...]:
    values = record.get("alternates") or []
    if not isinstance(values, list) or len(set(values)) != len(values):
        raise LabelError("alternates must be a list of distinct class ids")
    for value in values:
        if value not in scheme.classes or value in EXCEPTIONAL_OUTCOMES or value == primary:
            raise LabelError(f"alternate {value} is unknown, exceptional, or the primary")
    if values and primary in EXCEPTIONAL_OUTCOMES:
        raise LabelError("an exceptional primary outcome takes no alternates")
    return tuple(str(value) for value in values)


def resolve_label(record: Mapping[str, Any], scheme: Scheme, policy: SchemePolicy) -> GoldLabel:
    """Resolve and validate one label record."""
    item_id, gold_ref = record.get("item_id"), record.get("gold_ref")
    if not isinstance(item_id, str) or not item_id or not isinstance(gold_ref, str) or not gold_ref:
        raise LabelError("item_id and gold_ref must be non-empty strings")
    primary, truncated_from = _primary(record, scheme)
    kind = scheme.classes[primary].kind
    if primary not in EXCEPTIONAL_OUTCOMES and kind not in policy.primary_kinds:
        raise LabelError(
            f"primary {primary} has kind {kind}; allowed: {sorted(policy.primary_kinds)}"
        )
    alternates = _alternates(record, scheme, primary)
    split = record.get("split")
    if split is not None and split not in dict(policy.split_fractions):
        raise LabelError(f"split {split} is not declared by the policy")
    path = scheme.path(primary)
    return GoldLabel(
        item_id=item_id,
        gold_ref=gold_ref,
        group_key=str(record.get("content_sha256") or gold_ref),
        primary=primary,
        alternates=alternates,
        path=path,
        stratum=path[0],
        truncated_from=truncated_from,
        split=None if split is None else str(split),
    )


def _group_split(labels: Sequence[GoldLabel]) -> str | None:
    declared = {label.split for label in labels if label.split is not None}
    if len(declared) > 1:
        raise LabelError(f"group {labels[0].group_key} is declared in splits {sorted(declared)}")
    return next(iter(declared), None)


def _seeded(seed: int, key: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()


def assign_splits(labels: Sequence[GoldLabel], policy: SchemePolicy) -> list[GoldLabel]:
    """Give every group one split, balancing undeclared groups within each stratum."""
    if len({label.item_id for label in labels}) != len(labels):
        raise LabelError("item ids must be unique")
    groups: dict[str, list[GoldLabel]] = defaultdict(list)
    for label in labels:
        groups[label.group_key].append(label)
    chosen = {key: _group_split(members) for key, members in groups.items()}
    strata: dict[str, list[str]] = defaultdict(list)
    for key, members in groups.items():
        if chosen[key] is None:
            strata[members[0].stratum].append(key)
    for keys in strata.values():
        ordered = sorted(keys, key=lambda item: _seeded(policy.evaluation_seed, item))
        for index, key in enumerate(ordered):
            chosen[key] = _split_at((index + 0.5) / len(ordered), policy)
    return [replace(label, split=chosen[label.group_key]) for label in labels]


def _split_at(position: float, policy: SchemePolicy) -> str:
    bound = 0.0
    for name, fraction in policy.split_fractions:
        bound += fraction
        if position < bound:
            return name
    return policy.split_fractions[-1][0]


def label_row(label: GoldLabel, scheme_id: str) -> dict[str, Any]:
    """Return the frozen label row; ``path``/``primary`` feed hierarchical scoring."""
    return {
        "alternates": list(label.alternates),
        "gold_ref": label.gold_ref,
        "group_key": label.group_key,
        "item_id": label.item_id,
        "path": list(label.path),
        "primary": label.primary,
        "scheme_id": scheme_id,
        "split": label.split,
        "stratum": label.stratum,
        "truncated_from": label.truncated_from,
    }


def evaluation_item_row(label: GoldLabel, label_set: str, run_id: str) -> dict[str, Any]:
    """Return one row shaped by the ``evaluation-items`` contract."""
    return {
        "contract_version": EVALUATION_CONTRACT_VERSION,
        "dataset_id": label_set,
        "evaluation_item_id": f"{label_set}:{label.item_id}",
        "generation_id": run_id,
        "gold_ref": label.gold_ref,
        "item_kind": ITEM_KIND,
        "label": label.primary,
        "query_text": None,
        "split": label.split,
    }


def split_ledger(labels: Sequence[GoldLabel], policy: SchemePolicy) -> dict[str, Any]:
    """Return counts per split and stratum plus the split policy that produced them."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for label in labels:
        counts[str(label.split)][label.stratum] += 1
    return {
        "counts": {split: dict(sorted(items.items())) for split, items in sorted(counts.items())},
        "exceptional": sum(label.primary in EXCEPTIONAL_OUTCOMES for label in labels),
        "fractions": dict(policy.split_fractions),
        "groups": len({label.group_key for label in labels}),
        "items": len(labels),
        "seed": policy.evaluation_seed,
        "truncated": sum(label.truncated_from is not None for label in labels),
    }
