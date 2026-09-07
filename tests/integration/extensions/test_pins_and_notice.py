"""Unit coverage for pinned ParadeDB + AGE image metadata."""

from pathlib import Path

from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres_image.compatibility import (
    load_age_compatibility,
    write_age_compatibility,
)
from arxiv_int.stores.postgres_image.pins import load_image_pins, merge_shared_preload


def test_pins_match_dockerfile_and_notice() -> None:
    root = discover_project_root(Path(__file__))
    pins = load_image_pins(root)
    dockerfile = (root / "docker" / "postgres" / "Dockerfile").read_text(encoding="utf-8")
    notice = (root / "docker" / "postgres" / "NOTICE").read_text(encoding="utf-8")
    assert pins.paradedb_digest in dockerfile
    assert pins.age_git_sha in dockerfile
    assert pins.local_image_ref.startswith("arxiv-int/postgres:")
    assert "AGPL-3.0" in notice
    assert "Apache AGE" in notice
    assert pins.age_git_sha in notice


def test_merge_shared_preload_preserves_existing_libraries() -> None:
    assert (
        merge_shared_preload("pg_search,pg_cron,pg_stat_statements", "age")
        == "pg_search,pg_cron,pg_stat_statements,age"
    )
    assert (
        merge_shared_preload("pg_search,pg_cron,pg_stat_statements,age", "age")
        == "pg_search,pg_cron,pg_stat_statements,age"
    )


def test_age_compatibility_round_trip(tmp_path: Path) -> None:
    postgres = tmp_path / "docker" / "postgres"
    postgres.mkdir(parents=True)
    (postgres / "age-compatibility.json").write_text(
        '{"age_enabled": false, "reason": "pending", "image_ref": "", '
        '"probed_at": "", "probe_summary": {}}',
        encoding="utf-8",
    )
    loaded = load_age_compatibility(tmp_path)
    assert loaded.age_enabled is False
    written = write_age_compatibility(
        tmp_path,
        age_enabled=True,
        reason="probes passed",
        image_ref="arxiv-int/postgres:test",
        probe_summary={"cypher": "pass"},
    )
    assert written.age_enabled is True
    assert load_age_compatibility(tmp_path).probe_summary["cypher"] == "pass"
