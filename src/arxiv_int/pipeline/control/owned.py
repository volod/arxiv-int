"""Bind the existing owned identity fields to stage-declared packaged assets."""

import inspect
from dataclasses import asdict
from pathlib import Path
from typing import Any

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.control.asset_hashes import (
    PACKAGE_ROOT,
    digest_value,
    file_hashes,
)
from arxiv_int.pipeline.control.dbt_assets import generated_dbt_inputs
from arxiv_int.pipeline.control.dependency_assets import dependency_assets
from arxiv_int.pipeline.dag.registry import StageSpec
from arxiv_int.resources.paths import contracts_root, dbt_project_root

_SHARED_CODE = (
    "pipeline/control",
    "pipeline/dag",
    "pipeline/run",
    "pipeline/quality",
    "interfaces",
)
_DECLARATIONS = frozenset({"pipeline/dag/stages.py", "pipeline/run/fixtures.py"})
_SCHEMA_KINDS = {
    "jsonschema": ".schema.json",
    "parquet": ".parquet.json",
    "avro": ".avsc",
    "postgres": ".sql",
    "postgres/extensions": ".sql",
    "pydantic": ".py",
}


def owned_fingerprints(
    spec: StageSpec, project_root: Path, configuration_fingerprint: str
) -> dict[str, str]:
    """Read current assets on every lookup, including zero-worker cache checks."""
    sources = owned_sources(spec, project_root)
    values = {field: digest_value(spec.name, field, value) for field, value in sources.items()}
    values["configuration_fingerprint"] = configuration_fingerprint
    return values


def owned_sources(spec: StageSpec, project_root: Path) -> dict[str, Any]:
    """Return reproducible relative asset names/digests and declared values, without secrets."""
    contract, schema, validation = _contract_assets(spec, contracts_root(project_root))
    dbt_root = dbt_project_root(project_root)
    code = {
        path: digest
        for path, digest in file_hashes(PACKAGE_ROOT, _SHARED_CODE).items()
        if path not in _DECLARATIONS
    }
    code.update(file_hashes(PACKAGE_ROOT, spec.code_paths))
    if spec.runner is not None:
        runner_type = type(spec.runner)
        source = inspect.getsourcefile(runner_type)
        if source is None:
            raise ValueError("stage runner source is unavailable for fingerprinting")
        code[f"runner:{runner_type.__module__}.{runner_type.__qualname__}"] = hash_file(
            Path(source)
        )[0]
    shared_dbt = ("dbt_project.yml", "macros") if spec.dbt_models else ()
    dbt_contracts = _dbt_contracts(spec, contracts_root(project_root))
    return {
        "code_fingerprint": code,
        "dependency_fingerprint": dependency_assets(project_root, _dependencies(spec)),
        "contract_fingerprint": contract,
        "schema_fingerprint": schema,
        "tool_fingerprint": dict(spec.tools),
        "model_fingerprint": dict(spec.models),
        "prompt_fingerprint": dict(spec.prompts),
        "validation_catalog_fingerprint": validation,
        "dbt_model_fingerprint": file_hashes(dbt_root, (*shared_dbt, *spec.dbt_models)),
        "dbt_input_fingerprint": {
            "select": spec.dbt_select,
            "assets": file_hashes(dbt_root, spec.dbt_inputs),
            "sources": dbt_contracts,
        },
        "dbt_rule_fingerprint": {
            "assets": file_hashes(dbt_root, spec.dbt_rules),
            "sources": dbt_contracts,
        },
    }


def _contract_assets(
    spec: StageSpec, root: Path
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    ids = sorted(set((*spec.contracts, *spec.validators)))
    if not ids:
        return {}, {}, {}
    registry = FileRegistry(root)
    contracts: dict[str, Any] = {}
    schemas: list[str] = []
    for contract_id in ids:
        try:
            entry = registry.get_entry(contract_id)
        except KeyError as error:
            raise ValueError(f"unknown stage contract: {contract_id}") from error
        refs = [entry.odcs_ref]
        if entry.mapping_ref:
            refs.append(entry.mapping_ref)
        contracts[contract_id] = {"entry": asdict(entry), "assets": file_hashes(root, refs)}
        schemas.extend(
            f"generated/{kind}/{contract_id}{suffix}" for kind, suffix in _SCHEMA_KINDS.items()
        )
    validation: dict[str, Any] = {
        "catalogs": file_hashes(
            root, [f"generated/quality/{name}.rules.json" for name in spec.validators]
        ),
        "engine": file_hashes(PACKAGE_ROOT, ("data_quality/engine",)) if spec.validators else {},
    }
    return contracts, file_hashes(root, schemas), validation


def _dbt_contracts(spec: StageSpec, root: Path) -> dict[str, Any]:
    """Bind generated source/column/test declarations for explicitly consumed contracts."""
    if not spec.dbt_models:
        return {}
    return generated_dbt_inputs(root, (*spec.contracts, *spec.validators))


def _dependencies(spec: StageSpec) -> tuple[str, ...]:
    names = ("pyyaml", *spec.dependency_packages)
    if spec.validators:
        names += ("pandera", "polars")
    if spec.dbt_models:
        names += ("dbt-core", "dbt-postgres")
    return names
