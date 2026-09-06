"""Service-plan AGE gate behavior."""

from pathlib import Path

import pytest

from arxiv_int.runtime.service_plan import (
    ComposeConfigurationError,
    plan_services,
    require_graph_age,
)
from arxiv_int.stores.postgres_image.compatibility import write_age_compatibility


def test_graph_extensions_follow_age_compatibility_gate(tmp_path: Path) -> None:
    postgres = tmp_path / "docker" / "postgres"
    postgres.mkdir(parents=True)
    write_age_compatibility(
        tmp_path,
        age_enabled=False,
        reason="forced negative",
        image_ref="arxiv-int/postgres:test",
        probe_summary={"cypher": "fail"},
    )
    disabled = plan_services("graph", project_root=tmp_path)
    assert disabled.extensions == frozenset({"pg_search", "vector"})
    with pytest.raises(ComposeConfigurationError, match="graph profile is disabled"):
        require_graph_age(disabled)

    write_age_compatibility(
        tmp_path,
        age_enabled=True,
        reason="forced positive",
        image_ref="arxiv-int/postgres:test",
        probe_summary={"cypher": "pass"},
    )
    enabled = plan_services("graph", project_root=tmp_path)
    assert enabled.extensions == frozenset({"pg_search", "vector", "age"})
    require_graph_age(enabled)


def test_graph_extensions_default_to_age_without_project_root() -> None:
    assert plan_services("graph").extensions == frozenset({"pg_search", "vector", "age"})
