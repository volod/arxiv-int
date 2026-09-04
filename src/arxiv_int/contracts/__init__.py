"""Dependency-light primitives for contract registries and governance."""

from arxiv_int.contracts.canonical import (
    CanonicalField,
    CanonicalModel,
    SemanticTerm,
    load_canonical_model,
)
from arxiv_int.contracts.evolution import (
    CHANGE_ADDITIVE,
    CHANGE_BREAKING,
    CHANGE_IDENTICAL,
    ChangeReport,
    classify_change,
    freeze_baseline,
    schema_snapshot,
    version_policy_errors,
)
from arxiv_int.contracts.fingerprint import semantic_metadata_hash
from arxiv_int.contracts.generate import ContractGenerator, generate_registered
from arxiv_int.contracts.registry import ContractEntry, FileRegistry

__all__ = [
    "CHANGE_ADDITIVE",
    "CHANGE_BREAKING",
    "CHANGE_IDENTICAL",
    "CanonicalField",
    "CanonicalModel",
    "ChangeReport",
    "ContractEntry",
    "ContractGenerator",
    "FileRegistry",
    "SemanticTerm",
    "classify_change",
    "freeze_baseline",
    "generate_registered",
    "load_canonical_model",
    "schema_snapshot",
    "semantic_metadata_hash",
    "version_policy_errors",
]
