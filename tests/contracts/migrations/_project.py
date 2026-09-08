"""Build a disposable project tree holding contracts and an owned script directory."""

import shutil
from pathlib import Path

from arxiv_int.contracts.migrations.paths import script_location, versions_dir
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.resources.paths import contracts_root


def product_root() -> Path:
    """Return the checked-out repository root."""
    return discover_project_root(Path(__file__))


def disposable_project(destination: Path, *, contracts: bool = True) -> Path:
    """Copy contracts and the Alembic environment into a writable project tree."""
    if contracts:
        shutil.copytree(contracts_root(), destination / "contracts")
    source = script_location(product_root())
    target = script_location(destination)
    target.mkdir(parents=True, exist_ok=True)
    for name in ("env.py", "script.py.mako", "__init__.py"):
        shutil.copy2(source / name, target / name)
    versions = versions_dir(destination)
    versions.mkdir(parents=True, exist_ok=True)
    shutil.copy2(versions_dir(product_root()) / "__init__.py", versions / "__init__.py")
    return destination
