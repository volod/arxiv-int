"""Citation resolution covers duplicates, anchors, renames, and refusals."""

import hashlib
from pathlib import Path

from arxiv_int.query.evidence.catalog import load_catalog
from arxiv_int.query.evidence.model import Citation, EvidenceAnchor, EvidenceCatalog
from arxiv_int.query.evidence.resolve import resolve_citation
from tests.query.evidence._builders import (
    cell_anchor,
    document,
    event,
    member_anchor,
    occurrence,
    save_catalog,
    sealed_paths,
    sha256_bytes,
    write_source,
)

_BYTES = b"invoice-bytes"


def _checksums(root: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            records[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return records


def test_duplicate_silos_and_nested_member_and_cell_anchors(tmp_path: Path) -> None:
    digest = sha256_bytes(_BYTES)
    zip_digest = sha256_bytes(b"zip-container")
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    mail = tmp_path / "mail"
    write_source(alpha, "docs/invoice.pdf", _BYTES)
    write_source(beta, "docs/invoice.pdf", _BYTES)
    write_source(mail, "mail/bundle.zip", b"zip-container")
    catalog = EvidenceCatalog(
        documents=(
            document("doc-dup", digest),
            document("doc-mail", zip_digest),
            document("doc-sheet", digest),
        ),
        occurrences=(
            occurrence("doc-dup", "alpha", "docs/invoice.pdf", digest),
            occurrence("doc-dup", "beta", "docs/invoice.pdf", digest),
            occurrence(
                "doc-mail",
                "mail",
                "mail/bundle.zip",
                zip_digest,
                container_path="mail/bundle.zip",
                member_path="attachments/invoice.pdf",
            ),
            occurrence("doc-sheet", "alpha", "docs/invoice.pdf", digest),
        ),
        citations=(
            Citation(
                kind="content",
                citation_id="cite-mail",
                document_id="doc-mail",
                original=member_anchor(),
                normalized=EvidenceAnchor(space="normalized", page=2, kind="page"),
            ),
            Citation(
                kind="content",
                citation_id="cite-sheet",
                document_id="doc-sheet",
                original=cell_anchor(),
            ),
            Citation(kind="fact", citation_id="fact-1", document_id="doc-dup", fact_id="fact-1"),
            Citation(
                kind="report",
                citation_id="rep-1",
                document_id="doc-mail",
                report_id="rep-1",
                original=member_anchor(),
            ),
        ),
    )
    roots = {"alpha": alpha, "beta": beta, "mail": mail}
    duplicated = resolve_citation(catalog, "doc-dup", silo_roots=roots)
    assert {item.silo_id for item in duplicated.locations} == {"alpha", "beta"}
    assert {item.current_path for item in duplicated.locations} == {"docs/invoice.pdf"}
    assert all(item.status == "matching" for item in duplicated.locations)
    member = resolve_citation(catalog, "doc-mail", silo_roots=roots)
    assert member.locations[0].member_path == "attachments/invoice.pdf"
    assert member.locations[0].current_path == "mail/bundle.zip"
    assert member.original_anchor is not None
    assert member.original_anchor.member_path == "attachments/invoice.pdf"
    assert member.normalized_anchor is not None
    assert member.normalized_anchor.space == "normalized"
    sheet = resolve_citation(catalog, "doc-sheet", silo_roots=roots)
    assert sheet.original_anchor is not None
    assert sheet.original_anchor.sheet == "Payments"
    assert sheet.original_anchor.cell_range == "B2:B2"
    fact = resolve_citation(catalog, "fact-1", kind="fact", silo_roots=roots)
    assert fact.document_id == "doc-dup"
    assert len(fact.locations) == 2
    report = resolve_citation(catalog, "rep-1", kind="report", silo_roots=roots)
    assert report.document_id == "doc-mail"
    assert report.locations[0].member_path == "attachments/invoice.pdf"


def test_path_only_rename_missing_changed_and_read_only_catalog(tmp_path: Path) -> None:
    digest = sha256_bytes(_BYTES)
    changed = sha256_bytes(b"changed")
    silo = tmp_path / "silo"
    write_source(silo, "current/renamed.pdf", _BYTES)
    write_source(silo, "docs/changed.pdf", b"changed")
    catalog_path, _ledger = sealed_paths(tmp_path / "results")
    catalog = EvidenceCatalog(
        documents=(
            document("doc-renamed", digest),
            document("doc-missing", digest),
            document("doc-changed", digest),
        ),
        occurrences=(
            occurrence("doc-renamed", "silo", "docs/original.pdf", digest),
            occurrence("doc-missing", "silo", "docs/gone.pdf", digest),
            occurrence("doc-changed", "silo", "docs/changed.pdf", digest),
        ),
        events=(
            event(
                "ev-rename",
                "doc-renamed",
                "silo",
                "rename",
                "current/renamed.pdf",
                digest,
                previous="docs/original.pdf",
            ),
        ),
    )
    save_catalog(catalog_path, catalog)
    before = _checksums(catalog_path.parent)
    loaded = load_catalog(catalog_path)
    roots = {"silo": silo}
    renamed = resolve_citation(loaded, "doc-renamed", silo_roots=roots)
    assert renamed.locations[0].original_path == "docs/original.pdf"
    assert renamed.locations[0].current_path == "current/renamed.pdf"
    assert renamed.locations[0].status == "matching"
    missing = resolve_citation(loaded, "doc-missing", silo_roots=roots)
    assert missing.locations[0].status == "missing"
    drifted = resolve_citation(loaded, "doc-changed", silo_roots=roots)
    assert drifted.locations[0].status == "changed"
    assert drifted.content_hash == digest
    assert drifted.locations[0].content_hash == digest
    assert _checksums(catalog_path.parent) == before
    assert silo.joinpath("current/renamed.pdf").read_bytes() == _BYTES
    assert changed == sha256_bytes((silo / "docs/changed.pdf").read_bytes())


def test_escaping_link_and_ambiguous_fact_locations(tmp_path: Path) -> None:
    digest = sha256_bytes(_BYTES)
    silo = tmp_path / "silo"
    silo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(_BYTES)
    (silo / "docs").mkdir()
    (silo / "docs" / "escape.pdf").symlink_to(outside)
    catalog = EvidenceCatalog(
        documents=(
            document("doc-escape", digest),
            document("doc-a", digest),
            document("doc-b", digest),
        ),
        occurrences=(occurrence("doc-escape", "silo", "docs/escape.pdf", digest),),
        citations=(
            Citation(kind="fact", citation_id="f-a", document_id="doc-a", fact_id="shared-fact"),
            Citation(kind="fact", citation_id="f-b", document_id="doc-b", fact_id="shared-fact"),
        ),
    )
    escaped = resolve_citation(catalog, "doc-escape", silo_roots={"silo": silo})
    assert escaped.locations[0].status == "escaped"
    assert escaped.content_hash == digest
    ambiguous = resolve_citation(catalog, "shared-fact", kind="fact")
    assert ambiguous.ambiguous is True
    assert "ambiguous source locations" in ambiguous.findings


def test_copy_event_adds_additional_current_location(tmp_path: Path) -> None:
    digest = sha256_bytes(_BYTES)
    silo = tmp_path / "silo"
    write_source(silo, "docs/original.pdf", _BYTES)
    write_source(silo, "classified/original.pdf", _BYTES)
    catalog = EvidenceCatalog(
        documents=(document("doc-copy", digest),),
        occurrences=(occurrence("doc-copy", "silo", "docs/original.pdf", digest),),
        events=(
            event(
                "ev-copy",
                "doc-copy",
                "silo",
                "copy",
                "classified/original.pdf",
                digest,
                previous="docs/original.pdf",
            ),
        ),
    )
    resolved = resolve_citation(catalog, "doc-copy", silo_roots={"silo": silo})
    roles = {item.role: item for item in resolved.locations}
    assert roles["source"].current_path == "docs/original.pdf"
    assert roles["copy"].current_path == "classified/original.pdf"
    assert all(item.status == "matching" for item in resolved.locations)
    assert resolved.ambiguous is False


def test_unknown_document_has_no_locations() -> None:
    catalog = EvidenceCatalog(documents=(), occurrences=())
    resolved = resolve_citation(catalog, "missing-doc")
    assert resolved.locations == ()
    assert resolved.document_id == "missing-doc"
    assert any("unknown document" in item for item in resolved.findings)
