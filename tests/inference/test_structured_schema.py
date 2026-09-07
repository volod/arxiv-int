"""Structured-output schema generation, validation, and repair copy."""

from pathlib import Path

from arxiv_int.inference.schema import (
    CITED_SPAN_SCHEMA,
    REFUSAL_SCHEMA,
    check_schema_drift,
    extract_json_text,
    generate_schemas,
    is_refusal_payload,
    parse_json_object,
    repair_user_message,
    validate_instance,
)


def test_cited_span_and_refusal_envelopes_validate() -> None:
    valid = {
        "value": "alpha",
        "evidence": [{"quote": "alpha", "start": 0, "end": 5}],
    }
    assert validate_instance(CITED_SPAN_SCHEMA, valid) == ()
    assert validate_instance(CITED_SPAN_SCHEMA, {"value": ""}) != ()
    assert is_refusal_payload({"status": "refused", "reason": "not enough evidence"})
    assert not is_refusal_payload(valid)
    assert validate_instance(REFUSAL_SCHEMA, {"status": "ok", "reason": "x"}) != ()


def test_fence_stripping_and_repair_message_omit_the_prompt() -> None:
    payload = parse_json_object('```json\n{"status":"refused","reason":"no"}\n```')
    assert is_refusal_payload(payload)
    assert extract_json_text("plain") == "plain"
    message = repair_user_message(("$.value: shorter than minLength",))
    assert "secret-prompt" not in message
    assert "minLength" in message


def test_generated_schemas_are_stable(tmp_path: Path) -> None:
    written = generate_schemas(tmp_path)
    assert len(written) == 2
    assert check_schema_drift(tmp_path) == ()
    (tmp_path / "configs" / "models" / "schemas" / "cited-span.schema.json").write_text(
        "{}\n", encoding="utf-8"
    )
    findings = check_schema_drift(tmp_path)
    assert any("drifted" in finding for finding in findings)
