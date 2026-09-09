"""Data Contract CLI exporters used as the first generation path."""

import pathlib
import subprocess

from arxiv_int.contracts.generate.normalize import normalize_json, normalize_text
from arxiv_int.contracts.lint.datacontract import datacontract_command

_JSON_FORMATS = frozenset({"avro", "jsonschema"})


def export_with_datacontract(
    contract_path: pathlib.Path,
    *,
    fmt: str,
    dialect: str | None = None,
) -> str:
    """Export one ODCS file through Data Contract CLI and normalize the result."""
    command = datacontract_command()
    if command is None:
        raise RuntimeError(
            "Data Contract CLI is unavailable; install datacontract-cli or provide uv"
        )
    argv = [*command, "export", fmt, str(contract_path)]
    if fmt == "sql" and dialect:
        argv.extend(["--dialect", dialect])
    completed = subprocess.run(argv, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stdout or completed.stderr or "export failed").strip()
        raise RuntimeError(f"datacontract export {fmt} failed for {contract_path.name}: {detail}")
    raw = completed.stdout or ""
    if fmt in _JSON_FORMATS:
        import json

        return normalize_json(json.loads(raw))
    return normalize_text(raw)
