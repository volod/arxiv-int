"""Data Contract CLI lint integration for the product registry."""

import pytest

from arxiv_int.resources.paths import contracts_root

pytest.importorskip("jsonschema")

from arxiv_int.contracts.lint.datacontract import (
    datacontract_command,
    lint_with_datacontract,
)
from arxiv_int.contracts.lint.schema import odcs_schema_path


@pytest.mark.skipif(datacontract_command() is None, reason="Data Contract CLI unavailable")
def test_datacontract_cli_lints_every_dataset() -> None:
    root = contracts_root()
    files = sorted((root / "datasets").glob("*.odcs.yaml"))
    findings = lint_with_datacontract(files, json_schema=odcs_schema_path(root))
    assert findings == []
