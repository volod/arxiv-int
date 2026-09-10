"""Production stage proposing reversible duplicate and edition groups."""

import logging
import tempfile
from pathlib import Path

from arxiv_int.interfaces.pipeline import StageContext, StageOutcome, StageResult
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.dedupe.artifacts import CONTRACT, validate_manifest
from arxiv_int.pipeline.dedupe.decide import GroupingPlan, plan_groups
from arxiv_int.pipeline.dedupe.group import DUPLICATE_FAMILY, EDITION_FAMILY
from arxiv_int.pipeline.dedupe.model import DEFAULT_POLICY, DedupePolicy, dedupe_id
from arxiv_int.pipeline.dedupe.publish import DedupePublisher
from arxiv_int.pipeline.dedupe.sketches import SketchTables
from arxiv_int.pipeline.dedupe.source import (
    NormalizedInput,
    normalization_snapshot,
    normalized_inputs,
    snapshot_roots,
)
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.pipeline.stage_paths import stage_output_root, stage_scratch

_LOG = logging.getLogger(__name__)


class DedupeStage:
    """Group exact, near-duplicate, and edition documents without deleting any."""

    stage = "dedupe"
    feature = "lake"
    depends_on: tuple[str, ...] = ("normalize",)

    def __init__(self, policy: DedupePolicy = DEFAULT_POLICY) -> None:
        self.policy = policy

    def run(self, context: StageContext) -> StageResult:
        """Group one generation under a single publication lock."""
        root = dedupe_root(context)
        root.mkdir(parents=True, exist_ok=True)
        with pipeline_lock(root):
            return self._run(context)

    def _run(self, context: StageContext) -> StageResult:
        project_root = Path(context.options["project_root"])
        manifest_path, digest, summary = normalization_snapshot(context)
        validator = SnapshotValidator(project_root, (CONTRACT,))
        identity = dedupe_id(self.policy)
        publisher = DedupePublisher(
            context.results_dir.resolve(),
            context.generation_id,
            validator,
            identity,
            self.policy.batch_rows,
        )
        try:
            with tempfile.TemporaryDirectory(
                dir=stage_scratch(context), prefix="dedupe-"
            ) as scratch:
                documents, sketched, plan = self._plan(summary, Path(scratch))
            self._publish(publisher, plan)
            manifest = publisher.finish(
                {"manifest": str(manifest_path), "sha256": digest},
                plan.members,
                {
                    "normalized_documents": documents,
                    "sketched_documents": sketched,
                    "candidate_pairs": plan.candidates,
                    "candidates_truncated": plan.truncated,
                    "policy": {
                        "duplicate_similarity": self.policy.duplicate_similarity,
                        "edition_similarity": self.policy.edition_similarity,
                        "shingle_words": self.policy.shingle_words,
                        "sketch_bins": self.policy.sketch_bins,
                        "band_rows": self.policy.band_rows,
                    },
                },
            )
        except BaseException:
            publisher.abort()
            raise
        return self._result(context, manifest, validator, identity)

    def _plan(self, summary: dict[str, object], scratch: Path) -> tuple[int, int, GroupingPlan]:
        roots = snapshot_roots(summary)
        tables = SketchTables(scratch, self.policy)
        try:
            for item in normalized_inputs(roots):
                check_cancelled()
                tables.add(item, self._search_text(item))
        finally:
            tables.close()
        check_cancelled()
        plan = plan_groups(tables.sketch_path, tables.band_path, self.policy)
        return tables.documents, tables.sketched, plan

    def _search_text(self, item: NormalizedInput) -> str:
        path = item.search_path
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"normalized search view is missing for {item.document_id}")
        return path.read_bytes().decode("utf-8")

    def _publish(self, publisher: DedupePublisher, plan: GroupingPlan) -> None:
        publisher.add_members(plan.duplicates, DUPLICATE_FAMILY)
        publisher.add_members(plan.editions, EDITION_FAMILY)
        for edge, family in plan.pairs:
            publisher.add_pair(edge, family)

    def _result(
        self,
        context: StageContext,
        manifest: Path,
        validator: SnapshotValidator,
        identity: str,
    ) -> StageResult:
        digest = hash_file(manifest)[0]
        summary = validate_manifest(manifest, digest)
        groups = int(summary["duplicate_groups"])
        memberships = int(summary["duplicate_memberships"])
        suppressed = int(summary["suppressed_documents"])
        outcome: StageOutcome = "produced" if memberships else "empty"
        _LOG.info(
            "dedupe groups=%s memberships=%s suppressed=%s methods=%s dedupe_id=%s",
            groups,
            memberships,
            suppressed,
            summary["methods"],
            identity,
        )
        output = DatasetRef(
            CONTRACT,
            "1.0.0",
            context.generation_id,
            {"manifest": str(manifest), "sha256": digest},
        )
        validation = ValidationResultRef(
            CONTRACT, context.generation_id, validator[CONTRACT].fingerprint, "pass", True
        )
        return StageResult(
            self.stage,
            outcome,
            f"duplicate_groups={groups}; memberships={memberships}; suppressed={suppressed}",
            (output,),
            (validation,),
        )


def dedupe_root(context: StageContext) -> Path:
    """Resolve and protect the duplicate-grouping manifest root before writes."""
    return stage_output_root(context, "normalized/dedupe")
