import hashlib
import json
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.extraction.inventory import inventory_inputs, materialized_source
from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.extraction.ocr import _image_pixels
from arxiv_int.extraction.process import _failure_detail, run_command
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.inventory.stage import InventoryStage


def test_command_timeout_kills_bounded_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    killed: list[tuple[int, int]] = []

    class Process:
        pid = 42
        waits = 0

        def wait(self, timeout: int | None = None) -> int:
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired("fixture", timeout)
            return -9

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr("os.killpg", lambda pid, signal: killed.append((pid, signal)))
    with pytest.raises(ExtractionError, match="exceeded 1 seconds") as caught:
        run_command(
            (sys.executable, "-c", "import time; time.sleep(30)"),
            timeout_seconds=1,
            output_bytes=1024,
            scratch=tmp_path,
        )

    assert caught.value.reason == "tool-timeout"
    assert killed == [(42, 9)]


def test_tool_failure_detail_redacts_host_paths(tmp_path: Path) -> None:
    executable = str(tmp_path / ".venv/bin/docling")
    stderr = f'Traceback\n  File "{executable}"\nRuntimeError: failed at {tmp_path}/input.pdf'

    detail = _failure_detail(stderr.encode(), executable, tmp_path)

    assert str(tmp_path) not in detail
    assert detail == "RuntimeError: failed at <path>"


def test_command_output_limit_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(ExtractionError, match="output exceeded") as caught:
        run_command(
            (sys.executable, "-c", "print('x' * 100)"),
            timeout_seconds=5,
            output_bytes=20,
            scratch=tmp_path,
        )

    assert caught.value.reason == "tool-output-limit"


def test_materialized_archive_member_matches_inventory_and_preserves_source(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    archive = sources / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("inside/report.txt", b"member evidence")
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    context = StageContext(
        "inventory",
        "run-member",
        "run-member",
        (SiloRoot("one", sources),),
        tmp_path / "results",
        {"project_root": str(Path.cwd()), "tmp_dir": str(tmp_path / "scratch")},
    )
    InventoryStage().run(context)
    member = next(item for item in inventory_inputs(context) if item.members)

    with materialized_source(
        replace(context, stage="extract"),
        member,
        ExtractionPolicy(),
        tmp_path / "scratch",
    ) as staged:
        assert staged.read_bytes() == b"member evidence"

    assert hashlib.sha256(archive.read_bytes()).hexdigest() == before
    assert list((tmp_path / "scratch").iterdir()) == []


def test_png_pixel_budget_reads_header_without_decompression(tmp_path: Path) -> None:
    image = tmp_path / "large.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (10_000).to_bytes(4, "big") * 2)

    assert _image_pixels(image) == 100_000_000


def test_inventory_member_address_remains_structured(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    with zipfile.ZipFile(sources / "bundle.zip", "w") as archive:
        archive.writestr("nested/report.txt", b"text")
    context = StageContext(
        "inventory",
        "run-address",
        "run-address",
        (SiloRoot("one", sources),),
        tmp_path / "results",
        {"project_root": str(Path.cwd())},
    )
    InventoryStage().run(context)

    member = next(item for item in inventory_inputs(context) if item.members)

    assert json.loads(member.members[0]) == [0, "nested/report.txt"]


def test_ooxml_is_kept_as_one_document_for_extraction(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    with zipfile.ZipFile(sources / "table.xlsx", "w") as workbook:
        workbook.writestr("[Content_Types].xml", b"<Types/>")
    context = StageContext(
        "inventory",
        "run-xlsx",
        "run-xlsx",
        (SiloRoot("one", sources),),
        tmp_path / "results",
        {"project_root": str(Path.cwd())},
    )
    InventoryStage().run(context)

    rows = list(inventory_inputs(context))

    assert len(rows) == 1
    assert rows[0].media_type.endswith("spreadsheetml.sheet")
    assert rows[0].members == ()


def test_extraction_reads_checksum_validated_reused_inventory(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "document.txt").write_text("reused inventory", encoding="utf-8")
    inventory_context = StageContext(
        "inventory",
        "run-old",
        "run-old",
        (SiloRoot("one", sources),),
        tmp_path / "results",
        {"project_root": str(Path.cwd())},
    )
    result = InventoryStage().run(inventory_context)
    partition = result.outputs[0].partition
    extraction_context = StageContext(
        "extract",
        "run-new",
        "run-new",
        inventory_context.silos,
        inventory_context.results_dir,
        {
            "project_root": str(Path.cwd()),
            "inventory_manifest": partition["manifest"],
            "inventory_manifest_sha256": partition["sha256"],
        },
    )

    rows = list(inventory_inputs(extraction_context))

    assert len(rows) == 1
    assert rows[0].relative_path == "document.txt"
