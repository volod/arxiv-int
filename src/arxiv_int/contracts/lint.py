"""Orchestrate ODCS schema, integrity, and Data Contract CLI lint checks."""

import logging
import pathlib
from dataclasses import dataclass

from arxiv_int.contracts.datacontract_lint import lint_with_datacontract
from arxiv_int.contracts.integrity import validate_registry_integrity
from arxiv_int.contracts.schema_lint import odcs_schema_path, validate_dataset_files
from arxiv_int.runtime.project_root import find_project_root

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContractLintReport:
    """Collected findings from one contracts lint run."""

    findings: tuple[str, ...]
    checked_datasets: int
    datacontract_ran: bool

    @property
    def ok(self) -> bool:
        return not self.findings


def contracts_root_for(project_root: pathlib.Path | None = None) -> pathlib.Path:
    """Return the product contracts root under the project checkout."""
    root = project_root or find_project_root()
    return root / "contracts"


def lint_contracts(
    contracts_root: pathlib.Path,
    *,
    run_datacontract: bool = True,
) -> ContractLintReport:
    """Lint the product registry with official schema and integrity checks."""
    findings = list(validate_dataset_files(contracts_root))
    findings.extend(validate_registry_integrity(contracts_root))
    dataset_files = sorted((contracts_root / "datasets").glob("*.odcs.yaml"))
    datacontract_ran = False
    if run_datacontract and not findings:
        try:
            findings.extend(
                lint_with_datacontract(
                    dataset_files,
                    json_schema=odcs_schema_path(contracts_root),
                )
            )
            datacontract_ran = True
        except RuntimeError as error:
            findings.append(str(error))
    for finding in findings:
        _LOG.error("%s", finding)
    return ContractLintReport(
        findings=tuple(findings),
        checked_datasets=len(dataset_files),
        datacontract_ran=datacontract_ran,
    )
