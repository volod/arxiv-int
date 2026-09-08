import json
import logging
from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.evaluation.export.errors import (
    ExportLeakError,
    ExportPathError,
    ExportUnsupportedError,
)
from arxiv_int.evaluation.export.exporter import ExportMapping, ExportRequest, export_proof_bundle
from arxiv_int.evaluation.export.render import iban_valid, luhn_valid
from tests.evaluation.export.export_support import (
    excerpt_text,
    export_bundle,
    identities_payload,
    publish_identity_bundle,
)


def test_repeated_exports_from_different_roots_and_orderings_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data-a"))
    source_a = publish_identity_bundle(tmp_path / "src-a" / "bundle")
    dest_a = tmp_path / "out-a"
    first = export_bundle(source_a, dest_a, tmp_path / "proj-a", run_id="run-a")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data-b"))
    source_b = publish_identity_bundle(tmp_path / "src-b" / "bundle")
    dest_b = tmp_path / "out-b"
    reversed_maps = (
        ExportMapping("manifest.json", Path("manifest.json")),
        ExportMapping("scores.jsonl", Path("scores.jsonl")),
        ExportMapping("graph.json", Path("graph.json")),
        ExportMapping("items.json", Path("items.json")),
        ExportMapping("excerpt.txt", Path("excerpt.txt")),
    )
    second = export_proof_bundle(
        ExportRequest(
            source_bundle=source_b,
            mappings=reversed_maps,
            run_id="run-b",
            project_root=tmp_path / "proj-b",
            destination_root=dest_b,
        )
    )
    assert first.export_fingerprint == second.export_fingerprint
    assert first.source_fingerprint == second.source_fingerprint
    for name in ("excerpt.txt", "items.json", "graph.json", "scores.jsonl", "manifest.json"):
        assert (dest_a / name).read_bytes() == (dest_b / name).read_bytes()


def test_export_preserves_joins_formats_and_geotemporal_meaning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    source = publish_identity_bundle(tmp_path / "bundle")
    dest = tmp_path / "out"
    published = export_bundle(source, dest, tmp_path, run_id="formats")
    excerpt = (dest / "excerpt.txt").read_text(encoding="utf-8")
    items = json.loads((dest / "items.json").read_text(encoding="utf-8"))
    graph = json.loads((dest / "graph.json").read_text(encoding="utf-8"))
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    scores = (dest / "scores.jsonl").read_text(encoding="utf-8")
    assert "Alice Example" not in excerpt
    assert "Acme Example" not in excerpt
    assert "alice.example@acme.example" not in excerpt
    assert "100 kg" in excerpt
    assert "2020-01-01" in excerpt
    assert "55.75,37.62" in excerpt
    assert "@example.invalid" in excerpt
    assert items["answer"].count("100 kg") == 1
    assert "2020-01-01" in items["answer"]
    assert graph["edges"][0]["from"] == graph["nodes"][0]["id"]
    assert graph["edges"][0]["to"] == graph["nodes"][2]["id"]
    assert graph["nodes"][0]["label"] != graph["nodes"][1]["label"]
    assert manifest["configuration"]["identity_transform"]["data_class"] == "transformed"
    assert manifest["data_class"] == "transformed"
    assert "raw-archive" not in json.dumps(manifest)
    assert "Alice Example" not in scores
    map_path = published.diagnostics / "identity-map.json"
    mapping = json.loads(map_path.read_text(encoding="utf-8"))
    luhn = mapping["substitutions"]["fields"]["4532015112830366"]
    iban = mapping["substitutions"]["fields"]["DE89370400440532013000"]
    assert luhn_valid(luhn)
    assert iban_valid(iban)
    assert published.diagnostics.as_posix().endswith("/proof-export/formats")


def test_original_bundle_and_local_only_artifacts_stay_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    source = publish_identity_bundle(tmp_path / "bundle")
    before = {path.name: path.read_bytes() for path in source.iterdir() if path.is_file()}
    local = (source / "local-only.txt").read_bytes()
    dest = tmp_path / "out"
    export_bundle(source, dest, tmp_path, run_id="preserve")
    after = {path.name: path.read_bytes() for path in source.iterdir() if path.is_file()}
    assert before == after
    assert (source / "local-only.txt").read_bytes() == local
    assert not (dest / "local-only.txt").exists()
    assert excerpt_text() == (source / "excerpt.txt").read_text(encoding="utf-8")


