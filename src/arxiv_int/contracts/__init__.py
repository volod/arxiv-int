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
    CHANGE_GRAPH_PROJECTION,
    CHANGE_IDENTICAL,
    CHANGE_REINDEX,
    CHANGE_SEMANTIC_RETARGET,
    CHANGE_VECTOR_DIMENSION,
    FIELD_IDENTITY_SCHEMA_QUALIFIED,
    ChangeReport,
    EvolutionCheckReport,
    check_evolution_policy,
    classify_change,
    classify_contract_evolution,
    freeze_baseline,
    migrate_schema_snapshot,
    schema_field_id,
    schema_identity,
    schema_snapshot,
    version_policy_errors,
)
from arxiv_int.contracts.fingerprint import semantic_metadata_hash
from arxiv_int.contracts.generate import (
    ContractGenerator,
    GenerationResult,
    check_generation_drift,
    generate_all_contracts,
    generate_registered,
)
from arxiv_int.contracts.paths import resolve_rooted_reference
from arxiv_int.contracts.registry import ContractEntry, FileRegistry

__all__ = [
    "CHANGE_ADDITIVE",
    "CHANGE_BREAKING",
    "CHANGE_GRAPH_PROJECTION",
    "CHANGE_IDENTICAL",
    "CHANGE_REINDEX",
    "CHANGE_SEMANTIC_RETARGET",
    "CHANGE_VECTOR_DIMENSION",
    "FIELD_IDENTITY_SCHEMA_QUALIFIED",
    "CanonicalField",
    "CanonicalModel",
    "ChangeReport",
    "ContractEntry",
    "ContractGenerator",
    "EvolutionCheckReport",
    "FileRegistry",
    "GenerationResult",
    "SemanticTerm",
    "check_evolution_policy",
    "check_generation_drift",
    "classify_change",
    "classify_contract_evolution",
    "freeze_baseline",
    "generate_all_contracts",
    "generate_registered",
    "load_canonical_model",
    "migrate_schema_snapshot",
    "resolve_rooted_reference",
    "schema_field_id",
    "schema_identity",
    "schema_snapshot",
    "semantic_metadata_hash",
    "version_policy_errors",
]
