"""Data Contract CLI breaking-check wrapper."""

import pathlib
import subprocess

from arxiv_int.contracts.datacontract_lint import datacontract_command


def breaking_findings(baseline_odcs: pathlib.Path, current_odcs: pathlib.Path) -> list[str]:
    """Run ``datacontract breaking`` when the CLI is available.

    Returns an empty list when contracts are compatible or the CLI is unavailable.
    """
    command = datacontract_command()
    if command is None:
        return []
    completed = subprocess.run(
        [*command, "breaking", str(baseline_odcs), str(current_odcs)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return []
    detail = (completed.stdout or completed.stderr or "breaking check failed").strip()
    # Data Contract CLI exits non-zero for both tooling errors and real breaks.
    if "error" in detail.lower() and "incompatible" not in detail.lower():
        return [f"datacontract breaking failed for {current_odcs.name}: {detail}"]
    return [f"datacontract breaking reported changes for {current_odcs.name}: {detail}"]
