"""Contract-derived document/span validation for bounded extraction batches."""

import json
from pathlib import Path
from typing import Any

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.sqlalchemy import load_schema_model
from arxiv_int.data_quality.engine.batch_eval import check_batch_rule
from arxiv_int.data_quality.engine.model import ValidationLimits
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
                _arrow_type(self.arrow, field["arrowType"]),
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
                raise ValueError(f"extraction contract check failed: {rule.rule_id}")
        return table


class ExtractionValidator:
    """Document and span validators with one combined quality identity."""

    def __init__(self, project_root: Path) -> None:
        self.documents = ContractBatchValidator(project_root, "documents")
        self.spans = ContractBatchValidator(project_root, "spans")
        self.fingerprint = hash_file(contracts_root(project_root) / "generated/manifest.json")[0]


def _arrow_type(arrow: Any, name: str) -> Any:
    try:
        return {
            "string": arrow.string,
            "int64": arrow.int64,
            "float64": arrow.float64,
            "boolean": arrow.bool_,
        }[name]()
    except KeyError as error:
        raise ValueError(f"unsupported extraction Arrow type: {name}") from error
