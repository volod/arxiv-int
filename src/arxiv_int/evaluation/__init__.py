"""Dependency-free evaluation primitives, fixtures, bundles, and proof export."""

from arxiv_int.evaluation.bundles import (
    BundleSpec,
    PublishedBundle,
    publish_run_bundle,
    verify_run_bundle,
)
from arxiv_int.evaluation.bundles.errors import (
    BundleError,
    BundleExistsError,
    BundleIntegrityError,
    BundleLayoutError,
    BundleManifestError,
)
from arxiv_int.evaluation.evaluate.errors import (
    MissingEvidenceError,
    ProofExistsError,
    ProofUnknownCapabilityError,
)
from arxiv_int.evaluation.evaluate.run import EvaluateRequest, run_evaluate
from arxiv_int.evaluation.evaluate.stage import EvaluateStage
from arxiv_int.evaluation.export.errors import (
    ExportCollisionError,
    ExportError,
    ExportLeakError,
    ExportUnsupportedError,
)
from arxiv_int.evaluation.export.exporter import (
    ExportMapping,
    ExportRequest,
    PublishedExport,
    export_proof_bundle,
)
from arxiv_int.evaluation.scoring.linkage import LinkageLabel, LinkageMetrics, score_linkage
from arxiv_int.evaluation.scoring.metrics import ExtractionMetrics, extraction_metrics, text_metrics
from arxiv_int.evaluation.scoring.paired import (
    PairedComparison,
    PairedVerdict,
    paired_comparison,
    paired_verdict,
)

__all__ = [
    "BundleError",
    "BundleExistsError",
    "BundleIntegrityError",
    "BundleLayoutError",
    "BundleManifestError",
    "BundleSpec",
    "EvaluateRequest",
    "EvaluateStage",
    "ExportCollisionError",
    "ExportError",
    "ExportLeakError",
    "ExportMapping",
    "ExportRequest",
    "ExportUnsupportedError",
    "ExtractionMetrics",
    "LinkageLabel",
    "LinkageMetrics",
    "MissingEvidenceError",
    "PairedComparison",
    "PairedVerdict",
    "ProofExistsError",
    "ProofUnknownCapabilityError",
    "PublishedBundle",
    "PublishedExport",
    "export_proof_bundle",
    "extraction_metrics",
    "paired_comparison",
    "paired_verdict",
    "publish_run_bundle",
    "run_evaluate",
    "score_linkage",
    "text_metrics",
    "verify_run_bundle",
]
