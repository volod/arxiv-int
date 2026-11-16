"""Frozen scheme build, content identity, snapshot round-trip, and staleness."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.classification.vocabulary.build import build_scheme
from arxiv_int.classification.vocabulary.policy import (
    Extension,
    SchemePolicy,
    load_scheme_policy,
)
from arxiv_int.classification.vocabulary.snapshot import (
    CLASSES_FILE,
    MANIFEST_FILE,
    SnapshotError,
    check_snapshot,
    load_snapshot,
    write_snapshot,
)
from arxiv_int.classification.vocabulary.validate import errors
from tests.classification._fixtures import captions, write_project


@pytest.fixture(name="policy")
def policy_fixture(tmp_path: Path) -> SchemePolicy:
    return load_scheme_policy(write_project(tmp_path / "project"))


def test_build_freezes_rows_with_closure_captions_and_crosswalk(policy: SchemePolicy) -> None:
    built = build_scheme(policy, run_id="r1")
    assert built.publishable
    rows = {row["class_id"]: row for row in built.rows}
    assert len(rows) == 14 + 2
    leaf = rows["tax:01.02.01"]
    assert leaf["ancestor_path"] == "tax:01>tax:01.02" and leaf["depth"] == 3
    assert leaf["class_kind"] == "subfield" and leaf["path_token"] == "t01.02.01"
    assert json.loads(leaf["crosswalk_json"]) == ["fixture:item/01.02.01"]
    assert leaf["caption_ru"] and leaf["caption_uk"] and leaf["slug"] == "subfield-01-02-01"
    assert rows["unreadable"]["namespace"] == "outcome"
    assert built.manifest["taxonomy"]["licence"]["name"] == "MIT"
    assert built.manifest["coverage"][0]["mapped"] == 8


def test_scheme_id_depends_on_content_not_run(policy: SchemePolicy) -> None:
    first = build_scheme(policy, run_id="r1")
    second = build_scheme(policy, run_id="r2")
    letters = Extension("ext:letters", "tax:01.01.01", tuple(sorted(captions("L").items())), "")
    changed = build_scheme(replace(policy, extensions=(letters,)), run_id="r1")
    assert first.scheme_id == second.scheme_id and first.scheme_id.startswith("subjects-")
    assert changed.publishable and changed.scheme_id != first.scheme_id


def test_missing_licence_or_bad_extension_blocks_publication(tmp_path: Path) -> None:
    unlicensed = load_scheme_policy(
        write_project(tmp_path / "project", taxonomy_licence={"name": "", "url": ""})
    )
    assert not build_scheme(unlicensed, run_id="r").publishable
    policy = load_scheme_policy(write_project(tmp_path / "other"))
    clash = Extension("ext:unreadable", "tax:01", tuple(sorted(captions("X").items())), "")
    blocked = build_scheme(replace(policy, extensions=(clash,)), run_id="r")
    assert not blocked.publishable and blocked.rows == ()


def test_snapshot_round_trips_and_refuses_overwrite(policy: SchemePolicy, tmp_path: Path) -> None:
    built = build_scheme(policy, run_id="r1")
    directory = tmp_path / "scheme"
    write_snapshot(directory, built)
    assert check_snapshot(directory, policy) == []
    snapshot = load_snapshot(directory)
    assert snapshot.rows == built.rows
    resolution = snapshot.scheme.resolve_code("01.02.01.09")
    assert resolution is not None and resolution.truncated
    with pytest.raises(SnapshotError):
        write_snapshot(directory, built)


def _stale(directory: Path, policy: SchemePolicy) -> set[str]:
    return {item.code for item in errors(check_snapshot(directory, policy))}


def test_tampered_or_out_of_date_snapshots_are_stale(policy: SchemePolicy, tmp_path: Path) -> None:
    directory = tmp_path / "scheme"
    write_snapshot(directory, build_scheme(policy, run_id="r1"))
    for change in (
        {"policy_sha256": "0" * 64},
        {"extensions_sha256": "0" * 64},
        {"taxonomy": replace(policy.taxonomy, sha256="0" * 64)},
        {"sources": (replace(policy.sources[0], sha256="0" * 64),)},
    ):
        assert _stale(directory, replace(policy, **change)) == {"stale-snapshot"}  # type: ignore[arg-type]
    expected = {item.code for item in check_snapshot(directory, policy, expect_scheme_id="x")}
    assert expected == {"stale-snapshot"}
    classes = directory / CLASSES_FILE
    classes.write_text(classes.read_text(encoding="ascii").replace("Field", "Edited"), "ascii")
    assert "stale-snapshot" in _stale(directory, policy)
    (directory / MANIFEST_FILE).unlink()
    assert _stale(directory, policy) == {"stale-snapshot"}


def test_failed_build_writes_only_the_report(tmp_path: Path) -> None:
    policy = load_scheme_policy(
        write_project(tmp_path / "project", taxonomy_licence={"name": "", "url": ""})
    )
    directory = tmp_path / "scheme"
    with pytest.raises(SnapshotError, match="build-scheme"):
        load_snapshot(directory)
    write_snapshot(directory, build_scheme(policy, run_id="r"))
    assert sorted(path.name for path in directory.iterdir()) == ["report.json"]
    with pytest.raises(SnapshotError, match="did not publish"):
        load_snapshot(directory)
