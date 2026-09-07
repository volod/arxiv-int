"""Optional-import isolation for observability modules."""

import ast
from pathlib import Path

OBS_ROOT = Path(__file__).resolve().parents[2] / "src" / "arxiv_int" / "observability"
SQL_MODULES = frozenset({"postgres.py", "tables.py"})
BLOCKED = frozenset({"sqlalchemy", "alembic", "psycopg", "pandera", "dbt"})


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_core_observability_does_not_import_sqlalchemy() -> None:
    for path in OBS_ROOT.glob("*.py"):
        if path.name in SQL_MODULES:
            continue
        imported = _imported_names(path)
        assert imported.isdisjoint(BLOCKED), path.name
