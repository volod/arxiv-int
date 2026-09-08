"""Asset edits must invalidate their producers and consumers, preserving other work."""

import shutil
from pathlib import Path

import pytest

from arxiv_int.pipeline.dag.actions import fixture_plan
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.run.fixtures import FIXTURE_PROFILE_STAGES, fixture_registry
from arxiv_int.resources.paths import contracts_root
from tests.pipeline.conftest import make_context


@pytest.mark.parametrize(
    "asset",
    ("datasets/documents.odcs.yaml", "generated/quality/documents.rules.json"),
)
def test_asset_edit_recomputes_only_owning_branch(tmp_path: Path, asset: str) -> None:
    context = make_context(tmp_path)
    overlay = context.project_root / "contracts"
    shutil.copytree(contracts_root(), overlay)
    registry, runners = fixture_registry(validators=("documents",))
    plan = fixture_plan(registry, profile_stages=FIXTURE_PROFILE_STAGES)
    orchestrator = Orchestrator(registry, context.runs_dir)
    first = orchestrator.execute_plan(context, plan)
    assert not first.halted
    assert all(item.cache_hit for item in orchestrator.execute_plan(context, plan).executions)
    path = overlay / asset
    path.write_text(path.read_text() + "\n")
    changed = orchestrator.execute_plan(context, plan)
    assert [item.cache_hit for item in changed.executions] == [True, False, False]
    assert [runners[name].calls for name in FIXTURE_PROFILE_STAGES] == [1, 2, 2]


@pytest.mark.parametrize(
    "asset,field",
    (
        ("models/staging/stg_documents.sql", "dbt_model_fingerprint"),
        ("models/staging/_staging.yml", "dbt_input_fingerprint"),
        ("tests/assert_requested_failure.sql", "dbt_rule_fingerprint"),
    ),
)
def test_dbt_edits_and_stale_closure(tmp_path: Path, asset: str, field: str) -> None:
    from dataclasses import replace

    from arxiv_int.pipeline.control.fingerprints import reuse_key
    from arxiv_int.pipeline.control.lineage import (
        LineageEdge,
        keys_matching_owned_change,
        stale_closure,
    )
    from arxiv_int.pipeline.dag.execute import stage_identity
    from arxiv_int.pipeline.dag.registry import StageRegistry
    from arxiv_int.resources.paths import dbt_project_root

    context = make_context(tmp_path)
    overlay = context.project_root / "dbt"
    shutil.copytree(dbt_project_root(), overlay)
    base, runners = fixture_registry()
    beta = replace(
        base.get("beta"),
        contracts=("documents",),
        dbt_select=("stg_documents",),
        dbt_models=("models/staging/stg_documents.sql",),
        dbt_inputs=("models/staging/_staging.yml",),
        dbt_rules=("tests/assert_requested_failure.sql",),
    )
    registry = StageRegistry([beta if spec.name == "beta" else spec for spec in base.specs()])
    plan = fixture_plan(registry, profile_stages=FIXTURE_PROFILE_STAGES)
    orchestrator = Orchestrator(registry, context.runs_dir)
    first = orchestrator.execute_plan(context, plan)
    identity_context = replace(context, parameters={"document_id": first.executions[0].shard_id})
    identities = {}
    keys = []
    for name in FIXTURE_PROFILE_STAGES:
        identity = stage_identity(registry.get(name), identity_context, tuple(keys[-1:]))
        key = reuse_key(identity)
        identities[key] = identity
        keys.append(key)
    assert keys == [item.reuse_key for item in first.executions]
    path = overlay / asset
    path.write_text(path.read_text() + "\n")
    second = orchestrator.execute_plan(context, plan)
    assert [item.cache_hit for item in second.executions] == [True, False, False]
    roots = keys_matching_owned_change(identities, field, identities[keys[1]].owned[field])
    assert roots == {keys[1]}
    assert stale_closure(roots, [LineageEdge(*keys[:2]), LineageEdge(*keys[1:])]) == set(keys[1:])
    assert all(item.cache_hit for item in orchestrator.execute_plan(context, plan).executions)
    assert [runners[name].calls for name in FIXTURE_PROFILE_STAGES] == [1, 2, 2]


@pytest.mark.parametrize("declaration", ("tools", "models", "prompts"))
def test_declared_values_only_invalidate_their_branch(tmp_path: Path, declaration: str) -> None:
    from dataclasses import replace

    from arxiv_int.pipeline.dag.registry import StageRegistry

    context = make_context(tmp_path)
    registry, runners = fixture_registry()
    plan = fixture_plan(registry, profile_stages=FIXTURE_PROFILE_STAGES)
    first = Orchestrator(registry, context.runs_dir).execute_plan(context, plan)
    assert not first.halted
    changed = StageRegistry(
        [
            replace(spec, **{declaration: {"fixture": "sha256:changed"}})
            if spec.name == "beta"
            else spec
            for spec in registry.specs()
        ]
    )
    orchestrator = Orchestrator(changed, context.runs_dir)
    second = orchestrator.execute_plan(context, plan)
    assert [item.cache_hit for item in second.executions] == [True, False, False]
    assert all(item.cache_hit for item in orchestrator.execute_plan(context, plan).executions)
    assert [runners[name].calls for name in FIXTURE_PROFILE_STAGES] == [1, 2, 2]


def test_missing_asset_cannot_reuse_accepted_work(tmp_path: Path) -> None:
    context = make_context(tmp_path)
    overlay = context.project_root / "contracts"
    shutil.copytree(contracts_root(), overlay)
    registry, runners = fixture_registry(validators=("documents",))
    plan = fixture_plan(registry, profile_stages=FIXTURE_PROFILE_STAGES)
    orchestrator = Orchestrator(registry, context.runs_dir)
    assert not orchestrator.execute_plan(context, plan).halted
    (overlay / "generated/quality/documents.rules.json").unlink()
    with pytest.raises(ValueError, match="missing stage asset"):
        orchestrator.execute_plan(context, plan)
    assert [runners[name].calls for name in FIXTURE_PROFILE_STAGES] == [1, 1, 1]
