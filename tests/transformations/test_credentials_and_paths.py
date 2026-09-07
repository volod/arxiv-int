from pathlib import Path

import pytest

from arxiv_int.transformations.credentials import (
    DATABASE_URL_VARIABLE,
    bound_threads,
    parse_credentials,
    resolve_database_url,
    sanitize_generation_id,
)
from arxiv_int.transformations.model import MAX_THREADS


def test_sanitize_generation_id_is_postgres_safe() -> None:
    assert sanitize_generation_id("Run-01") == "run_01"
    assert sanitize_generation_id("12go") == "g_12go"
    with pytest.raises(ValueError, match="letter or digit"):
        sanitize_generation_id("---")


def test_bound_threads_caps_at_the_documented_maximum() -> None:
    assert bound_threads(0) == 1
    assert bound_threads(99) == MAX_THREADS
    assert bound_threads(2) == 2


def test_parse_credentials_redacts_missing_host() -> None:
    with pytest.raises(ValueError, match="missing a host"):
        parse_credentials("postgresql://user:secret@/db")


def test_parse_credentials_reads_sqlalchemy_urls() -> None:
    parsed = parse_credentials(
        "postgresql+psycopg://arxiv_int:s3cret@127.0.0.1:55432/arxiv_int", threads=8
    )
    assert parsed.host == "127.0.0.1"
    assert parsed.user == "arxiv_int"
    assert parsed.password == "s3cret"
    assert parsed.port == "55432"
    assert parsed.dbname == "arxiv_int"
    assert parsed.threads == MAX_THREADS
    assert parsed.env_mapping()["ARXIV_INT_DBT_PASSWORD"] == "s3cret"


def test_resolve_database_url_prefers_explicit_then_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    monkeypatch.delenv("ARXIV_INT_MIGRATION_DATABASE_URL", raising=False)
    assert resolve_database_url(None) is None
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://u:p@127.0.0.1/db")
    assert resolve_database_url(None) == "postgresql://u:p@127.0.0.1/db"
    assert (
        resolve_database_url("postgresql://other@127.0.0.1/db") == "postgresql://other@127.0.0.1/db"
    )


def test_artifact_paths_stay_under_data_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from arxiv_int.transformations.paths import (
        active_pointer_path,
        dbt_artifact_dir,
        lock_path,
        published_manifest_dir,
        published_quality_dir,
    )

    artifact = dbt_artifact_dir(tmp_path, "run-1")
    assert artifact == tmp_path / "data" / "dbt" / "run-1"
    assert lock_path(tmp_path, "g1").parent == tmp_path / "data" / "dbt" / "locks"
    assert active_pointer_path(tmp_path).name == "active-generation.json"
    runs = tmp_path / "runs"
    assert published_manifest_dir(runs, "run-1") == runs / "run-1" / "manifests"
    assert published_quality_dir(runs, "run-1") == runs / "run-1" / "quality"
