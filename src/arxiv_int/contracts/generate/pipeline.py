"""Orchestrate deterministic multi-format contract generation and drift checks."""

import logging
import pathlib
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.generate.adapters import (
    graph_extension_sql,
    parquet_descriptor,
    postgres_extension_sql,
    provenance_sidecar,
    search_extension_sql,
    vector_extension_sql,
)
from arxiv_int.contracts.generate.export import export_with_datacontract
from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.contracts.sqlalchemy.ddl import baseline_ddl, contract_ddl
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel, load_schema_model

_LOG = logging.getLogger(__name__)

GENERATOR_VERSION = "2.1.0"
_CLI_FORMATS = (
    ("avro", "avro", ".avsc", None),
    ("jsonschema", "jsonschema", ".schema.json", None),
    ("pydantic", "pydantic-model", ".py", None),
)
BASELINE_DDL_RELATIVE = "postgres/baseline.sql"


@dataclass(frozen=True)
class GenerationResult:
    """Outcome of generating or checking the contracts/generated tree."""

    root: pathlib.Path
    files: tuple[pathlib.Path, ...]
    manifest_fingerprint: str


def _write(path: pathlib.Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    return sha256_text(path.read_text(encoding="utf-8"))


def _contract_artifacts(
    registry: FileRegistry,
    contract_id: str,
    contracts_root: pathlib.Path,
    output_root: pathlib.Path,
    model: ContractSchemaModel,
) -> dict[str, str]:
    entry = registry.get_entry(contract_id)
    odcs_path = contracts_root / entry.odcs_ref
    odcs = registry.load_odcs(contract_id)
    fingerprints: dict[str, str] = {}
    for folder, fmt, suffix, dialect in _CLI_FORMATS:
        exported = export_with_datacontract(odcs_path, fmt=fmt, dialect=dialect)
        relative = f"{folder}/{contract_id}{suffix}"
        fingerprints[relative] = _write(output_root / relative, exported)

    relative = f"postgres/{contract_id}.sql"
    fingerprints[relative] = _write(
        output_root / relative, contract_ddl(model.metadata, model.by_contract(contract_id))
    )

    relative = f"parquet/{contract_id}.parquet.json"
    fingerprints[relative] = _write(output_root / relative, parquet_descriptor(odcs, contract_id))

    relative = f"postgres/extensions/{contract_id}.sql"
    fingerprints[relative] = _write(
        output_root / relative, postgres_extension_sql(odcs, contract_id)
    )

    search_sql = search_extension_sql(odcs, contract_id)
    if search_sql is not None:
        relative = f"search/{contract_id}.sql"
        fingerprints[relative] = _write(output_root / relative, search_sql)

    vector_sql = vector_extension_sql(odcs, contract_id)
    if vector_sql is not None:
        relative = f"postgres/extensions/{contract_id}.vector.sql"
        fingerprints[relative] = _write(output_root / relative, vector_sql)

    graph_sql = graph_extension_sql(odcs, contract_id)
    if graph_sql is not None:
        relative = f"graph/{contract_id}.sql"
        fingerprints[relative] = _write(output_root / relative, graph_sql)

    from arxiv_int.data_quality.generate import catalog_document
    from arxiv_int.data_quality.generate.dbt_yaml import render_contract_dbt_yaml
    from arxiv_int.data_quality.rules import compile_rule_catalog

    catalog = compile_rule_catalog(model.by_contract(contract_id), model.tables, odcs)
    relative = f"quality/{contract_id}.rules.json"
    fingerprints[relative] = _write(
        output_root / relative, normalize_json(catalog_document(catalog))
    )
    relative = f"dbt/{contract_id}.yml"
    fingerprints[relative] = _write(output_root / relative, render_contract_dbt_yaml(catalog))

    semantic_hash = entry.stored_semantic_hash
    if entry.mapping_ref is not None and semantic_hash is None:
        semantic_hash = registry.semantic_fingerprint(contract_id)
    relative = f"provenance/{contract_id}.json"
    fingerprints[relative] = _write(
        output_root / relative,
        provenance_sidecar(
            odcs,
            contract_id,
            semantic_hash=semantic_hash,
            artifact_fingerprints=fingerprints,
        ),
    )
    return fingerprints


def _write_manifest(
    output_root: pathlib.Path,
    by_contract: dict[str, dict[str, str]],
    shared: dict[str, str],
) -> str:
    files = {
        path: digest for artifacts in by_contract.values() for path, digest in artifacts.items()
    }
    files.update(shared)
    manifest: dict[str, Any] = {
        "generatorVersion": GENERATOR_VERSION,
        "shared": dict(sorted(shared.items())),
        "contracts": {
            contract_id: dict(sorted(artifacts.items()))
            for contract_id, artifacts in sorted(by_contract.items())
        },
        "files": dict(sorted(files.items())),
    }
    text = normalize_json(manifest)
    path = output_root / "manifest.json"
    path.write_text(text, encoding="utf-8")
    return sha256_text(text)


def generate_all_contracts(
    contracts_root: pathlib.Path,
    output_root: pathlib.Path | None = None,
) -> GenerationResult:
    """Generate all committed physical artifacts under contracts/generated."""
    registry = FileRegistry(contracts_root)
    destination = output_root or (contracts_root / "generated")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    model = load_schema_model(registry)
    odcs_by_contract = {
        contract_id: registry.load_odcs(contract_id) for contract_id in registry.contract_ids()
    }
    by_contract: dict[str, dict[str, str]] = {}
    for contract_id in registry.contract_ids():
        _LOG.info("generating artifacts for %s", contract_id)
        by_contract[contract_id] = _contract_artifacts(
            registry, contract_id, contracts_root, destination, model
        )
    from arxiv_int.data_quality.generate import DBT_SOURCES_RELATIVE, compile_catalogs
    from arxiv_int.data_quality.generate.dbt_yaml import render_dbt_yaml

    catalogs = compile_catalogs(model, odcs_by_contract)
    shared = {
        BASELINE_DDL_RELATIVE: _write(
            destination / BASELINE_DDL_RELATIVE, baseline_ddl(model.metadata)
        ),
        DBT_SOURCES_RELATIVE: _write(destination / DBT_SOURCES_RELATIVE, render_dbt_yaml(catalogs)),
    }
    manifest_fingerprint = _write_manifest(destination, by_contract, shared)
    files = tuple(sorted(path for path in destination.rglob("*") if path.is_file()))
    return GenerationResult(destination, files, manifest_fingerprint)


def _file_map(root: pathlib.Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            mapping[relative] = path.read_text(encoding="utf-8")
    return mapping


def check_generation_drift(contracts_root: pathlib.Path) -> list[str]:
    """Regenerate into a temp directory and report drift against committed outputs."""
    committed = contracts_root / "generated"
    if not committed.is_dir():
        return ["committed contracts/generated tree is missing; run make contracts-gen"]
    with tempfile.TemporaryDirectory(prefix="arxiv-int-contracts-gen-") as tmp:
        generated = generate_all_contracts(contracts_root, pathlib.Path(tmp) / "generated")
        left = _file_map(committed)
        right = _file_map(generated.root)
    findings: list[str] = []
    for name in sorted(set(left) | set(right)):
        if name not in left:
            findings.append(f"generated artifact missing from commit: {name}")
        elif name not in right:
            findings.append(f"committed artifact missing from regeneration: {name}")
        elif left[name] != right[name]:
            findings.append(f"artifact drift: {name}")
    return findings
