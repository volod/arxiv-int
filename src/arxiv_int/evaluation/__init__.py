"""Dependency-free evaluation primitives, fixtures, bundles, and proof export."""

from arxiv_int.evaluation.bundle_errors import (
    BundleError,
    BundleExistsError,
    BundleIntegrityError,
    BundleLayoutError,
    BundleManifestError,
)
from arxiv_int.evaluation.bundles import (
    BundleSpec,
    PublishedBundle,
    publish_run_bundle,
    verify_run_bundle,
)
from arxiv_int.evaluation.eval_errors import (
    MissingEvidenceError,
    ProofExistsError,
    ProofUnknownCapabilityError,
)
from arxiv_int.evaluation.evaluate_run import EvaluateRequest, run_evaluate
from arxiv_int.evaluation.export_errors import (
    ExportCollisionError,
    ExportError,
    ExportLeakError,
    ExportUnsupportedError,
)
from arxiv_int.evaluation.exporter import (
    ExportMapping,
    ExportRequest,
    PublishedExport,
    export_proof_bundle,
)
from arxiv_int.evaluation.linkage import LinkageLabel, LinkageMetrics, score_linkage
from arxiv_int.evaluation.metrics import ExtractionMetrics, extraction_metrics, text_metrics
from arxiv_int.evaluation.paired import (
    PairedComparison,
    PairedVerdict,
    paired_comparison,
    paired_verdict,
)
from arxiv_int.evaluation.stage import EvaluateStage

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
