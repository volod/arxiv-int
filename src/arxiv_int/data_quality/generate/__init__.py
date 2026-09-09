"""Generate committed quality catalogs and dbt YAML from normalized contracts."""

import json
from collections.abc import Mapping
from typing import Any

from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel
from arxiv_int.data_quality.engine.model import RULE_CATALOG_VERSION, RuleCatalog
from arxiv_int.data_quality.generate.dbt_yaml import render_contract_dbt_yaml, render_dbt_yaml
from arxiv_int.data_quality.rules import compile_rule_catalog

QUALITY_DIR = "quality"
DBT_DIR = "dbt"
DBT_SOURCES_RELATIVE = f"{DBT_DIR}/sources.yml"


def _normalize_json(document: Any) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _rule_json(rule: Any) -> dict[str, Any]:
    payload = {
        "acceptedValues": list(rule.accepted_values),
        "backend": rule.backend,
        "column": rule.column,
        "dbtTest": rule.dbt_test,
        "description": rule.description,
        "diskBackend": rule.disk_backend,
        "id": rule.rule_id,
        "kind": rule.kind,
        "logicalType": rule.logical_type,
        "maxLength": rule.max_length,
        "precision": rule.precision,
        "required": rule.required,
        "scale": rule.scale,
        "scope": rule.scope,
        "severity": rule.severity,
        "targetColumn": rule.target_column,
        "targetContractId": rule.target_contract_id,
        "targetSchema": rule.target_schema,
        "targetTable": rule.target_table,
        "unitColumn": rule.unit_column,
        "version": rule.version,
    }
    return {key: value for key, value in payload.items() if value not in (None, (), [])}


def catalog_document(catalog: RuleCatalog) -> dict[str, Any]:
    """Return the committed JSON document for one rule catalog."""
    return {
        "catalogVersion": catalog.catalog_version,
        "contractId": catalog.contract_id,
        "description": catalog.description,
        "odcsId": catalog.odcs_id,
        "primaryKey": list(catalog.primary_key),
        "rules": [_rule_json(rule) for rule in catalog.rules],
        "schemaName": catalog.schema_name,
        "tableName": catalog.table_name,
        "version": catalog.version,
    }


def compile_catalogs(
    model: ContractSchemaModel, odcs_by_contract: Mapping[str, dict[str, Any]]
) -> tuple[RuleCatalog, ...]:
    """Compile catalogs for every owned contract in stable order."""
    catalogs = []
    for table in sorted(model.tables, key=lambda item: item.contract_id):
        catalogs.append(
            compile_rule_catalog(table, model.tables, odcs_by_contract[table.contract_id])
        )
    return tuple(catalogs)


def quality_artifacts(
    model: ContractSchemaModel, odcs_by_contract: Mapping[str, dict[str, Any]]
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Return per-contract and shared generated quality/dbt texts."""
    catalogs = compile_catalogs(model, odcs_by_contract)
    per_contract: dict[str, dict[str, str]] = {}
    for catalog in catalogs:
        per_contract[catalog.contract_id] = {
            f"{QUALITY_DIR}/{catalog.contract_id}.rules.json": _normalize_json(
                catalog_document(catalog)
            ),
            f"{DBT_DIR}/{catalog.contract_id}.yml": render_contract_dbt_yaml(catalog),
        }
    shared = {DBT_SOURCES_RELATIVE: render_dbt_yaml(catalogs)}
    return per_contract, shared


def catalog_version() -> str:
    """Return the committed quality catalog format version."""
    return RULE_CATALOG_VERSION
