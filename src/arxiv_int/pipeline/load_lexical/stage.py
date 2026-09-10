"""Production stage loading canonical corpus rows and the ParadeDB projection."""

import logging
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import create_engine

from arxiv_int.interfaces.pipeline import StageContext, StageOutcome, StageResult
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef
from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.load_lexical.artifacts import (
    CHUNKS_CONTRACT,
    CONTRACT_VERSION,
    DATASET,
    DOCUMENTS_CONTRACT,
    LOADED_CONTRACTS,
    search_root,
)
from arxiv_int.pipeline.load_lexical.loader import LoadCounts, load_contract, schema_model
from arxiv_int.pipeline.load_lexical.publish import load_summary, publish_summary
from arxiv_int.pipeline.load_lexical.reconcile import Reconciliation, reconcile
from arxiv_int.pipeline.load_lexical.source import (
    CorpusChain,
    chunk_batches,
    corpus_chain,
    document_batches,
    document_languages,
)
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.retrieval.projection import active_target, index_size
from arxiv_int.stores.postgres.selection import store_database_url
from arxiv_int.stores.projections.lifecycle import build_projections
from arxiv_int.stores.projections.model import KIND_LEXICAL, KindBuild, ProjectionRequest

_LOG = logging.getLogger(__name__)


class LexicalLoadError(RuntimeError):
    """Raised when the lexical load or its projection build cannot be published."""


class LoadLexicalStage:
    """Bulk-load document and chunk rows, then rebuild the active BM25 projection."""

    stage = "load-lexical"
    feature = "store"
    depends_on: tuple[str, ...] = ("chunk",)

    def run(self, context: StageContext) -> StageResult:
        """Load and index one generation under a single publication lock."""
        root = lexical_root(context)
        root.mkdir(parents=True, exist_ok=True)
        with pipeline_lock(root):
            return self._run(context)

    def _run(self, context: StageContext) -> StageResult:
        project_root = Path(context.options["project_root"])
        chain = corpus_chain(context)
        url = store_database_url(project_root)
        validator = SnapshotValidator(project_root, LOADED_CONTRACTS)
        loads = self._load(chain, project_root, url, validator)
        check_cancelled()
        build = self._build(context, project_root, url)
        chunks = next(item for item in loads if item.contract == CHUNKS_CONTRACT)
        reconciliation, sizes = self._verify(url, build, chunks)
        if not reconciliation.ok:
            raise LexicalLoadError(f"lexical load did not reconcile: {reconciliation.detail}")
        summary = load_summary(
            generation_id=context.generation_id,
            build=build,
            loads=loads,
            reconciliation=reconciliation,
            upstream=chain.references(),
            index_bytes=sizes,
            activated=True,
        )
        manifest, digest = publish_summary(runs_dir(context), context.run_id, summary)
        return self._result(context, manifest, digest, validator, loads, reconciliation)

    def _load(
        self,
        chain: CorpusChain,
        project_root: Path,
        url: str,
        validator: SnapshotValidator,
    ) -> tuple[LoadCounts, ...]:
        model = schema_model(project_root)
        languages = document_languages(chain)
        engine = create_engine(url, pool_pre_ping=True)
        try:
            with engine.begin() as connection:
                documents = load_contract(
                    connection,
                    model=model,
                    validator=validator,
                    contract=DOCUMENTS_CONTRACT,
                    key="document_id",
                    batches=document_batches(chain, languages),
                )
                check_cancelled()
                chunks = load_contract(
                    connection,
                    model=model,
                    validator=validator,
                    contract=CHUNKS_CONTRACT,
                    key="chunk_id",
                    batches=chunk_batches(chain),
                )
        finally:
            engine.dispose()
        return (documents, chunks)

    def _build(self, context: StageContext, project_root: Path, url: str) -> KindBuild:
        result = build_projections(
            ProjectionRequest(
                run_id=context.run_id,
                project_root=project_root,
                database_url=url,
                kinds=(KIND_LEXICAL,),
                activate=True,
                publish=True,
                runs_dir=runs_dir(context),
            )
        )
        if not result.ok or not result.kinds:
            raise LexicalLoadError(f"lexical projection build failed: {result.detail}")
        if not result.activated:
            raise LexicalLoadError("lexical projection built but was not activated")
        return result.kinds[0]

    def _verify(
        self, url: str, build: KindBuild, chunks: LoadCounts
    ) -> tuple[Reconciliation, Mapping[str, int]]:
        engine = create_engine(url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                reconciliation = reconcile(
                    connection,
                    table=build.engine_object.split(":")[0],
                    loaded_chunks=chunks.rows,
                    loaded_checksum=chunks.checksum,
                    projection_checksum=build.checksum,
                )
                return reconciliation, index_size(connection, active_target(connection))
        finally:
            engine.dispose()

    def _result(
        self,
        context: StageContext,
        manifest: Path,
        digest: str,
        validator: SnapshotValidator,
        loads: tuple[LoadCounts, ...],
        reconciliation: Reconciliation,
    ) -> StageResult:
        rows = sum(item.rows for item in loads)
        outcome: StageOutcome = "produced" if reconciliation.projection_rows else "empty"
        _LOG.info(
            "load-lexical loaded=%d chunks=%d indexed=%d unindexed=%d",
            rows,
            reconciliation.canonical_chunks,
            reconciliation.projection_rows,
            reconciliation.unindexed_chunks,
        )
        output = DatasetRef(
            DATASET,
            CONTRACT_VERSION,
            context.generation_id,
            {"manifest": str(manifest), "sha256": digest},
        )
        validations = tuple(
            ValidationResultRef(
                item.contract, context.generation_id, validator.fingerprint, "pass", True
            )
            for item in loads
        )
        return StageResult(
            self.stage,
            outcome,
            f"loaded={rows}; indexed={reconciliation.projection_rows}",
            (output,),
            validations,
        )


def runs_dir(context: StageContext) -> Path:
    """Resolve the run journal root the stage writes lexical evidence under."""
    configured = context.options.get("runs_dir", "")
    return Path(configured) if configured else context.results_dir / "runs"


def lexical_root(context: StageContext) -> Path:
    """Resolve and protect the run-scoped lexical evidence root before writes."""
    return search_root(runs_dir(context), context.run_id)
