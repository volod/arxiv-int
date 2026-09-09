"""Production stage composing inventory, extraction lanes, validation, and publication."""

import hashlib
import json
import logging
from dataclasses import asdict
from pathlib import Path

from arxiv_int.extraction.artifacts import validate_manifest
from arxiv_int.extraction.docling import DoclingExtractor
from arxiv_int.extraction.inventory import inventory_inputs, materialized_source
from arxiv_int.extraction.iscc_tika import IsccTikaExtractor
from arxiv_int.extraction.model import (
    DEFAULT_POLICY,
    ExtractionError,
    ExtractionPolicy,
    InventoryInput,
)
from arxiv_int.extraction.ocr import OcrExtractor
from arxiv_int.extraction.publish import ExtractionPublisher
from arxiv_int.extraction.router import TieredExtractor
from arxiv_int.extraction.validate import ExtractionValidator
from arxiv_int.interfaces.pipeline import StageContext, StageOutcome, StageResult
from arxiv_int.interfaces.sources import SourceOccurrence
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.runtime.containment import overlaps, resolve_allowed_path

_LOG = logging.getLogger(__name__)


class ExtractionStage:
    """Extract unique content once and preserve every occurrence and failure."""

    stage = "extract"
    feature = "extraction"
    depends_on: tuple[str, ...] = ("inventory",)

    def __init__(
        self,
        policy: ExtractionPolicy = DEFAULT_POLICY,
        router: TieredExtractor | None = None,
    ) -> None:
        self.policy = policy
        self.router = router

    def run(self, context: StageContext) -> StageResult:
        """Run tiered extraction under one generation-scoped publication lock."""
        root = extraction_root(context)
        root.mkdir(parents=True, exist_ok=True)
        with pipeline_lock(root):
            return self._run(context)

    def _run(self, context: StageContext) -> StageResult:
        project_root = Path(context.options["project_root"])
        scratch = Path(context.options.get("tmp_dir", str(context.results_dir / "tmp"))).resolve()
        _protect(scratch, context)
        scratch.mkdir(parents=True, exist_ok=True)
        validator = ExtractionValidator(project_root)
        model_cache = Path(
            context.options.get("model_cache_dir", str(context.results_dir / "models"))
        ).resolve()
        _protect(model_cache, context)
        router = self.router or _production_router(self.policy, scratch, model_cache / "docling")
        publisher = ExtractionPublisher(
            context.results_dir.resolve(),
            context.generation_id,
            validator,
            self.policy.batch_rows,
        )
        seen: dict[str, str] = {}
        try:
            for item in inventory_inputs(context):
                check_cancelled()
                self._extract_item(context, item, publisher, router, scratch, seen)
            manifest = publisher.finish()
        except Exception:
            publisher.abort()
            raise
        digest = hash_file(manifest)[0]
        summary = validate_manifest(manifest, digest)
        documents = int(summary["documents"])
        quarantined = int(summary["quarantined"])
        outcome: StageOutcome = "produced" if documents and not quarantined else "partial"
        if not documents and not quarantined:
            outcome = "empty"
        _LOG.info(
            "extract documents=%s spans=%s quarantined=%s reused_content=%s",
            documents,
            summary["spans"],
            quarantined,
            summary["reused_content"],
        )
        partition = {"manifest": str(manifest), "sha256": digest}
        outputs = (
            DatasetRef("documents", "1.0.0", context.generation_id, partition),
            DatasetRef("spans", "1.0.0", context.generation_id, partition),
        )
        validations = (
            ValidationResultRef(
                contract,
                context.generation_id,
                getattr(validator, contract).fingerprint,
                "pass",
                True,
            )
            for contract in ("documents", "spans")
        )
        return StageResult(
            self.stage,
            outcome,
            (
                f"documents={documents}; spans={summary['spans']}; "
                f"quarantined={quarantined}; reused_content={summary['reused_content']}"
            ),
            outputs,
            tuple(validations),
        )

    def _extract_item(
        self,
        context: StageContext,
        item: InventoryInput,
        publisher: ExtractionPublisher,
        router: TieredExtractor,
        scratch: Path,
        seen: dict[str, str],
    ) -> None:
        """Extract or quarantine one inventory observation."""
        if item.status != "ready" or not item.content_hash:
            publisher.add_quarantine(
                item,
                f"inventory-{item.reason or 'unreadable'}",
                "inventory did not publish readable supported content",
            )
            return
        document_id = _document_id(item.content_hash)
        if item.content_hash in seen:
            publisher.add_occurrence(item, seen[item.content_hash], reused=True)
            return
        occurrence = SourceOccurrence(
            item.silo_id,
            item.relative_path,
            context.generation_id,
            content_hash=item.content_hash,
            container_path=item.relative_path if item.members else "",
            member_path=_member_path(item),
            status=item.status,
        )
        try:
            with materialized_source(context, item, self.policy, scratch) as source:
                document = router.extract(source, occurrence, item.media_type, item.encoding)
            if not document.text.strip():
                raise ExtractionError("empty-text", "all selected extractors returned empty text")
            publisher.add_document(item, document, document_id)
            seen[item.content_hash] = document_id
        except ExtractionError as error:
            publisher.add_quarantine(item, error.reason, error.detail)


def extraction_root(context: StageContext) -> Path:
    """Resolve and protect the extraction manifest root before writes."""
    results = context.results_dir.resolve()
    _protect(results, context)
    target = (
        results
        / "normalized/extraction/contract_version=1.0.0"
        / (f"generation_id={context.generation_id}")
    )
    resolved = resolve_allowed_path(target, (results,))
    if resolved != target:
        raise ValueError("extraction output path must not traverse symlinks")
    return resolved


def _production_router(
    policy: ExtractionPolicy, scratch: Path, docling_artifacts: Path
) -> TieredExtractor:
    return TieredExtractor(
        IsccTikaExtractor(policy, scratch),
        DoclingExtractor(policy, scratch, docling_artifacts),
        OcrExtractor(policy, scratch),
        policy,
    )


def _document_id(content_hash: str) -> str:
    return hashlib.sha256(f"document:{content_hash}".encode("ascii")).hexdigest()


def _member_path(item: InventoryInput) -> str:
    """Return the innermost relative member name for source-facing anchors."""
    if not item.members:
        return ""
    value = json.loads(item.members[-1])
    if not isinstance(value, list) or len(value) != 2 or not isinstance(value[1], str):
        raise ExtractionError("invalid-member-address", "inventory member address is invalid")
    return value[1]


def policy_identity(policy: ExtractionPolicy = DEFAULT_POLICY) -> str:
    """Return the stable configured extraction policy identity."""
    payload = json.dumps(asdict(policy), ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _protect(candidate: Path, context: StageContext) -> None:
    roots = [
        Path(context.options["project_root"]).resolve(),
        *(silo.root.resolve() for silo in context.silos),
        *(
            Path(value).resolve()
            for value in json.loads(context.options.get("protected_roots", "[]"))
        ),
    ]
    if candidate == Path(candidate.anchor) or any(overlaps(candidate, root) for root in roots):
        raise ValueError("extraction output overlaps protected roots")
