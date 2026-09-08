from pathlib import Path

import pytest

from arxiv_int.interfaces.stores import DatasetRef, TransformationRunRef, ValidationResultRef
from tests.interfaces.test_protocols import FakeArtifactStore


def _chunks(generation_id: str) -> DatasetRef:
    return DatasetRef(
        dataset="chunks",
        contract_version="1.0.0",
        generation_id=generation_id,
        partition={"bucket": "ab"},
    )


def test_dataset_reference_compares_by_value_and_carries_no_absolute_path() -> None:
    reference = _chunks("gen-1")

    assert reference == DatasetRef(
        dataset="chunks",
        contract_version="1.0.0",
        generation_id="gen-1",
        partition={"bucket": "ab"},
    )
    assert FakeArtifactStore().locate(reference) == Path("chunks") / "gen-1"


def test_distinct_generations_of_one_partition_are_not_interchangeable() -> None:
    first = _chunks("gen-1")
    second = _chunks("gen-2")
    store = FakeArtifactStore()

    assert first != second
    assert first.logical_partition() == second.logical_partition()
    assert store.locate(first) != store.locate(second)
    assert store.publish(second, Path("staged")) == Path("staged") / "gen-2"


def test_dataset_partition_mapping_cannot_be_mutated_after_construction() -> None:
    payload = {"bucket": "ab"}
    reference = DatasetRef(
        dataset="chunks",
        contract_version="1.0.0",
        generation_id="gen-1",
        partition=payload,
    )
    payload["bucket"] = "zz"
    assert reference.partition["bucket"] == "ab"
    with pytest.raises(TypeError):
        reference.partition["bucket"] = "zz"  # type: ignore[index]


def test_failed_validation_ref_cannot_look_publishable() -> None:
    failed = ValidationResultRef(
        contract_id="urn:arxiv-int:contract:chunks:1.0.0",
        generation_id="gen-1",
        catalog_fingerprint="sha256:catalog",
        status="fail",
        publishable=False,
    )
    passed = ValidationResultRef(
        contract_id="urn:arxiv-int:contract:chunks:1.0.0",
        generation_id="gen-1",
        catalog_fingerprint="sha256:catalog",
        status="pass",
        publishable=True,
    )

    assert failed.publishable is False
    assert passed.publishable is True
    assert failed.generation_id == passed.generation_id


def test_transformation_run_ref_keeps_activation_separate_from_status() -> None:
    failed = TransformationRunRef(
        run_id="run-1",
        generation_id="gen-1",
        command="build",
        status="failed",
        input_fingerprint="sha256:input",
        model_fingerprint="sha256:model",
        activatable=False,
    )
    not_run = TransformationRunRef(
        run_id="run-1",
        generation_id="gen-1",
        command="build",
        status="not-run",
        input_fingerprint="sha256:input",
        model_fingerprint="sha256:model",
        activatable=False,
    )

    assert failed.activatable is False
    assert not_run.status == "not-run"
    assert failed.command == not_run.command


def test_dishonest_quality_and_transform_flags_are_refused() -> None:
    with pytest.raises(ValueError, match="publishable"):
        ValidationResultRef(
            contract_id="urn:arxiv-int:contract:chunks:1.0.0",
            generation_id="gen-1",
            catalog_fingerprint="sha256:catalog",
            status="fail",
            publishable=True,
        )
    with pytest.raises(ValueError, match="activatable"):
        TransformationRunRef(
            run_id="run-1",
            generation_id="gen-1",
            command="build",
            status="failed",
            input_fingerprint="sha256:input",
            model_fingerprint="sha256:model",
            activatable=True,
        )
