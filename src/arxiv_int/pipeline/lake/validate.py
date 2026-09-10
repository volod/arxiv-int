"""Contract-derived Pandera validation for bounded normalized-lake batches."""

import json
import re
from pathlib import Path
from typing import Any

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.sqlalchemy import load_schema_model
from arxiv_int.data_quality.engine.batch_eval import check_batch_rule
from arxiv_int.data_quality.engine.model import KIND_UNIQUE, SCOPE_SNAPSHOT, ValidationLimits
from arxiv_int.data_quality.rules import compile_rule_catalog
from arxiv_int.data_quality.rules.pandera_schema import schema_for
from arxiv_int.features import require_module
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.resources.paths import contracts_root


class ContractBatchValidator:
    """Compile one generated contract and validate each materialized Arrow batch."""

    def __init__(self, project_root: Path, contract_id: str) -> None:
        root = contracts_root(project_root)
        registry = FileRegistry(root)
        model = load_schema_model(registry)
        table = next(item for item in model.tables if item.contract_id == contract_id)
        self.contract_id = contract_id
        self.catalog = compile_rule_catalog(table, model.tables, registry.load_odcs(contract_id))
        self.schema = schema_for(self.catalog)
        self.fingerprint = hash_file(root / f"generated/quality/{contract_id}.rules.json")[0]
        self.arrow = require_module("pyarrow")
        self.polars = require_module("polars")
        spec = json.loads(
            (root / f"generated/parquet/{contract_id}.parquet.json").read_text(encoding="utf-8")
        )
        fields = [
            self.arrow.field(
                field["name"],
                arrow_type(self.arrow, field["arrowType"]),
                nullable=field["nullable"],
            )
            for field in spec["fields"]
        ]
        fields.append(self.arrow.field(spec["partitionKey"], self.arrow.string(), nullable=False))
        self.arrow_schema = self.arrow.schema(fields)

    def batch(self, rows: list[dict[str, object]]) -> Any:
        """Return an Arrow table only after generated schema and batch rules pass."""
        table = self.arrow.Table.from_pylist(rows, schema=self.arrow_schema)
        frame = self.polars.from_arrow(table)
        self.schema.validate(frame, lazy=True)
        for rule in self.catalog.rules:
            if rule.scope != "batch":
                continue
            result = check_batch_rule(rule, frame, ValidationLimits())
            if result.status != "pass":
                raise ValueError(f"{self.contract_id} contract check failed: {rule.rule_id}")
        return table


class SnapshotValidator:
    """One validator per emitted contract plus a combined generated-catalog identity."""

    def __init__(self, project_root: Path, contracts: tuple[str, ...]) -> None:
        self.validators = {
            contract: ContractBatchValidator(project_root, contract) for contract in contracts
        }
        self.fingerprint = hash_file(contracts_root(project_root) / "generated/manifest.json")[0]

    def __getitem__(self, contract: str) -> ContractBatchValidator:
        return self.validators[contract]

    def check_identities(self, contract: str, root: Path) -> None:
        """Refuse a snapshot whose primary keys collide across published batches."""
        files = sorted(root.glob("part-*.parquet"))
        if not files:
            return
        columns = [
            rule.column
            for rule in self[contract].catalog.rules
            if rule.kind == KIND_UNIQUE and rule.scope == SCOPE_SNAPSHOT and rule.column is not None
        ]
        if not columns:
            return
        polars = require_module("polars")
        frame = polars.scan_parquet([str(path) for path in files])
        for column in columns:
            duplicates = (
                frame.group_by(column)
                .len()
                .filter(polars.col("len") > 1)
                .collect(engine="streaming")
            )
            if duplicates.height:
                raise ValueError(
                    f"{contract} identity collision: {duplicates.height} duplicate {column} value(s)"
                )


_DECIMAL = re.compile(r"^decimal128\((\d+), (\d+)\)$")


def arrow_type(arrow: Any, name: str) -> Any:
    """Map one generated Arrow type name onto its PyArrow type."""
    decimal = _DECIMAL.match(name)
    if decimal is not None:
        return arrow.decimal128(int(decimal.group(1)), int(decimal.group(2)))
    try:
        return {
            "string": arrow.string,
            "int64": arrow.int64,
            "float64": arrow.float64,
            "bool": arrow.bool_,
        }[name]()
    except KeyError as error:
        raise ValueError(f"unsupported normalized-lake Arrow type: {name}") from error
