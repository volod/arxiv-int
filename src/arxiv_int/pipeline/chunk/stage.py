"""Production stage emitting source-aligned chunks for retained documents."""

import logging
from pathlib import Path

from arxiv_int.interfaces.pipeline import StageContext, StageOutcome, StageResult
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef
from arxiv_int.pipeline.chunk.artifacts import CONTRACT, validate_manifest
from arxiv_int.pipeline.chunk.assemble import chunk_document
from arxiv_int.pipeline.chunk.model import (
    DEFAULT_POLICY,
    ChunkingError,
    ChunkPolicy,
    chunker_id,
)
from arxiv_int.pipeline.chunk.publish import ChunkPublisher
from arxiv_int.pipeline.chunk.source import (
    ChunkInput,
    canonical_text,
    chunk_inputs,
    original_offsets,
    suppressed_documents,
    upstream,
)
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.pipeline.stage_paths import stage_output_root

_LOG = logging.getLogger(__name__)


class ChunkStage:
    """Emit deterministic chunks that stay aligned to their source offsets."""

    stage = "chunk"
    feature = "lake"
    depends_on: tuple[str, ...] = ("normalize", "dedupe")

    def __init__(self, policy: ChunkPolicy = DEFAULT_POLICY) -> None:
        self.policy = policy

    def run(self, context: StageContext) -> StageResult:
        """Chunk one generation under a single publication lock."""
        root = chunk_root(context)
        root.mkdir(parents=True, exist_ok=True)
        with pipeline_lock(root):
            return self._run(context)

    def _run(self, context: StageContext) -> StageResult:
        project_root = Path(context.options["project_root"])
        normalization = upstream(context, "normalization")
        dedupe = upstream(context, "dedupe")
        validator = SnapshotValidator(project_root, (CONTRACT,))
        chunker = chunker_id(self.policy)
        publisher = ChunkPublisher(
            context.results_dir.resolve(),
            context.generation_id,
            validator,
            chunker,
            self.policy.batch_rows,
        )
        try:
            suppressed = suppressed_documents(dedupe.roots())
            for item in chunk_inputs(normalization.roots()):
                check_cancelled()
                if item.document_id in suppressed:
                    publisher.add_suppressed()
                    continue
                self._chunk_item(item, publisher)
            manifest = publisher.finish(
                {
                    "normalization": normalization.reference(),
                    "dedupe": dedupe.reference(),
                }
            )
        except BaseException:
            publisher.abort()
            raise
        return self._result(context, manifest, validator, chunker)

    def _chunk_item(self, item: ChunkInput, publisher: ChunkPublisher) -> None:
        try:
            text = canonical_text(item)
            offsets = original_offsets(item)
            produced = chunk_document(text, self.policy)
        except ChunkingError as error:
            publisher.add_quarantine(item, error.reason, error.detail)
            return
        except (OSError, ValueError, KeyError) as error:
            publisher.add_quarantine(item, "unreadable-normalized-views", str(error))
            return
        publisher.add_document(item, produced.chunks, offsets, truncated=produced.truncated)

    def _result(
        self,
        context: StageContext,
        manifest: Path,
        validator: SnapshotValidator,
        chunker: str,
    ) -> StageResult:
        digest = hash_file(manifest)[0]
        summary = validate_manifest(manifest, digest)
        chunks = int(summary["chunks"])
        documents = int(summary["chunked_documents"])
        quarantined = int(summary["quarantined"])
        outcome: StageOutcome = "produced" if chunks else ("partial" if quarantined else "empty")
        _LOG.info(
            "chunk chunks=%s documents=%s suppressed=%s quarantined=%s kinds=%s chunker=%s",
            chunks,
            documents,
            summary["suppressed_documents"],
            quarantined,
            summary["kinds"],
            chunker,
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
            f"chunks={chunks}; documents={documents}; quarantined={quarantined}",
            (output,),
            (validation,),
        )


def chunk_root(context: StageContext) -> Path:
    """Resolve and protect the chunk manifest root before writes."""
    return stage_output_root(context, "normalized/chunking")
