import json
from pathlib import Path

from arxiv_int.transformations.artifacts import (
    compiled_sql_fingerprint,
    input_fingerprint,
    relation_names,
    rule_outcomes_from_run_results,
    sanitize_value,
    write_sanitized_json,
)


def test_sanitize_value_drops_env_and_redacts_urls() -> None:
    payload = {
        "metadata": {
            "env": {"ARXIV_INT_DBT_PASSWORD": "super-secret", "PATH": "/usr/bin"},
            "user": "arxiv_int",
        },
        "url": "postgresql://arxiv_int:super-secret@127.0.0.1/arxiv_int",
        "password": "super-secret",
        "nested": [{"token": "abc", "ok": 1}],
    }
    cleaned = sanitize_value(payload)
    assert "env" not in cleaned["metadata"]
    assert "password" not in cleaned
    assert "super-secret" not in json.dumps(cleaned)
    assert "<redacted>" in cleaned["url"]
    assert cleaned["nested"] == [{"ok": 1}]


def test_write_sanitized_json_and_compiled_fingerprint(tmp_path: Path) -> None:
    source = tmp_path / "manifest.json"
    source.write_text(json.dumps({"env": {"SECRET": "x"}, "ok": True}), encoding="utf-8")
    written = write_sanitized_json(source, tmp_path / "out" / "manifest.json")
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded == {"ok": True}
    compiled = tmp_path / "compiled" / "arxiv_int" / "a.sql"
    compiled.parent.mkdir(parents=True)
    compiled.write_text("select 1\n", encoding="utf-8")
    first = compiled_sql_fingerprint(tmp_path)
    compiled.write_text("select 2\n", encoding="utf-8")
    assert compiled_sql_fingerprint(tmp_path) != first
    assert compiled_sql_fingerprint(tmp_path / "missing") != ""


def test_input_fingerprint_and_relation_names_are_stable() -> None:
    left = input_fingerprint(
        command="build",
        generation_id="r1",
        policy_version="1",
        select=("tag:fixture",),
        full_refresh=False,
    )
    right = input_fingerprint(
        command="build",
        generation_id="r1",
        policy_version="1",
        select=("tag:fixture",),
        full_refresh=False,
    )
    changed = input_fingerprint(
        command="build",
        generation_id="r1",
        policy_version="2",
        select=("tag:fixture",),
        full_refresh=False,
    )
    assert left == right
    assert left != changed
    names = relation_names("r1")
    assert names[0] == "derived.stg_documents__g_r1"
    assert all(item.startswith("derived.") for item in names)


def test_rule_outcomes_from_run_results_redact_messages() -> None:
    outcomes = rule_outcomes_from_run_results(
        {
            "results": [
                {
                    "unique_id": "test.arxiv_int.x",
                    "status": "fail",
                    "message": "postgresql://u:secret@127.0.0.1/db exploded",
                    "failures": 1,
                }
            ]
        }
    )
    assert outcomes[0]["status"] == "fail"
    assert "secret" not in outcomes[0]["message"]
