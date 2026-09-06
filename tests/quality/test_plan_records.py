from pathlib import Path

from arxiv_int.quality.plan_records import read_record, record_findings
from tests.quality._plan_fixture import checkpoint_block, record_text, task_block, write_project

SNAPSHOT = task_block("earlier-work")
CHECKPOINT_SNAPSHOT = checkpoint_block("review-earlier-work")


def _findings(
    tmp_path: Path,
    records: dict[str, str],
    index: dict[str, str] | None = None,
) -> list[str]:
    return record_findings(write_project(tmp_path, records=records, index=index))


def test_an_accepted_record_keeps_the_full_task_snapshot(tmp_path: Path) -> None:
    records = {"earlier-work": record_text("earlier-work", snapshot=SNAPSHOT)}

    assert _findings(tmp_path, records) == []


def test_a_snapshot_preserves_every_task_field(tmp_path: Path) -> None:
    path = tmp_path / "earlier-work.md"
    path.write_text(record_text("earlier-work", snapshot=SNAPSHOT), encoding="utf-8")

    record = read_record(path)

    assert record.snapshot is not None
    assert record.snapshot.identifier == "earlier-work"
    assert record.snapshot.fields["acceptance gates"].startswith("`make ci` passes")


def test_an_accepted_record_without_a_snapshot_is_reported(tmp_path: Path) -> None:
    records = {"earlier-work": record_text("earlier-work")}

    findings = _findings(tmp_path, records)

    assert any("no fenced accepted-task snapshot" in finding for finding in findings)


def test_an_accepted_record_without_evidence_is_reported(tmp_path: Path) -> None:
    records = {"earlier-work": record_text("earlier-work", snapshot=SNAPSHOT, evidence=False)}

    findings = _findings(tmp_path, records)

    assert any("no acceptance evidence row" in finding for finding in findings)


def test_a_snapshot_for_another_task_is_reported(tmp_path: Path) -> None:
    records = {"earlier-work": record_text("earlier-work", snapshot=task_block("other-work"))}

    findings = _findings(tmp_path, records)

    assert any("does not match the record id" in finding for finding in findings)


def test_a_record_filed_under_another_id_is_reported(tmp_path: Path) -> None:
    records = {"filed-elsewhere": record_text("earlier-work", snapshot=SNAPSHOT)}

    findings = _findings(tmp_path, records)

    assert any("is filed as `filed-elsewhere`" in finding for finding in findings)


def test_an_unindexed_record_is_reported(tmp_path: Path) -> None:
    records = {"earlier-work": record_text("earlier-work", snapshot=SNAPSHOT)}

    findings = _findings(tmp_path, records, index={})

    assert any("not linked from the record index" in finding for finding in findings)


def test_a_record_without_a_state_is_reported(tmp_path: Path) -> None:
    text = record_text("earlier-work", snapshot=SNAPSHOT).replace("- State: accepted", "- Stage:")
    findings = _findings(tmp_path, {"earlier-work": text})

    assert any("declares no `State`" in finding for finding in findings)


def test_a_checkpoint_record_must_state_both_verdicts(tmp_path: Path) -> None:
    records = {
        "review-earlier-work": record_text("review-earlier-work", snapshot=CHECKPOINT_SNAPSHOT)
    }

    findings = _findings(tmp_path, records)

    assert any("no refactor and proceed verdict" in finding for finding in findings)


def test_a_no_refactor_checkpoint_verdict_is_accepted(tmp_path: Path) -> None:
    handoff = (
        "Coverage: the two producer records. Verdict: no refactor needed.\n\n"
        "Decision: proceed with the listed nonblocking notes. `none identified` remains open.\n"
    )
    records = {
        "review-earlier-work": record_text(
            "review-earlier-work",
            snapshot=CHECKPOINT_SNAPSHOT,
            handoff=handoff,
        )
    }

    assert _findings(tmp_path, records) == []


def test_an_active_record_needs_no_snapshot_or_evidence(tmp_path: Path) -> None:
    records = {"earlier-work": record_text("earlier-work", state="active.", evidence=False)}

    assert _findings(tmp_path, records) == []


def test_a_missing_records_directory_is_reported(tmp_path: Path) -> None:
    assert record_findings(tmp_path) == ["missing required directory: docs/impl/records"]
