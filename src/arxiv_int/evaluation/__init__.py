"""Dependency-free evaluation primitives and immutable evidence bundles."""

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
from arxiv_int.evaluation.linkage import LinkageLabel, LinkageMetrics, score_linkage
from arxiv_int.evaluation.metrics import ExtractionMetrics, extraction_metrics, text_metrics
from arxiv_int.evaluation.paired import (
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
