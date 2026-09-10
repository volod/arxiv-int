import json
from pathlib import Path

import pytest

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.normalize.artifacts import validate_manifest
from arxiv_int.pipeline.normalize.text import load_offset_map
from tests.pipeline.chain import ChainRun, run_chain


@pytest.fixture(scope="module")
def chain(tmp_path_factory: pytest.TempPathFactory) -> ChainRun:
    return run_chain(tmp_path_factory.mktemp("normalize"))


def _summary(run: ChainRun) -> dict[str, object]:
    manifest = run.manifest(run.normalize)
    return json.loads(manifest.read_text(encoding="ascii"))


def test_stage_publishes_views_languages_and_quarantine(chain: ChainRun) -> None:
    summary = _summary(chain)

    assert chain.normalize.outcome == "produced"
    assert summary["normalized_documents"] == 7
    assert summary["quarantined"] == 1
    assert summary["languages"]["rus"] == 1
    assert chain.normalize.outputs[0].dataset == "normalized-documents"
    assert all(validation.publishable for validation in chain.normalize.validations)


def test_published_offset_maps_reproduce_the_original_slice(chain: ChainRun) -> None:
    summary = _summary(chain)
    root = Path(str(summary["roots"]["normalized-documents"]))
    extraction = Path(
        str(json.loads(chain.manifest(chain.extract).read_text("ascii"))["roots"]["documents"])
    )
    checked = 0
    for offsets_path in sorted((root / "offsets").glob("*.json")):
        payload = json.loads(offsets_path.read_text(encoding="ascii"))
        # Byte-exact reads: universal newlines would hide the carriage returns the
        # published offset map is built to address.
        canonical = (
            (root / "canonical" / f"{payload['normalized_document_id']}.txt").read_bytes()
        ).decode("utf-8")
        original = ((extraction / "text" / f"{payload['document_id']}.txt").read_bytes()).decode(
            "utf-8"
        )
        offsets = load_offset_map(payload["canonical_from_original"])
        for index in (0, len(canonical) // 2, max(len(canonical) - 1, 0)):
            assert 0 <= offsets.to_source(index) < max(len(original), 1)
        assert original[offsets.to_source(0) : offsets.to_source(len(canonical))].strip()
        checked += 1
    assert checked == 7


def test_quarantine_records_the_document_without_content(chain: ChainRun) -> None:
    summary = _summary(chain)
    quarantine = Path(str(summary["roots"]["quarantine"])) / "quarantine.jsonl"
    records = [json.loads(line) for line in quarantine.read_text(encoding="ascii").splitlines()]

    assert [item["reason"] for item in records] == ["empty-canonical-text"]
    assert "text" not in records[0]


def test_manifest_rejects_a_tampered_canonical_view(tmp_path: Path) -> None:
    disposable = run_chain(tmp_path, fixtures={"prose.txt": "Odin. Dva. Tri.\n"})
    manifest = disposable.manifest(disposable.normalize)
    summary = json.loads(manifest.read_text(encoding="ascii"))
    view = next((Path(str(summary["roots"]["normalized-documents"])) / "canonical").iterdir())
    view.write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum"):
        validate_manifest(manifest, hash_file(manifest)[0])