def test_residual_identities_and_identity_catalog_export_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    source = publish_identity_bundle(tmp_path / "bundle")
    with pytest.raises(ExportPathError, match="raw identity artifact"):
        export_proof_bundle(
            ExportRequest(
                source_bundle=source,
                mappings=(ExportMapping("identities.json", Path("identities.json")),),
                run_id="leak",
                project_root=tmp_path,
                destination_root=tmp_path / "out",
            )
        )
    dest = tmp_path / "out"
    export_bundle(source, dest, tmp_path, run_id="ok")
    leaked = dest / "excerpt.txt"
    leaked.write_text(leaked.read_text(encoding="utf-8") + "Alice Example\n", encoding="utf-8")
    from arxiv_int.evaluation.export.catalog import parse_identity_catalog
    from arxiv_int.evaluation.export.checks import refuse_leaks
    from arxiv_int.evaluation.export.map import build_substitution_table

    table = build_substitution_table(
        parse_identity_catalog(identities_payload()), {"excerpt.txt": excerpt_text()}
    )
    with pytest.raises(ExportLeakError, match="source identity"):
        refuse_leaks(leaked.read_bytes(), table.needles)


def test_empty_catalog_copies_text_without_identity_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arxiv_int.evaluation.bundles import publish_run_bundle
    from tests.evaluation.bundles.bundle_support import spec

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    source = tmp_path / "bundle"
    publish_run_bundle(source, spec(), [], artifacts={"note.txt": "no identities here\n"})
    dest = tmp_path / "out"
    export_proof_bundle(
        ExportRequest(
            source_bundle=source,
            mappings=(ExportMapping("note.txt", Path("note.txt")),),
            run_id="empty",
            project_root=tmp_path,
            destination_root=dest,
        )
    )
    assert (dest / "note.txt").read_text(encoding="utf-8") == "no identities here\n"


def test_unsupported_binary_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from arxiv_int.evaluation.bundles import publish_run_bundle
    from tests.evaluation.bundles.bundle_support import spec

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    source = tmp_path / "bundle"
    publish_run_bundle(
        source,
        spec(),
        [],
        artifacts={"shot.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 16},
    )
    with pytest.raises(ExportUnsupportedError, match="unsupported export format"):
        export_proof_bundle(
            ExportRequest(
                source_bundle=source,
                mappings=(ExportMapping("shot.png", Path("shot.png")),),
                run_id="png",
                project_root=tmp_path,
                destination_root=tmp_path / "out",
            )
        )


def test_destination_inside_source_bundle_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    source = publish_identity_bundle(tmp_path / "bundle")
    with pytest.raises(ExportPathError, match="inside the source bundle"):
        export_proof_bundle(
            ExportRequest(
                source_bundle=source,
                mappings=(ExportMapping("excerpt.txt", source / "excerpt.txt"),),
                run_id="mutate",
                project_root=tmp_path,
            )
        )


def test_cli_export_and_policy_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    source = publish_identity_bundle(tmp_path / "bundle")
    dest = tmp_path / "git-out"
    parser = build_parser()
    args = parser.parse_args(
        [
            "evaluation",
            "export-proof",
            "--source-bundle",
            str(source),
            "--map",
            "excerpt.txt=excerpt.txt",
            "--run-id",
            "cli",
            "--destination-root",
            str(dest),
        ]
    )
    assert args.evaluation_command == "export-proof"
    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    caplog.set_level(logging.INFO)
    assert (
        main(
            [
                "evaluation",
                "export-proof",
                "--source-bundle",
                str(source),
                "--map",
                "excerpt.txt=excerpt.txt",
                "--run-id",
                "cli",
                "--destination-root",
                str(dest),
            ]
        )
        == 0
    )
    assert "exported 1 proof artifact" in caplog.text
    assert (dest / "excerpt.txt").is_file()
    generate_root = tmp_path / "policy-root"
    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: generate_root,
    )
    assert main(["evaluation", "identity-policy", "generate"]) == 0
    assert main(["evaluation", "identity-policy", "check"]) == 0
