"""Typed frozen evaluation items, gold sets, and item ledgers."""

from collections.abc import Mapping
from dataclasses import dataclass

from arxiv_int.evaluation.evaluate.errors import FixtureCatalogError
from arxiv_int.evaluation.fixtures.kinds import (
    FIXTURE_CONTRACT_VERSION,
    FIXTURE_DATASET_ID,
    FIXTURE_GENERATION_ID,
    ITEM_KINDS,
    SCHEMA_VERSION,
    SPLITS,
)


@dataclass(frozen=True, slots=True)
class EvaluationItem:
    """One frozen scoring item with gold, polarity examples, and provenance."""

    item_id: str
    item_kind: str
    split: str
    gold_ref: str
    dataset_id: str
    generation_id: str
    contract_version: str
    query_text: str | None
    label: str | None
    gold: Mapping[str, object]
    positive: Mapping[str, object]
    negative: Mapping[str, object]
    provenance: Mapping[str, str]

    def as_json_dict(self) -> dict[str, object]:
        """Return the canonical JSON object for one item."""
        return {
            "contract_version": self.contract_version,
            "dataset_id": self.dataset_id,
            "generation_id": self.generation_id,
            "gold": dict(self.gold),
            "gold_ref": self.gold_ref,
            "item_id": self.item_id,
            "item_kind": self.item_kind,
            "label": self.label,
            "negative": dict(self.negative),
            "positive": dict(self.positive),
            "provenance": dict(self.provenance),
            "query_text": self.query_text,
            "split": self.split,
        }


@dataclass(frozen=True, slots=True)
class GoldFamily:
    """One immutable family of evaluation items."""

    family: str
    schema_version: int
    items: tuple[EvaluationItem, ...]

    def as_json_dict(self) -> dict[str, object]:
        """Return the canonical family document."""
        return {
            "family": self.family,
            "items": [item.as_json_dict() for item in self.items],
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class ItemLedger:
    """Replayable identity of a frozen gold set."""

    fingerprint: str
    item_ids: tuple[str, ...]
    family_counts: Mapping[str, int]
    seed: int


def require_item_fields(payload: Mapping[str, object]) -> None:
    """Refuse a malformed item before it can enter a ledger."""
    item_id = payload.get("item_id")
    kind = payload.get("item_kind")
    split = payload.get("split")
    gold_ref = payload.get("gold_ref")
    if not isinstance(item_id, str) or not item_id:
        raise FixtureCatalogError("evaluation item is missing item_id")
    if kind not in ITEM_KINDS:
        raise FixtureCatalogError(f"unknown evaluation item_kind {kind!r} for {item_id}")
    if split not in SPLITS:
        raise FixtureCatalogError(f"unknown evaluation split {split!r} for {item_id}")
    if not isinstance(gold_ref, str) or not gold_ref:
        raise FixtureCatalogError(f"evaluation item {item_id} is missing gold_ref")


def item_from_payload(payload: Mapping[str, object]) -> EvaluationItem:
    """Parse one canonical item object."""
    require_item_fields(payload)
    gold = payload.get("gold")
    positive = payload.get("positive")
    negative = payload.get("negative")
    provenance = payload.get("provenance")
    if not isinstance(gold, dict) or not isinstance(positive, dict):
        raise FixtureCatalogError("evaluation item gold/positive must be objects")
    if not isinstance(negative, dict) or not isinstance(provenance, dict):
        raise FixtureCatalogError("evaluation item negative/provenance must be objects")
    query = payload.get("query_text")
    label = payload.get("label")
    if query is not None and not isinstance(query, str):
        raise FixtureCatalogError("query_text must be a string or null")
    if label is not None and not isinstance(label, str):
        raise FixtureCatalogError("label must be a string or null")
    return EvaluationItem(
        item_id=str(payload["item_id"]),
        item_kind=str(payload["item_kind"]),
        split=str(payload["split"]),
        gold_ref=str(payload["gold_ref"]),
        dataset_id=str(payload.get("dataset_id") or FIXTURE_DATASET_ID),
        generation_id=str(payload.get("generation_id") or FIXTURE_GENERATION_ID),
        contract_version=str(payload.get("contract_version") or FIXTURE_CONTRACT_VERSION),
        query_text=query,
        label=label,
        gold=gold,
        positive=positive,
        negative=negative,
        provenance={str(key): str(value) for key, value in provenance.items()},
    )


def family_from_payload(payload: Mapping[str, object]) -> GoldFamily:
    """Parse one canonical family document."""
    family = payload.get("family")
    version = payload.get("schema_version")
    items = payload.get("items")
    if family not in ITEM_KINDS:
        raise FixtureCatalogError(f"unknown evaluation family {family!r}")
    if version != SCHEMA_VERSION or not isinstance(items, list) or not items:
        raise FixtureCatalogError(f"evaluation family {family!r} is missing or malformed")
    parsed = tuple(item_from_payload(item) for item in items)
    kinds = {item.item_kind for item in parsed}
    if kinds != {family}:
        raise FixtureCatalogError(f"evaluation family {family} contains mixed item kinds")
    return GoldFamily(family, SCHEMA_VERSION, parsed)
