"""Secret-free extraction tool identities for stage reuse fingerprints."""

import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path


def extraction_tool_versions() -> dict[str, str]:
    """Return bounded package/CLI identities without importing heavy engines."""
    try:
        tika = package_version("iscc-tika")
    except PackageNotFoundError:
        tika = "unavailable"
    return {
        "iscc-tika": tika,
        "docling": _command_version((str(Path(sys.executable).with_name("docling")), "--version")),
        "tesseract": _command_version(("tesseract", "--version")),
        "tesseract-languages": _tesseract_languages(),
    }


def _command_version(command: tuple[str, ...]) -> str:
    if shutil.which(command[0]) is None:
        return "unavailable"
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    output = result.stdout or result.stderr
    return output.decode("utf-8", errors="replace").splitlines()[0][:200] or "unknown"


def _tesseract_languages() -> str:
    if shutil.which("tesseract") is None:
        return "unavailable"
    try:
        result = subprocess.run(
            ("tesseract", "--list-langs"),
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    lines = result.stdout.decode("utf-8", errors="replace").splitlines()
    return ",".join(sorted(line.strip() for line in lines[1:] if line.strip()))[:500] or "unknown"
