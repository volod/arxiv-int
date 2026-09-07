import ast
from pathlib import Path

from arxiv_int.features import optional_modules

INTERFACE_ROOT = Path(__file__).resolve().parents[2] / "src" / "arxiv_int" / "interfaces"


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_interface_package_does_not_import_optional_modules() -> None:
    heavy = optional_modules()
    imported: set[str] = set()
    for path in INTERFACE_ROOT.glob("*.py"):
        imported.update(_imported_names(path))

    assert imported.isdisjoint(heavy)
    assert "pandera" not in imported
    assert "dbt" not in imported
    assert "polars" not in imported
