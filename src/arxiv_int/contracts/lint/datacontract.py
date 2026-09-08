"""Invoke Data Contract CLI lint against the official ODCS schema."""

import os
import pathlib
import shutil
import subprocess
from collections.abc import Sequence

DATACONTRACT_PACKAGE = "datacontract-cli==1.1.3"


def datacontract_command() -> list[str] | None:
    """Return an argv prefix that can run ``datacontract``, if available."""
    direct = shutil.which("datacontract")
    if direct:
        return [direct]
    uv = shutil.which("uv")
    if uv is None:
        return None
    if os.environ.get("UV_OFFLINE") == "1":
        # Offline CI may lack a cached tool install; prefer an on-PATH binary.
        return None
    return [uv, "tool", "run", "--from", DATACONTRACT_PACKAGE, "datacontract"]


def lint_with_datacontract(
    contract_files: Sequence[pathlib.Path],
    *,
    json_schema: pathlib.Path,
    env: dict[str, str] | None = None,
) -> list[str]:
    """Run Data Contract CLI lint for each ODCS file.

    Returns finding strings; an empty list means every file passed. Raises
    RuntimeError when the CLI cannot be located.
    """
    command = datacontract_command()
    if command is None:
        raise RuntimeError(
            "Data Contract CLI is unavailable; install datacontract-cli or provide uv"
        )
    findings: list[str] = []
    merged = os.environ.copy()
    if env:
        merged.update(env)
    for path in contract_files:
        completed = subprocess.run(
            [*command, "lint", str(path), "--json-schema", str(json_schema), "--all-errors"],
            check=False,
            capture_output=True,
            text=True,
            env=merged,
        )
        if completed.returncode == 0:
            continue
        detail = (completed.stdout or completed.stderr or "lint failed").strip()
        findings.append(f"{path.name}: Data Contract CLI lint failed: {detail}")
    return findings
