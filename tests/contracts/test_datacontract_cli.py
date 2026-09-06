"""Data Contract CLI lint integration for the product registry."""

from pathlib import Path

import pytest

pytest.importorskip("jsonschema")

from arxiv_int.contracts.datacontract_lint import (
    datacontract_command,
    lint_with_datacontract,
)
from arxiv_int.contracts.schema_lint import odcs_schema_path
from arxiv_int.quality.project_root import discover_project_root


@pytest.mark.skipif(datacontract_command() is None, reason="Data Contract CLI unavailable")
def test_datacontract_cli_lints_every_dataset() -> None:
    root = discover_project_root(Path(__file__)) / "contracts"
    files = sorted((root / "datasets").glob("*.odcs.yaml"))
    findings = lint_with_datacontract(files, json_schema=odcs_schema_path(root))
    assert findings == []
