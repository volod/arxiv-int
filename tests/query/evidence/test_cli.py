"""CLI locate and import-ledger stay read-only for sources and catalogs."""

import json
from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.query.evidence.model import EvidenceCatalog
from tests.query.evidence._builders import (
    document,
    event,
    occurrence,
    save_catalog,
    save_ledger,
    sealed_paths,
    sha256_bytes,
    write_source,
)

_BYTES = b"cli-bytes"


def test_cli_help_lists_archive_locate_and_import_ledger() -> None:
    parser = build_parser()
    text = parser.format_help()
    assert "archive" in text
    locate = parser.parse_args(["archive", "locate", "doc-1", "--json", "--kind", "fact"])
    assert locate.token == "doc-1"
    assert locate.kind == "fact"
    imported = parser.parse_args(["archive", "import-ledger", "ledger.json"])
    assert imported.archive_command == "import-ledger"


def test_locate_cli_json_and_import_without_runtime(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "arxiv_int.query.evidence.commands._load_runtime",
        _refuse_runtime,
    )
    digest = sha256_bytes(_BYTES)
    silo = tmp_path / "alpha"
    write_source(silo, "docs/note.txt", _BYTES)
    catalog_path, ledger_path = sealed_paths(tmp_path / "results")
    save_catalog(
        catalog_path,
        EvidenceCatalog(
            documents=(document("doc-1", digest),),
            occurrences=(occurrence("alpha", "docs/note.txt", digest),),
        ),
    )
    code = main(
        [
            "archive",
            "locate",
            "doc-1",
            "--catalog",
            str(catalog_path),
            "--ledger",
            str(ledger_path),
            "--silo",
            f"alpha={silo}",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "arxiv-int.evidence-resolution.v1"
    assert payload["document_id"] == "doc-1"
    assert payload["locations"][0]["status"] == "matching"
    assert "/home/" not in json.dumps(payload)
    incoming = tmp_path / "incoming.json"
    save_ledger(incoming, (event("ev-cli", "doc-1", "alpha", "initial", "docs/note.txt", digest),))
    imported = main(
        [
            "archive",
            "import-ledger",
            str(incoming),
            "--ledger",
            str(ledger_path),
            "--json",
        ]
    )
    assert imported == 0
    report = json.loads(capsys.readouterr().out)
    assert report["inserted"] == 1
    assert report["skipped"] == 0


def test_locate_unknown_document_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog_path, ledger_path = sealed_paths(tmp_path)
    save_catalog(catalog_path, EvidenceCatalog(documents=(), occurrences=()))
    code = main(
        [
            "archive",
            "locate",
            "missing",
            "--catalog",
            str(catalog_path),
            "--ledger",
            str(ledger_path),
            "--json",
        ]
    )
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["locations"] == []


def _refuse_runtime(*_args: object, **_kwargs: object) -> object:
    raise RuntimeError("runtime config must not load when catalog and ledger are explicit")
