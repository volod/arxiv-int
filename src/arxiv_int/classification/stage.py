"""Restartable production stage assigning every physical inventory file exactly once."""

import json
import logging
import resource
import time
from pathlib import Path
from typing import Any

from arxiv_int.classification.artifacts import (
    CLASSIFICATION_CLASSES,
    FILE_CLASSIFICATIONS,
    validate_manifest,
)
from arxiv_int.classification.features import CaptionClassifier
from arxiv_int.classification.layout import ClassificationLayout
from arxiv_int.classification.policy import load_classifier_policy
from arxiv_int.classification.publish import ClassificationPublisher
from arxiv_int.classification.review import ReviewSamples, write_operating_point_packet
from arxiv_int.classification.source import physical_files, source_snapshots
from arxiv_int.classification.vocabulary.build import build_scheme
from arxiv_int.classification.vocabulary.policy import load_scheme_policy
from arxiv_int.classification.vocabulary.snapshot import (
    Snapshot,
    check_snapshot,
    load_snapshot,
    write_snapshot,
)
from arxiv_int.interfaces.pipeline import StageContext, StageOutcome, StageResult
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.pipeline.stage_paths import stage_output_root

_LOG = logging.getLogger(__name__)


class ClassificationStage:
    """Classify physical files from validated inventory and normalization snapshots."""

    stage = "classify"
    feature = "lake"
    depends_on: tuple[str, ...] = ("inventory", "normalize")

    def run(self, context: StageContext) -> StageResult:
        """Publish a complete immutable mapping under one generation lock."""
        root = classification_root(context)
        root.mkdir(parents=True, exist_ok=True)
        with pipeline_lock(root):
            return self._run(context)

    def _run(self, context: StageContext) -> StageResult:
        started = time.monotonic()
        project_root = Path(context.options["project_root"])
        policy = load_classifier_policy(project_root)
        scheme_snapshot = _scheme_snapshot(context, project_root)
        sources = source_snapshots(context)
        validator = SnapshotValidator(project_root, (FILE_CLASSIFICATIONS, CLASSIFICATION_CLASSES))
        classifier = CaptionClassifier(scheme_snapshot.scheme, policy)
        physical_rows = int(sources["inventory"]["rows"]) - _virtual_member_count(
            Path(str(sources["inventory"]["manifest"]))
        )
        publisher = ClassificationPublisher(
            context.results_dir.resolve(),
            context.generation_id,
            validator,
            policy,
            str(scheme_snapshot.manifest["schemeId"]),
            context.run_id,
            str(sources["extraction"]["sha256"]),
            str(sources["normalization"]["normalizer_id"]),
        )
        review_samples = ReviewSamples()
        try:
            publisher.add_scheme(scheme_snapshot.rows)
            for item in physical_files(sources, max_text_chars=policy.max_text_chars):
                check_cancelled()
                classification = classifier.classify(item)
                if classifier.classify(item) != classification:
                    raise RuntimeError("classifier is not reproducible for unchanged input")
                publisher.add(item, classification)
                review_samples.add(item, classification)
            elapsed = time.monotonic() - started
            manifest = publisher.finish(
                upstream=_upstream_references(sources),
                scheme={
                    "scheme_id": scheme_snapshot.manifest["schemeId"],
                    "scheme_version": scheme_snapshot.manifest["schemeVersion"],
                    "content_sha256": scheme_snapshot.manifest["contentSha256"],
                },
                scheme_rows=len(scheme_snapshot.rows),
                elapsed_seconds=elapsed,
                peak_memory_mib=_peak_memory_mib(),
                physical_inventory_rows=physical_rows,
                virtual_member_rows=int(sources["inventory"]["rows"]) - physical_rows,
            )
        except BaseException:
            publisher.abort()
            raise
        digest = hash_file(manifest)[0]
        summary = validate_manifest(manifest, digest)
        write_operating_point_packet(
            context,
            scheme_snapshot.manifest,
            scheme_snapshot.rows,
            summary,
            manifest,
            digest,
            review_samples,
        )
        return self._result(context, manifest, digest, summary, validator)

    def _result(
        self,
        context: StageContext,
        manifest: Path,
        digest: str,
        summary: dict[str, Any],
        validator: SnapshotValidator,
    ) -> StageResult:
        rows = int(summary["file_classifications"])
        counts = summary["counts_by_primary"]
        exceptional = int(counts.get("unclassified", 0)) + int(counts.get("unreadable", 0))
        outcome: StageOutcome = "produced" if rows else "empty"
        partition = {"manifest": str(manifest), "sha256": digest}
        outputs = tuple(
            DatasetRef(contract, "1.0.0", context.generation_id, partition)
            for contract in (FILE_CLASSIFICATIONS, CLASSIFICATION_CLASSES)
        )
        validations = tuple(
            ValidationResultRef(
                contract, context.generation_id, validator[contract].fingerprint, "pass", True
            )
            for contract in (FILE_CLASSIFICATIONS, CLASSIFICATION_CLASSES)
        )
        _LOG.info(
            "classify physical_files=%d exceptional=%d throughput=%.2f files/s",
            rows,
            exceptional,
            summary["runtime"]["throughput_files_per_second"],
        )
        return StageResult(
            self.stage,
            outcome,
            f"physical_files={rows}; exceptional={exceptional}",
            outputs,
            validations,
        )


def classification_root(context: StageContext) -> Path:
    """Resolve and protect the classification manifest root before writes."""
    return stage_output_root(context, "normalized/classification")


def _scheme_snapshot(context: StageContext, project_root: Path) -> Snapshot:
    runs_dir = Path(context.options.get("runs_dir", str(context.results_dir / "runs")))
    directory = ClassificationLayout.for_run(runs_dir, context.run_id).scheme
    scheme_policy = load_scheme_policy(project_root)
    if directory.exists():
        findings = check_snapshot(directory, scheme_policy)
        if findings:
            raise ValueError("classification scheme snapshot is stale or damaged")
        return load_snapshot(directory)
    built = build_scheme(scheme_policy, run_id=context.run_id)
    if not built.publishable:
        raise ValueError("packaged classification scheme did not pass validation")
    write_snapshot(directory, built)
    return load_snapshot(directory)


def _virtual_member_count(inventory_manifest: Path) -> int:
    count = 0
    for path in sorted(inventory_manifest.parent.glob("*.metadata.jsonl")):
        with path.open(encoding="ascii") as handle:
            for line in handle:
                if line.strip() and json.loads(line).get("members"):
                    count += 1
    return count


def _upstream_references(sources: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    return {
        name: {"manifest": str(summary["manifest"]), "sha256": str(summary["sha256"])}
        for name, summary in sources.items()
    }


def _peak_memory_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
