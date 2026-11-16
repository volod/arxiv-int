"""Source coverage and structural balance gates."""

from dataclasses import replace
from pathlib import Path

from arxiv_int.classification.vocabulary.build import taxonomy_classes
from arxiv_int.classification.vocabulary.coverage import balance, coverage
from arxiv_int.classification.vocabulary.model import Scheme
from arxiv_int.classification.vocabulary.policy import SchemePolicy, load_scheme_policy
from arxiv_int.classification.vocabulary.validate import errors
from tests.classification._fixtures import captions, fixture_classes, write_project


def policy_for(tmp_path: Path, **options: object) -> SchemePolicy:
    return load_scheme_policy(write_project(tmp_path / "project", **options))  # type: ignore[arg-type]


def coverage_codes(policy: SchemePolicy) -> set[str]:
    found, _ = coverage(taxonomy_classes(policy), policy.sources)
    return {item.code for item in errors(found)}


def test_complete_coverage_reports_every_item_mapped(tmp_path: Path) -> None:
    policy = policy_for(tmp_path)
    found, stats = coverage(taxonomy_classes(policy), policy.sources)
    assert found == []
    assert stats == [{"items": 8, "mapped": 8, "sourceId": "fixture-source"}]


def test_unmapped_duplicate_and_unknown_references_fail(tmp_path: Path) -> None:
    classes = fixture_classes()
    classes[2].pop("crosswalk")
    assert coverage_codes(
        policy_for(
            tmp_path / "a",
            classes=classes,
            items=["fixture:item/01.01.01", "fixture:item/01.01.02"],
        )
    ) == {"coverage-missing", "crosswalk-unknown"}
    doubled = fixture_classes()
    doubled[3]["crosswalk"] = ["fixture:item/01.01.01"]
    assert "coverage-duplicate" in coverage_codes(policy_for(tmp_path / "b", classes=doubled))


def balance_codes(policy: SchemePolicy) -> set[str]:
    found, _ = balance(Scheme.of(taxonomy_classes(policy)), policy.balance)
    return {item.code for item in found}


def test_balanced_fixture_passes_with_statistics(tmp_path: Path) -> None:
    policy = policy_for(tmp_path)
    found, stats = balance(Scheme.of(taxonomy_classes(policy)), policy.balance)
    assert found == []
    assert stats["leaves"] == 8 and stats["maxDomainLeafShare"] == 0.5
    assert stats["classesPerDepth"] == {"1": 2, "2": 4, "3": 8}


def test_shallow_leaf_thin_branch_and_dominant_domain_fail(tmp_path: Path) -> None:
    shallow = [*fixture_classes(), {"captions": captions("Domain 03"), "code": "03"}]
    assert "unbalanced-depth" in balance_codes(policy_for(tmp_path / "a", classes=shallow))
    thin = [item for item in fixture_classes() if item["code"] != "02.02.02"]
    assert "unbalanced-branching" in balance_codes(policy_for(tmp_path / "b", classes=thin))
    policy = policy_for(tmp_path / "c")
    strict = replace(policy, balance=replace(policy.balance, max_domain_leaf_share=0.4))
    assert balance_codes(strict) == {"unbalanced-domain"}
