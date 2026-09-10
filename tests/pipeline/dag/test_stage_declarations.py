"""Every production stage must own the first-party code and data it actually executes."""

import ast
from pathlib import Path

import pytest

from arxiv_int.pipeline.control.asset_hashes import PACKAGE_ROOT
from arxiv_int.pipeline.control.owned import owned_sources
from arxiv_int.pipeline.dag.registry import StageSpec
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.normalize.language import profile_fingerprint

LANGUAGE_PROFILES = "resources/language/profiles.json"
_STAGES_WITH_RUNNERS = tuple(
    spec.name for spec in production_registry().specs() if spec.runner is not None
)


def _module_file(name: str) -> Path | None:
    """Resolve one first-party module name onto its packaged file."""
    candidate = PACKAGE_ROOT.joinpath(*name.split(".")[1:])
    module = candidate.with_suffix(".py")
    if module.is_file():
        return module
    package = candidate / "__init__.py"
    return package if package.is_file() else None


def _first_party_imports(path: Path) -> set[str]:
    """Collect every ``arxiv_int`` module a file imports, including function-local imports."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("arxiv_int"):
            module = str(node.module)
            found.add(module)
            found.update(
                f"{module}.{alias.name}"
                for alias in node.names
                if _module_file(f"{module}.{alias.name}") is not None
            )
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if alias.name.startswith("arxiv_int"))
    return found


def _executed_files(entry: str) -> dict[str, str]:
    """Map the transitive first-party import closure of one runner onto packaged paths."""
    files: dict[str, str] = {}
    pending = [entry]
    while pending:
        name = pending.pop()
        path = _module_file(name)
        if name in files or path is None:
            continue
        files[name] = path.relative_to(PACKAGE_ROOT).as_posix()
        pending.extend(_first_party_imports(path))
    return files


def _declared(spec: StageSpec, project_root: Path) -> dict[str, str]:
    code = owned_sources(spec, project_root)["code_fingerprint"]
    return {str(key): str(value) for key, value in code.items()}


@pytest.mark.parametrize("stage", _STAGES_WITH_RUNNERS)
def test_stage_owns_every_first_party_module_it_executes(stage: str, tmp_path: Path) -> None:
    spec = production_registry().get(stage)
    assert spec.runner is not None
    declared = _declared(spec, tmp_path)
    runner_module = type(spec.runner).__module__
    executed = _executed_files(runner_module)
    undeclared = sorted(
        relative
        for name, relative in executed.items()
        if name != runner_module and relative not in declared
    )
    assert undeclared == [], f"{stage} would reuse cached work across edits to: {undeclared}"


def test_reviewed_language_profiles_are_owned_by_normalize_alone(tmp_path: Path) -> None:
    registry = production_registry()
    normalize = _declared(registry.get("normalize"), tmp_path)
    assert normalize.get(LANGUAGE_PROFILES) == profile_fingerprint()
    for stage in ("inventory", "extract", "dedupe", "chunk"):
        assert LANGUAGE_PROFILES not in _declared(registry.get(stage), tmp_path)
