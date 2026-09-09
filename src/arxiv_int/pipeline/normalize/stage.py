"""Production stage building canonical text views without touching extracted records."""

import logging
from pathlib import Path

from arxiv_int.interfaces.pipeline import StageContext, StageOutcome, StageResult
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.normalize.artifacts import CONTRACT, validate_manifest
from arxiv_int.pipeline.normalize.language import detect_language, profile_fingerprint
from arxiv_int.pipeline.normalize.model import (
    DEFAULT_POLICY,
    DocumentInput,
    NormalizationError,
    NormalizePolicy,
    normalizer_id,
)
from arxiv_int.pipeline.normalize.publish import NormalizationPublisher
from arxiv_int.pipeline.normalize.source import (
    document_inputs,
    extraction_snapshot,
    snapshot_roots,
)
from arxiv_int.pipeline.normalize.text import canonical_view, search_view
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.pipeline.stage_paths import stage_output_root

_LOG = logging.getLogger(__name__)


class NormalizeStage:
    """Derive reversible canonical and search views for every extracted document."""

    stage = "normalize"
    feature = "lake"
    depends_on: tuple[str, ...] = ("extract",)

    def __init__(self, policy: NormalizePolicy = DEFAULT_POLICY) -> None:
        self.policy = policy

    def run(self, context: StageContext) -> StageResult:
        """Normalize one generation under a single publication lock."""
        root = normalization_root(context)
        root.mkdir(parents=True, exist_ok=True)
        with pipeline_lock(root):
            return self._run(context)

    def _run(self, context: StageContext) -> StageResult:
        project_root = Path(context.options["project_root"])
        manifest_path, digest, summary = extraction_snapshot(context)
        validator = SnapshotValidator(project_root, (CONTRACT,))
        normalizer = normalizer_id(self.policy, profile_fingerprint(project_root))
        publisher = NormalizationPublisher(
            context.results_dir.resolve(),
            context.generation_id,
            validator,
            normalizer,
            self.policy.batch_rows,
        )
        try:
            for item in document_inputs(snapshot_roots(summary)):
                check_cancelled()
                self._normalize_item(item, publisher, project_root)
            manifest = publisher.finish({"manifest": str(manifest_path), "sha256": digest})
        except BaseException:
            publisher.abort()
            raise
        return self._result(context, manifest, validator, normalizer)

    def _normalize_item(
        self, item: DocumentInput, publisher: NormalizationPublisher, project_root: Path
    ) -> None:
        try:
            original = self._read(item)
            canonical = canonical_view(original)
            if not canonical.text.strip():
                raise NormalizationError(
                    "empty-canonical-text", "normalization produced no retained characters"
                )
            search = search_view(canonical.text)
            language = detect_language(
                canonical.text,
                sample_chars=self.policy.language_sample_chars,
                min_letters=self.policy.min_language_letters,
                min_confidence=self.policy.min_language_confidence,
                project_root=project_root,
            )
        except NormalizationError as error:
            publisher.add_quarantine(item, error.reason, error.detail)
            return
        publisher.add_document(item, canonical, search, language)

    def _read(self, item: DocumentInput) -> str:
        if item.text_path.is_symlink() or not item.text_path.is_file():
            raise NormalizationError("missing-extracted-text", "extracted text is not a real file")
        size = item.text_path.stat().st_size
        if size > self.policy.max_document_chars * 4:
            raise NormalizationError(
                "document-size-limit",
                f"extracted text exceeds the {self.policy.max_document_chars} character budget",
            )
        text = item.text_path.read_text(encoding="utf-8")
        if len(text) > self.policy.max_document_chars:
            raise NormalizationError(
                "document-size-limit",
                f"extracted text exceeds the {self.policy.max_document_chars} character budget",
            )
        return text

    def _result(
        self,
        context: StageContext,
        manifest: Path,
        validator: SnapshotValidator,
        normalizer: str,
    ) -> StageResult:
        digest = hash_file(manifest)[0]
        summary = validate_manifest(manifest, digest)
        documents = int(summary["normalized_documents"])
        quarantined = int(summary["quarantined"])
        outcome: StageOutcome = "produced" if documents else ("partial" if quarantined else "empty")
        _LOG.info(
            "normalize documents=%s quarantined=%s languages=%s normalizer=%s",
            documents,
            quarantined,
            summary["languages"],
            normalizer,
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
            f"normalized_documents={documents}; quarantined={quarantined}",
            (output,),
            (validation,),
        )


def normalization_root(context: StageContext) -> Path:
    """Resolve and protect the normalization manifest root before writes."""
    return stage_output_root(context, "normalized/normalization")
