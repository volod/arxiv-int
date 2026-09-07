from pathlib import Path

from arxiv_int.evaluation.export_policy import (
    POLICY_FILENAME,
    POLICY_ID,
    check_policy_drift,
    generate_policy,
    namespaced_digest,
    policy_fingerprint,
)


def test_namespaced_digest_is_stable_and_kind_separated() -> None:
    first = namespaced_digest("entity.person", "person:alpha")
    second = namespaced_digest("entity.person", "person:alpha")
    other = namespaced_digest("entity.company", "person:alpha")

    assert first == second
    assert len(first) == 64
    assert first != other
    assert first == namespaced_digest("entity.person", "person:alpha")


def test_policy_generate_and_check_are_canonical(tmp_path: Path) -> None:
    path = generate_policy(tmp_path)
    assert path.name == POLICY_FILENAME
    assert check_policy_drift(tmp_path) == ()
    fingerprint = policy_fingerprint()
    assert len(fingerprint) == 64
    path.write_text("{}\n", encoding="utf-8")
    findings = check_policy_drift(tmp_path)
    assert findings
    assert POLICY_ID.startswith("arxiv-int.proof-identity")
