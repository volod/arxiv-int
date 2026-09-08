"""Optional-import isolation for pipeline orchestration modules."""

import ast
from pathlib import Path

ORCH_ROOT = Path(__file__).resolve().parents[3] / "src" / "arxiv_int" / "pipeline"
BLOCKED = frozenset({"sqlalchemy", "alembic", "psycopg", "pandera", "dbt"})
ALLOWED_LAZY = frozenset()


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_orchestration_modules_do_not_import_heavy_stacks_at_module_level() -> None:
    skip = {"dispatch.py", "commands.py", "cli.py", "stages.py", "quality_bound.py"}
    for path in ORCH_ROOT.glob("*.py"):
        if path.name in skip:
            continue
        imported = _imported_names(path)
        assert imported.isdisjoint(BLOCKED), path.name
