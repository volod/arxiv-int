"""Bounded, content-light operating-point review evidence."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arxiv_int.classification.layout import ClassificationLayout
from arxiv_int.classification.model import Classification, PhysicalFile
from arxiv_int.classification.vocabulary.review import vocabulary_packet
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.run.persist import write_json

_SAMPLES_PER_KIND = 5


@dataclass(slots=True)
class ReviewSamples:
    """Retain a bounded set of decisions without copying source text."""

    assigned: list[dict[str, object]] = field(default_factory=list)
    ambiguous: list[dict[str, object]] = field(default_factory=list)
    exceptional: list[dict[str, object]] = field(default_factory=list)

    def add(self, item: PhysicalFile, result: Classification) -> None:
        """Add one row to each applicable review category."""
        sample: dict[str, object] = {
            "occurrenceId": item.occurrence_id,
            "relativePath": item.relative_path,
            "primary": result.primary,
            "alternates": list(result.alternates),
            "confidence": result.confidence,
            "failureReason": result.failure_reason,
            "candidates": [
                {
                    "classId": candidate.class_id,
                    "score": round(candidate.score, 6),
                    "matchedTerms": list(candidate.matched_terms),
                }
                for candidate in result.candidates[:3]
            ],
        }
        if result.primary in {"unclassified", "unreadable"}:
            _append_bounded(self.exceptional, sample)
        else:
            _append_bounded(self.assigned, sample)
        if result.alternates:
            _append_bounded(self.ambiguous, sample)


def _append_bounded(destination: list[dict[str, object]], sample: dict[str, object]) -> None:
    if len(destination) < _SAMPLES_PER_KIND:
        destination.append(sample)


def write_operating_point_packet(
    context: StageContext,
    scheme_manifest: dict[str, Any],
    scheme_rows: tuple[dict[str, Any], ...],
    summary: dict[str, Any],
    mapping_manifest: Path,
    mapping_sha256: str,
    samples: ReviewSamples,
) -> None:
    """Write a draft packet tied to exact mapping, scheme, and policy identities."""
    runs_dir = Path(context.options.get("runs_dir", str(context.results_dir / "runs")))
    layout = ClassificationLayout.for_run(runs_dir, context.run_id)
    packet = vocabulary_packet(
        scheme_manifest,
        scheme_rows,
        inspect_command=f"arxiv-int classification tree --run-id {context.run_id}",
    )
    packet.update(
        accounting=summary["accounting"],
        classifier=summary["classifier"],
        countsByPrimary=summary["counts_by_primary"],
        mappingManifest={"path": str(mapping_manifest), "sha256": mapping_sha256},
        scheme=summary["scheme"],
        upstream=summary["upstream"],
        evaluation=None,
        pending=["prove-archive-classification-on-provided-archive"],
        readiness="draft",
        requiredDecision=(
            "accept or revise thresholds and exceptional outcomes, or retain unclassified; "
            "confirm Russian and Ukrainian captions"
        ),
        reviewSamples={
            "assigned": samples.assigned,
            "ambiguous": samples.ambiguous,
            "exceptional": samples.exceptional,
        },
        runtime=summary["runtime"],
    )
    write_json(layout.review / "operating-point.json", packet)
