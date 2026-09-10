"""Reusable evaluation metrics and immutable result bundles."""

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
from arxiv_int.evaluation.scoring.errors import MissingEvidenceError
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
    "ExtractionMetrics",
    "LinkageLabel",
    "LinkageMetrics",
    "MissingEvidenceError",
    "PairedComparison",
    "PairedVerdict",
    "PublishedBundle",
    "extraction_metrics",
    "paired_comparison",
    "paired_verdict",
    "publish_run_bundle",
    "score_linkage",
    "text_metrics",
    "verify_run_bundle",
]
