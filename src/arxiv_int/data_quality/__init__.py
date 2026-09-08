"""Contract-derived dataset quality checks and typed validation results.

Optional Pandera/Polars/PyArrow imports stay behind feature guards so CLI and
core paths that do not validate data never import them.
"""

from arxiv_int.data_quality.engine.model import (
    CheckResult,
    DatasetValidationResult,
    DbtEvidence,
    QualityRule,
    RuleCatalog,
    ValidationLimits,
)
from arxiv_int.data_quality.engine.results import is_publishable
from arxiv_int.data_quality.generate import catalog_document, compile_catalogs, quality_artifacts
from arxiv_int.data_quality.rules import UnsupportedQualityMappingError, compile_rule_catalog

__all__ = [
    "CheckResult",
    "DatasetValidationResult",
    "DbtEvidence",
    "QualityRule",
    "RuleCatalog",
    "UnsupportedQualityMappingError",
    "ValidationLimits",
    "catalog_document",
    "compile_catalogs",
    "compile_rule_catalog",
    "is_publishable",
    "quality_artifacts",
]
