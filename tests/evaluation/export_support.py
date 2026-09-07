from pathlib import Path

from arxiv_int.evaluation.bundle_manifest import canonical_json
from arxiv_int.evaluation.bundles import publish_run_bundle
from arxiv_int.evaluation.exporter import ExportMapping, ExportRequest, export_proof_bundle
from tests.evaluation.bundle_support import spec


def excerpt_text() -> str:
    return (
        "Alice Example joined Acme Example LLC to sell Pump-100.\n"
        "Later Alice Example reviewed the same Pump-100.\n"
        "Pay 100 kg on 2020-01-01 at 55.75,37.62 using +7 (495) 123-45-67.\n"
        "Email alice.example@acme.example about Example Street 12, Exampleville, 125009.\n"
    )


def excerpt_spans() -> list[dict[str, object]]:
    text = excerpt_text()
    first = "Alice Example"
    second_start = text.index(first, len(first))
    return [
        {"artifact": "excerpt.txt", "end": len(first), "entity_id": "person:alpha", "start": 0},
        {
            "artifact": "excerpt.txt",
            "end": second_start + len(first),
            "entity_id": "person:beta",
            "start": second_start,
        },
    ]


def identities_payload() -> dict[str, object]:
    return {
        "entities": [
            {
                "aliases": ["A. Example"],
                "id": "person:alpha",
                "kind": "person",
                "labels": ["Alice Example"],
            },
            {"id": "person:beta", "kind": "person", "labels": ["Alice Example"]},
            {
                "aliases": ["Acme Example"],
                "id": "company:acme",
                "kind": "company",
                "labels": ["Acme Example LLC"],
            },
            {"id": "product:pump", "kind": "product", "labels": ["Pump-100"]},
        ],
        "fields": [
            {"kind": "email", "value": "alice.example@acme.example"},
            {"kind": "phone", "prefix": "+7", "value": "+7 (495) 123-45-67"},
            {
                "city": "Exampleville",
                "house": "12",
                "kind": "address",
                "postal": "125009",
                "street": "Example Street",
                "value": "Example Street 12, Exampleville, 125009",
            },
            {"kind": "account", "scheme": "luhn", "value": "4532015112830366"},
            {"kind": "account", "scheme": "iban", "value": "DE89370400440532013000"},
            {"kind": "account", "scheme": "inn10", "value": "0123456789"},
        ],
        "schema_version": 1,
        "spans": excerpt_spans(),
    }


def items_payload() -> dict[str, object]:
    return {
        "answer": "Alice Example sold 100 kg of Pump-100 in Exampleville on 2020-01-01 at 55.75,37.62",
        "entity_id": "person:alpha",
        "label": "Acme Example LLC",
        "query_text": "Where did Alice Example work?",
        "start": 0,
        "end": 13,
        "artifact": "excerpt.txt",
    }


def graph_payload() -> dict[str, object]:
    return {
        "edges": [{"from": "person:alpha", "rel": "works_at", "to": "company:acme"}],
        "nodes": [
            {"id": "person:alpha", "label": "Alice Example"},
            {"id": "person:beta", "label": "Alice Example"},
            {"id": "company:acme", "label": "Acme Example LLC"},
        ],
    }


def publish_identity_bundle(directory: Path) -> Path:
    identities = canonical_json(identities_payload()).decode("utf-8")
    publish_run_bundle(
        directory,
        spec(),
        [{"item_id": "Alice Example", "score": 1.0, "entity_id": "person:alpha"}],
        artifacts={
            "excerpt.txt": excerpt_text(),
            "items.json": canonical_json(items_payload()).decode("utf-8"),
            "graph.json": canonical_json(graph_payload()).decode("utf-8"),
            "identities.json": identities,
            "local-only.txt": "Alice Example stays local.\n",
        },
    )
    return directory


def export_bundle(source: Path, dest_root: Path, project_root: Path, run_id: str = "export-1"):
    mappings = (
        ExportMapping("excerpt.txt", Path("excerpt.txt")),
        ExportMapping("items.json", Path("items.json")),
        ExportMapping("graph.json", Path("graph.json")),
        ExportMapping("scores.jsonl", Path("scores.jsonl")),
        ExportMapping("manifest.json", Path("manifest.json")),
    )
    return export_proof_bundle(
        ExportRequest(
            source_bundle=source,
            mappings=mappings,
            run_id=run_id,
            project_root=project_root,
            destination_root=dest_root,
        )
    )
