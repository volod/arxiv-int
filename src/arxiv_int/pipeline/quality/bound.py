"""Producer-boundary Pandera and dbt checks without a second scheduler."""

from collections.abc import Mapping
from dataclasses import asdict
from typing import Protocol

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.data_quality.engine.model import STATUS_NOT_RUN, STATUS_PASS
from arxiv_int.interfaces.pipeline import StageResult
from arxiv_int.interfaces.stores import TransformationRunRef, ValidationResultRef
from arxiv_int.pipeline.control.quality import GLOBAL_SCOPE, QualityCheck, activation_decision
from arxiv_int.pipeline.dag.registry import StageSpec
from arxiv_int.pipeline.run.errors import QualityBoundaryError

_PASSING_GLOBAL = QualityCheck("global.fixture", STATUS_PASS, GLOBAL_SCOPE, "error", True)


class QualityBoundary(Protocol):
    """Run declared validators and dbt selections at a producer boundary."""

    def checks(self) -> tuple[QualityCheck, ...]:
        """Return required whole-snapshot checks, including explicit not-run evidence."""

    def validate(
        self, dataset: str, files: Mapping[str, bytes], generation_id: str
    ) -> ValidationResultRef:
        """Validate one produced dataset."""

    def transform(
        self, select: tuple[str, ...], generation_id: str, run_id: str
    ) -> TransformationRunRef:
        """Run one declared dbt selection."""


class FixtureQuality:
    """Deterministic boundary used by fixture DAGs; statuses are injectable."""

    def __init__(
        self,
        *,
        validation_status: str = STATUS_PASS,
        transform_status: str = "ok",
        publishable: bool | None = None,
        activatable: bool | None = None,
    ) -> None:
        self.validation_status = validation_status
        self.transform_status = transform_status
        self.publishable = validation_status == STATUS_PASS if publishable is None else publishable
        self.activatable = transform_status == "ok" if activatable is None else activatable
        self.validated: list[str] = []
        self.transformed: list[tuple[str, ...]] = []

    def checks(self) -> tuple[QualityCheck, ...]:
        """Fixture-only global validation evidence."""
        return passing_checks()

    def validate(
        self, dataset: str, files: Mapping[str, bytes], generation_id: str
    ) -> ValidationResultRef:
        """Return the configured validation status for one dataset."""
        del files
        self.validated.append(dataset)
        return ValidationResultRef(
            dataset,
            generation_id,
            "fixture-catalog",
            self.validation_status,
            self.publishable,
        )

    def transform(
        self, select: tuple[str, ...], generation_id: str, run_id: str
    ) -> TransformationRunRef:
        """Return the configured dbt status for one selection."""
        self.transformed.append(select)
        return TransformationRunRef(
            run_id,
            generation_id,
            "build",
            self.transform_status,
            "fixture-input",
            "fixture-model",
            self.activatable,
        )


def passing_checks() -> tuple[QualityCheck, ...]:
    """Return the global check the shard executor requires before a worker runs."""
    return (_PASSING_GLOBAL,)


def apply_boundary(
    spec: StageSpec,
    files: Mapping[str, bytes],
    quality: QualityBoundary,
    *,
    generation_id: str,
    run_id: str,
    result: StageResult,
) -> bytes:
    """Validate exact-generation evidence and retain it beside the stage payload."""
    validations = tuple(
        quality.validate(dataset, files, generation_id) for dataset in spec.validators
    )
    for dataset, ref in zip(spec.validators, validations, strict=True):
        if ref.contract_id != dataset:
            raise QualityBoundaryError(f"validation contract mismatch: {dataset}")
    transformations: tuple[TransformationRunRef, ...] = (
        (quality.transform(spec.dbt_select, generation_id, run_id),) if spec.dbt_select else ()
    )
    validations += result.validations
    transformations += result.transformations
    checks = quality.checks()
    decision = activation_decision(
        checks,
        validations=validations,
        transformations=transformations,
        generation_id=generation_id,
    )
    if not decision.allowed:
        raise QualityBoundaryError(";".join(decision.blocking))
    return normalize_json(
        {
            "generation_id": generation_id,
            "checks": [asdict(item) for item in checks],
            "validations": [asdict(item) for item in validations],
            "transformations": [asdict(item) for item in transformations],
        }
    ).encode("ascii")


def production_quality() -> QualityBoundary:
    """Return the adapter that calls shared Pandera and dbt runners on demand."""
    return ProductionQuality()


class ProductionQuality:
    """Lazy adapter over ``data_quality`` and ``transformations`` runners."""

    def checks(self) -> tuple[QualityCheck, ...]:
        """Concrete global validators remain unimplemented; refuse publication."""
        return (QualityCheck("global.unexecuted", STATUS_NOT_RUN, GLOBAL_SCOPE, "error"),)

    def validate(
        self, dataset: str, files: Mapping[str, bytes], generation_id: str
    ) -> ValidationResultRef:
        """Map a real dataset check onto a validation pointer; tests inject fixtures."""
        del files
        return ValidationResultRef(dataset, generation_id, "unexecuted", STATUS_NOT_RUN, False)

    def transform(
        self, select: tuple[str, ...], generation_id: str, run_id: str
    ) -> TransformationRunRef:
        """Invoke the shared dbt runner for one declared selection."""
        from arxiv_int.runtime.project_root import find_project_root
        from arxiv_int.transformations.model import TransformRequest
        from arxiv_int.transformations.runner import run_transform

        result = run_transform(
            TransformRequest(
                command="build",
                run_id=run_id,
                project_root=find_project_root(),
                select=select,
            )
        )
        return TransformationRunRef(
            run_id,
            generation_id,
            "build",
            result.status,
            result.input_fingerprint or "missing",
            result.model_fingerprint or "missing",
            result.activatable,
        )
