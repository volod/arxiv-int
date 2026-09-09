"""Locate packaged configs, contracts, ontology, and dbt assets.

A wheel install has no checkout-root ``contracts/`` tree. These helpers resolve
the files shipped beside this module. Tests may pass a temporary ``project_root``
that contains overlay directories of the same names; those overlays win when
present so disposable trees keep working.
"""

from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
CONFIGS_DIRNAME = "configs"
CONTRACTS_DIRNAME = "contracts"
ONTOLOGY_DIRNAME = "ontology"
DBT_DIRNAME = "dbt"
LANGUAGE_DIRNAME = "language"


def resource_root() -> Path:
    """Return the packaged ``arxiv_int.resources`` directory."""
    return _PACKAGE_ROOT


def _overlay_or_packaged(project_root: Path | None, dirname: str) -> Path:
    if project_root is not None:
        overlay = Path(project_root) / dirname
        if overlay.is_dir():
            return overlay.resolve()
    return (_PACKAGE_ROOT / dirname).resolve()


def output_root(project_root: Path, dirname: str) -> Path:
    """Return where generated files for ``dirname`` should be written.

    An existing overlay wins. A checkout with packaged assets writes into the
    package. Any other ``project_root`` (disposable trees) gets
    ``<project_root>/<dirname>`` so generate/check pairs stay local and cannot
    mutate packaged sources.
    """
    overlay = Path(project_root) / dirname
    if overlay.is_dir():
        return overlay.resolve()
    packaged = (_PACKAGE_ROOT / dirname).resolve()
    if (Path(project_root) / "pyproject.toml").is_file() and packaged.is_dir():
        return packaged
    return overlay


def configs_root(project_root: Path | None = None) -> Path:
    """Return overlay ``<project>/configs`` or the packaged configs tree."""
    return _overlay_or_packaged(project_root, CONFIGS_DIRNAME)


def configs_output_root(project_root: Path) -> Path:
    """Return where generated config files for ``project_root`` should be written."""
    return output_root(project_root, CONFIGS_DIRNAME)


def contracts_root(project_root: Path | None = None) -> Path:
    """Return overlay ``<project>/contracts`` or the packaged contracts tree."""
    return _overlay_or_packaged(project_root, CONTRACTS_DIRNAME)


def ontology_root(project_root: Path | None = None) -> Path:
    """Return overlay ``<project>/ontology`` or the packaged ontology tree."""
    return _overlay_or_packaged(project_root, ONTOLOGY_DIRNAME)


def dbt_project_root(project_root: Path | None = None) -> Path:
    """Return overlay ``<project>/dbt`` or the packaged dbt project."""
    return _overlay_or_packaged(project_root, DBT_DIRNAME)


def language_root(project_root: Path | None = None) -> Path:
    """Return overlay ``<project>/language`` or the packaged language profiles."""
    return _overlay_or_packaged(project_root, LANGUAGE_DIRNAME)
