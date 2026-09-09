"""Optional-import isolation for reconcile and prune packages."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "src" / "arxiv_int" / "pipeline"
BLOCKED = frozenset({"sqlalchemy", "alembic", "psycopg", "pandera", "dbt"})
SQL_MODULES = frozenset({"postgres.py", "tables.py"})


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_in_memory_reconcile_and_prune_do_not_import_sqlalchemy() -> None:
    for package in ("reconcile", "prune"):
        for path in (ROOT / package).glob("*.py"):
            if path.name in SQL_MODULES:
                continue
            imported = _imported_names(path)
            assert imported.isdisjoint(BLOCKED), f"{package}/{path.name}"
