import json
from pathlib import Path

import pytest

from arxiv_int.evaluation.bundle_manifest import canonical_json
from arxiv_int.evaluation.bundles import publish_run_bundle
from arxiv_int.evaluation.export_policy import DATA_CLASS_TRANSFORMED
from arxiv_int.evaluation.exporter import ExportMapping, ExportRequest, export_proof_bundle
from arxiv_int.evaluation.families import all_items
from arxiv_int.evaluation.geo_eval import score_geotemporal
from arxiv_int.evaluation.scoring import polarity_scores, score_item
from tests.evaluation.bundle_support import spec
from tests.evaluation.export_support import identities_payload


def test_export_rewrites_labels_and_answers_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    items = {
        "answer": "Fixture Person Alpha works at Fixture Company LLC",
        "label": "Fixture Person Alpha",
        "query_text": "Where does Fixture Person Alpha work?",
        "source_valid_start": "2019-01-01",
        "recorded_time": "2021-06-01",
        "valid": False,
        "implication": "identity",
    }
    identities = {
        "schema_version": 1,
        "entities": [
            {
                "id": "person:alpha",
                "kind": "person",
                "labels": ["Fixture Person Alpha"],
                "aliases": [],
            },
            {
                "id": "company:acme",
                "kind": "company",
                "labels": ["Fixture Company LLC"],
                "aliases": [],
            },
        ],
        "fields": [],
        "spans": [],
    }
    source = tmp_path / "bundle"
    publish_run_bundle(
        source,
        spec(),
        [{"item_id": "catalog-person-final", "score": 1.0}],
        artifacts={
            "items.json": canonical_json(items).decode("utf-8"),
            "identities.json": canonical_json(identities).decode("utf-8"),
        },
    )
    dest = tmp_path / "export"
    published = export_proof_bundle(
        ExportRequest(
            source_bundle=source,
            mappings=(
                ExportMapping("items.json", Path("items.json")),
                ExportMapping("manifest.json", Path("manifest.json")),
            ),
            run_id="fixture-export",
            project_root=tmp_path / "proj",
            destination_root=dest,
        )
    )
    rewritten = json.loads((dest / "items.json").read_text(encoding="utf-8"))
    assert "Fixture Person Alpha" not in json.dumps(rewritten)
    assert "Fixture Company LLC" not in json.dumps(rewritten)
    assert rewritten["source_valid_start"] == "2019-01-01"
    assert rewritten["recorded_time"] == "2021-06-01"
    assert rewritten["valid"] is False
    assert rewritten["implication"] == "identity"
    assert rewritten["label"] in rewritten["answer"]
    assert rewritten["label"] in rewritten["query_text"]
    geo = score_geotemporal(
        {
            "source_valid_start": rewritten["source_valid_start"],
            "recorded_time": rewritten["recorded_time"],
        },
        {
            "source_valid_start": rewritten["source_valid_start"],
            "recorded_time": rewritten["recorded_time"],
        },
    )
    assert geo["source_recorded_distinct"] == 1.0
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["data_class"] == DATA_CLASS_TRANSFORMED
    assert published.export_fingerprint
    domain = [item for item in all_items() if item.item_kind == "domain-negative"]
    for item in domain:
        assert item.gold["valid"] is False
        assert polarity_scores(item)[0] > polarity_scores(item)[1]


def test_identity_catalog_from_support_still_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    assert identities_payload()["schema_version"] == 1
    item = next(row for row in all_items() if row.item_id == "geo-unknown-crs-final")
    negative = score_item(item, item.negative)
    assert negative["unknown_crs_kept"] == 0.0
