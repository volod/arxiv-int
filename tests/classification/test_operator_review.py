"""Synthetic terminal review checks; no classifier proposal becomes gold by default."""

from io import StringIO

import pytest

from arxiv_int.classification import review_terminal
from arxiv_int.classification.gold_terminal import review_gold
from arxiv_int.classification.labels import read_labels
from arxiv_int.classification.layout import ClassificationLayout
from arxiv_int.classification.review_terminal import review_operating_point
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import load_json, write_json
from tests.integration.classification.review import check_calibration

pytest_plugins = ("tests.classification.test_archive_calibration",)


def _layout(context: RunContext) -> ClassificationLayout:
    return ClassificationLayout.for_run(context.runs_dir, context.run_id)


def test_operating_review_decodes_unicode_and_refuses_unmeasured_accept(
    calibrated_context: RunContext,
) -> None:
    layout = _layout(calibrated_context)
    packet_path = layout.review / "operating-point.json"
    packet = load_json(packet_path)
    packet["readiness"] = "pending"
    packet["pending"] = ["reviewed archive labels and held-out calibration"]
    packet["inspectionCases"] = {
        "assigned": [{"evidence": [{"term": "\u0434\u0430\u043d\u043d\u044b\u0445"}]}]
    }
    write_json(packet_path, packet)
    output = StringIO()
    with pytest.raises(ValueError, match="accept refused"):
        review_operating_point(
            calibrated_context.project_root,
            calibrated_context.runs_dir,
            calibrated_context.run_id,
            StringIO("a\n"),
            output,
        )
    assert "данных" in output.getvalue()
    assert "ru:" in output.getvalue() and "uk:" in output.getvalue()
    assert not (layout.review / "decision.json").exists()


def test_retain_decision_is_explicit_bound_and_not_overwritten(
    calibrated_context: RunContext,
) -> None:
    context = calibrated_context
    output = StringIO()
    assert (
        review_operating_point(
            context.project_root,
            context.runs_dir,
            context.run_id,
            StringIO("u\nNo safe promotion yet\nretain-unclassified\n"),
            output,
        )
        == 0
    )
    decision = load_json(_layout(context).review / "decision.json")
    packet = load_json(_layout(context).review / "operating-point.json")
    assert decision["decision"] == "retain-unclassified"
    assert decision["mappingManifest"] == packet["mappingManifest"]
    assert decision["classifier"] == packet["classifier"]
    with pytest.raises(ValueError, match="already exists"):
        review_operating_point(
            context.project_root, context.runs_dir, context.run_id, StringIO("q\n"), StringIO()
        )


def test_accept_requires_bound_passing_calibration(
    calibrated_context: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = calibrated_context
    layout = _layout(context)
    path = layout.review / "operating-point.json"
    packet = load_json(path)
    integrity = layout.review / "integrity-test.json"
    write_json(integrity, {"mappingManifest": packet["mappingManifest"]})
    packet["integrity"] = {"log": str(integrity), "sha256": hash_file(integrity)[0]}
    packet["calibration"] = check_calibration(context)
    assert packet["calibration"]["qualityGatesPassed"] is False
    packet["evaluation"]["passed"] = True
    packet["calibration"]["qualityGatesPassed"] = True
    packet["calibration"]["reportSha256"] = packet["evaluation"]["sha256"]
    packet["pending"] = []
    packet["readiness"] = "ready"
    monkeypatch.setattr(review_terminal, "_packet", lambda *_: (packet, "synthetic-packet"))
    assert (
        review_operating_point(
            context.project_root,
            context.runs_dir,
            context.run_id,
            StringIO("a\nReviewed held-out errors and captions\naccept\n"),
            StringIO(),
        )
        == 0
    )
    decision = load_json(layout.review / "decision.json")
    assert decision["decision"] == "accept"
    assert decision["approvalStatus"] == "approved"
    assert decision["evaluation"] == packet["evaluation"]


def test_revise_records_proposals_without_editing_policy(calibrated_context: RunContext) -> None:
    context = calibrated_context
    layout = _layout(context)
    before = load_json(layout.review / "operating-point.json")["classifier"]
    assert (
        review_operating_point(
            context.project_root,
            context.runs_dir,
            context.run_id,
            StringIO("r\n0.60\n\n\nKeep unreadable distinct\nInspect more misses\nrevise\n"),
            StringIO(),
        )
        == 0
    )
    decision = load_json(layout.review / "decision.json")
    assert decision["decision"] == "revise"
    assert decision["approvalStatus"] == "not-approved"
    assert decision["proposal"]["thresholds"] == {"primary": 0.6}
    assert decision["proposal"]["exceptionalOutcomes"] == "Keep unreadable distinct"
    assert load_json(layout.review / "operating-point.json")["classifier"] == before


def test_gold_review_requires_human_confirmation_and_resumes(
    calibrated_context: RunContext,
) -> None:
    context = calibrated_context
    layout = _layout(context)
    output = StringIO()
    assert (
        review_gold(
            context.project_root,
            context.runs_dir,
            context.run_id,
            "human-draft",
            4,
            StringIO("q\n"),
            output,
        )
        == 2
    )
    gold = layout.review / "gold-human-draft.jsonl"
    assert read_labels(gold) == []
    assert "Classifier proposal (not gold)" in output.getvalue()
    assert (
        review_gold(
            context.project_root,
            context.runs_dir,
            context.run_id,
            "human-draft",
            4,
            StringIO("unclassified\n\nyes\nq\n"),
            StringIO(),
        )
        == 2
    )
    confirmed = read_labels(gold)
    assert len(confirmed) == 1
    assert confirmed[0]["primary"] == "unclassified"
    assert confirmed[0]["content_sha256"]
    result = review_gold(
        context.project_root,
        context.runs_dir,
        context.run_id,
        "human-draft",
        4,
        StringIO("f\nfreeze\n"),
        StringIO(),
    )
    assert result in {0, 1}
    assert read_labels(gold) == confirmed
    assert (layout.evaluation("human-draft") / "labels.jsonl").is_file()
    assert (layout.quality_evaluation("human-draft") / "metrics.json").is_file()


def test_gold_draft_refuses_mapping_identity_change(calibrated_context: RunContext) -> None:
    context = calibrated_context
    layout = _layout(context)
    assert (
        review_gold(
            context.project_root,
            context.runs_dir,
            context.run_id,
            "identity-bound",
            1,
            StringIO("q\n"),
            StringIO(),
        )
        == 2
    )
    metadata = layout.review / "gold-identity-bound.meta.json"
    changed = load_json(metadata)
    changed["mappingManifest"]["sha256"] = "0" * 64
    write_json(metadata, changed)
    with pytest.raises(ValueError, match="identity differs"):
        review_gold(
            context.project_root,
            context.runs_dir,
            context.run_id,
            "identity-bound",
            1,
            StringIO("q\n"),
            StringIO(),
        )
