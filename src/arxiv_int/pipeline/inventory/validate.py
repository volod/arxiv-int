"""Contract-derived batch validation plus stricter inventory provenance invariants."""

import json
import re
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
from arxiv_int.pipeline.inventory.model import Observation
from arxiv_int.resources.paths import contracts_root


class InventoryValidator:
    """Compile the canonical contract once, then validate bounded materialized batches."""

    def __init__(self, project_root: Path) -> None:
        root = contracts_root(project_root)
        registry = FileRegistry(root)
        model = load_schema_model(registry)
        table = next(item for item in model.tables if item.contract_id == "source-occurrences")
        self.catalog = compile_rule_catalog(
            table, model.tables, registry.load_odcs("source-occurrences")
        )
        self.schema = schema_for(self.catalog)
        self.fingerprint = hash_file(root / "generated/quality/source-occurrences.rules.json")[0]
        self.arrow = require_module("pyarrow")
        self.polars = require_module("polars")
        spec = json.loads((root / "generated/parquet/source-occurrences.parquet.json").read_text())
        spec["fields"].append({"name": spec["partitionKey"], "nullable": False})
        self.arrow_schema = self.arrow.schema(
            [
                self.arrow.field(field["name"], self.arrow.string(), nullable=field["nullable"])
                for field in spec["fields"]
            ]
        )

    def batch(
        self, items: list[Observation], scan: str, generation: str, silos: frozenset[str]
    ) -> Any:
        """Return an Arrow table only after schema, rules and provenance actually pass."""
        for item in items:
            _provenance(item, silos)
        rows = [item.contract_row(scan, generation) for item in items]
        table = self.arrow.Table.from_pylist(rows, schema=self.arrow_schema)
        frame = self.polars.from_arrow(table)
        self.schema.validate(frame, lazy=True)
        for rule in self.catalog.rules:
            if rule.scope == "batch":
                result = check_batch_rule(rule, frame, ValidationLimits())
                if result.status != "pass":
                    raise ValueError(f"inventory contract check failed: {rule.rule_id}")
        return table


def _provenance(item: Observation, silos: frozenset[str]) -> None:
    path = Path(item.relative_path)
    if (
        item.silo_id not in silos
        or not item.relative_path
        or path.is_absolute()
        or ".." in path.parts
        or item.size < 0
        or item.status not in {"ready", "quarantined"}
    ):
        raise ValueError("invalid inventory provenance")
    if item.content_hash is not None and re.fullmatch("[0-9a-f]{64}", item.content_hash) is None:
        raise ValueError("invalid inventory content identity")
    if item.status == "ready" and not item.content_hash:
        raise ValueError("readable inventory occurrence is missing a strong hash")
    if item.status == "quarantined" and not item.reason:
        raise ValueError("quarantined inventory occurrence is missing its reason")
    if item.members and not item.parent_hash and item.members[-1] != "!policy":
        raise ValueError("archive member is missing its parent content identity")
