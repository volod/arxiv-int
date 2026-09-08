"""Registry of frozen evaluation families and committed catalog generation."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path

from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.evaluation.evaluate.errors import FixtureCatalogError
from arxiv_int.evaluation.evaluate.paths import fixture_root
from arxiv_int.evaluation.families.corpus import (
    classification_family,
    extraction_family,
    reporting_family,
)
from arxiv_int.evaluation.families.domain import (
    anomaly_family,
    domain_artifact_family,
    domain_negative_family,
)
from arxiv_int.evaluation.families.knowledge import (
    catalog_family,
    entity_family,
    fact_family,
)
from arxiv_int.evaluation.families.ontology import (
    geotemporal_family,
    graph_family,
    ontology_family,
)
from arxiv_int.evaluation.families.search import russian_retrieval_family, semantic_family
from arxiv_int.evaluation.fixtures.guard import collect_items, item_ledger
from arxiv_int.evaluation.fixtures.kinds import ITEM_KINDS, SCHEMA_VERSION
from arxiv_int.evaluation.fixtures.model import EvaluationItem, GoldFamily, family_from_payload

FAMILY_BUILDERS: Mapping[str, Callable[[], GoldFamily]] = {
    "anomaly": anomaly_family,
    "catalog": catalog_family,
    "classification": classification_family,
    "domain-artifact": domain_artifact_family,
    "domain-negative": domain_negative_family,
    "entity": entity_family,
    "extraction": extraction_family,
    "fact": fact_family,
    "geotemporal": geotemporal_family,
    "graph": graph_family,
    "ontology": ontology_family,
    "reporting": reporting_family,
    "russian-retrieval": russian_retrieval_family,
    "semantic": semantic_family,
}


def built_families() -> tuple[GoldFamily, ...]:
    """Return every frozen family in catalog order."""
    return tuple(FAMILY_BUILDERS[name]() for name in ITEM_KINDS)


def all_items(families: tuple[GoldFamily, ...] | None = None) -> tuple[EvaluationItem, ...]:
    """Flatten every frozen item."""
    selected = families if families is not None else built_families()
    return collect_items(family.items for family in selected)


def catalog_document(families: tuple[GoldFamily, ...] | None = None) -> dict[str, object]:
    """Return the committed catalog identity over all families."""
    selected = families if families is not None else built_families()
    items = all_items(selected)
    ledger = item_ledger(items)
    return {
        "families": [
            {"family": family.family, "item_count": len(family.items)} for family in selected
        ],
        "item_ids": list(ledger.item_ids),
        "ledger_fingerprint": ledger.fingerprint,
        "schema_version": SCHEMA_VERSION,
        "seed": ledger.seed,
    }


def family_bytes(family: GoldFamily) -> bytes:
    """Serialize one family with canonical JSON."""
    return canonical_json(family.as_json_dict())


def catalog_bytes(families: tuple[GoldFamily, ...] | None = None) -> bytes:
    """Serialize the catalog document."""
    return canonical_json(catalog_document(families))


def write_fixture_catalog(destination: Path) -> dict[str, Path]:
    """Write family JSON and the catalog ledger into ``destination``."""
    destination.mkdir(parents=True, exist_ok=True)
    families = built_families()
    written = {"index.json": destination / "index.json"}
    written["index.json"].write_bytes(catalog_bytes(families))
    for family in families:
        path = destination / f"{family.family}.json"
        path.write_bytes(family_bytes(family))
        written[f"{family.family}.json"] = path
    return written


def load_fixture_catalog(root: Path) -> tuple[GoldFamily, ...]:
    """Load committed family documents and require a matching catalog ledger."""
    families = []
    for name in ITEM_KINDS:
        path = root / f"{name}.json"
        if not path.is_file():
            raise FixtureCatalogError(f"missing fixture family {path}")
        payload = _load_json(path)
        families.append(family_from_payload(payload))
    loaded = tuple(families)
    catalog_path = root / "index.json"
    if not catalog_path.is_file():
        raise FixtureCatalogError("missing fixture index.json")
    on_disk = catalog_path.read_bytes()
    if on_disk != catalog_bytes(loaded):
        raise FixtureCatalogError("fixture catalog ledger does not match family files")
    item_ledger(all_items(loaded))
    return loaded


def fixture_drift(project_root: Path) -> list[str]:
    """Return drift findings when committed fixtures do not match generation."""
    root = fixture_root(project_root)
    findings: list[str] = []
    expected = write_expected_bytes()
    for name, payload in expected.items():
        path = root / name
        if not path.is_file():
            findings.append(f"missing {name}")
            continue
        if path.read_bytes() != payload:
            findings.append(f"drift in {name}")
    return findings


def write_expected_bytes() -> dict[str, bytes]:
    """Return the canonical bytes for every committed fixture file."""
    families = built_families()
    documents = {"index.json": catalog_bytes(families)}
    for family in families:
        documents[f"{family.family}.json"] = family_bytes(family)
    return documents


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FixtureCatalogError(f"cannot read fixture {path}") from error
    if not isinstance(payload, dict):
        raise FixtureCatalogError(f"fixture {path} is not an object")
    return payload
