"""End-to-end held-out evaluation through the classification stage and CLI."""

import json
from pathlib import Path

from coverage import Coverage

from arxiv_int.cli import main
from arxiv_int.pipeline.inventory.model import Observation
from tests.classification.stage_helpers import classify
from tests.pipeline.chain import run_chain


def test_frozen_held_out_fixture_meets_quality_and_resource_gates(tmp_path: Path) -> None:
    fixtures: dict[str, str] = {}
    expected: dict[str, tuple[str, list[str]]] = {}
    cases = (
        (
            "machine",
            "Machine learning artificial intelligence data science",
            "tax:02.03.01",
            ["tax:02", "tax:02.03", "tax:02.03.01"],
        ),
        (
            "structure",
            "Structural engineering structural analysis and design",
            "tax:04.02.01",
            ["tax:04", "tax:04.02", "tax:04.02.01"],
        ),
        ("random", "xqz unrelated gibberish 193847", "unclassified", ["unclassified"]),
        ("blank", "\u200b\n", "unreadable", ["unreadable"]),
    )
    for index in range(8):
        for stem, text, primary, path in cases:
            name = f"{stem}-{index}.txt"
            fixtures[name] = text
            expected[name] = (primary, path)
    run = run_chain(tmp_path, fixtures=fixtures)
    classification = classify(run)
    manifest = Path(classification.outputs[0].partition["manifest"])
    labels = tmp_path / "held-out.jsonl"
    labels.write_text(
        "".join(
            json.dumps(
                {
                    "gold_ref": f"synthetic:{name}",
                    "item_id": Observation("one", name).occurrence_id,
                    "path": path,
                    "primary": primary,
                    "split": "test",
                },
                sort_keys=True,
            )
            + "\n"
            for name, (primary, path) in sorted(expected.items())
        ),
        encoding="ascii",
    )
    arguments = [
        "classification",
        "evaluate",
        "--run-id",
        run.context.run_id,
        "--classification",
        str(manifest),
        "--labels",
        str(labels),
        "--label-set",
        "synthetic-held-out",
        "--runs-dir",
        str(run.context.results_dir / "runs"),
        "--project-root",
        str(Path.cwd()),
    ]

    exit_code = main(arguments)
    report_path = (
        run.context.results_dir
        / "runs/run-chain/evaluation/classification/synthetic-held-out/metrics.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if Coverage.current() is None:
        assert exit_code == 0
        assert report["passed"] is True
        assert all(report["gates"].values())
    else:
        assert exit_code == 1
        assert {name for name, passed in report["gates"].items() if not passed} == {"throughput"}
    assert report["metrics"]["exact_accuracy"] == 1.0
