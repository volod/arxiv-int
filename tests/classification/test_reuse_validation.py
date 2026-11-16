"""A cached classify attempt must still point at an intact external snapshot."""

import json
from pathlib import Path

import pytest

from arxiv_int.classification.reuse import validate_classification_output
from arxiv_int.pipeline.dag.execute import _output_validators
from tests.classification.stage_helpers import classify
from tests.pipeline.chain import run_chain


def _attempt(tmp_path: Path) -> tuple[Path, Path]:
    run = run_chain(
        tmp_path, fixtures={"ml.txt": "Machine learning artificial intelligence data science"}
    )
    result = classify(run)
    directory = tmp_path / "attempt"
    directory.mkdir()
    (directory / "stage.json").write_text(
        json.dumps(
            {
                "stage": "classify",
                "outputs": [
                    {
                        "dataset": item.dataset,
                        "generationId": item.generation_id,
                        "partition": dict(item.partition),
                    }
                    for item in result.outputs
                ],
            }
        ),
        encoding="ascii",
    )
    return directory, run.manifest(result)


def test_classification_snapshot_is_rechecked_before_cache_hit(tmp_path: Path) -> None:
    directory, manifest = _attempt(tmp_path)
    validate_classification_output(directory)
    summary = json.loads(manifest.read_text(encoding="ascii"))
    part = next(Path(summary["roots"]["file-classifications"]).glob("part-*.parquet"))
    part.write_bytes(part.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="checksum"):
        validate_classification_output(directory)


def test_classification_reuse_validator_is_registered() -> None:
    assert validate_classification_output in _output_validators()


def test_classification_reuse_refuses_wrong_generation(tmp_path: Path) -> None:
    directory, _ = _attempt(tmp_path)
    path = directory / "stage.json"
    payload = json.loads(path.read_text(encoding="ascii"))
    payload["outputs"][0]["generationId"] = "other"
    path.write_text(json.dumps(payload), encoding="ascii")
    with pytest.raises(ValueError, match="generation"):
        validate_classification_output(directory)
