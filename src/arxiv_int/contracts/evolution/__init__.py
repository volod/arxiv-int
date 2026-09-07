"""Schema evolution baselines, policy classification, and migration checks."""

from arxiv_int.contracts.evolution.baseline import (
    build_reviewed_snapshot,
    freeze_all_baselines,
    freeze_contract_baseline,
)
from arxiv_int.contracts.evolution.check import (
    EvolutionCheckReport,
    check_evolution_policy,
    compare_fixture_pair,
)
from arxiv_int.contracts.evolution.core import (
    CHANGE_ADDITIVE,
    CHANGE_BREAKING,
    CHANGE_GRAPH_PROJECTION,
    CHANGE_IDENTICAL,
    CHANGE_REINDEX,
    CHANGE_SEMANTIC_RETARGET,
    CHANGE_VECTOR_DIMENSION,
    FIELD_IDENTITY_SCHEMA_QUALIFIED,
    ChangeReport,
    baseline_history,
    classify_change,
    freeze_baseline,
    migrate_schema_snapshot,
    schema_field_id,
    schema_identity,
    schema_snapshot,
    version_policy_errors,
)
from arxiv_int.contracts.evolution.migrations import (
    migration_policy_findings,
    migration_report,
)
from arxiv_int.contracts.evolution.policy import (
    classify_contract_evolution,
    classify_projection_change,
    classify_semantic_change,
    merge_change_reports,
    projection_snapshot,
)

__all__ = [
    "CHANGE_ADDITIVE",
    "CHANGE_BREAKING",
    "CHANGE_GRAPH_PROJECTION",
    "CHANGE_IDENTICAL",
    "CHANGE_REINDEX",
    "CHANGE_SEMANTIC_RETARGET",
    "CHANGE_VECTOR_DIMENSION",
    "FIELD_IDENTITY_SCHEMA_QUALIFIED",
    "ChangeReport",
    "EvolutionCheckReport",
    "baseline_history",
    "build_reviewed_snapshot",
    "check_evolution_policy",
    "classify_change",
    "classify_contract_evolution",
    "classify_projection_change",
    "classify_semantic_change",
    "compare_fixture_pair",
    "freeze_all_baselines",
    "freeze_baseline",
    "freeze_contract_baseline",
    "merge_change_reports",
    "migrate_schema_snapshot",
    "migration_policy_findings",
    "migration_report",
    "projection_snapshot",
    "schema_field_id",
    "schema_identity",
    "schema_snapshot",
    "version_policy_errors",
]
