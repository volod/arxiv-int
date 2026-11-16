"""The shipped subject taxonomy is licensed, balanced, multilingual and covers its sources."""

import re
from collections import Counter

from arxiv_int.classification.vocabulary.build import build_scheme
from arxiv_int.classification.vocabulary.policy import load_scheme_policy
from arxiv_int.resources.paths import configs_root

POLICY = load_scheme_policy()
CYRILLIC = re.compile("[\u0400-\u04ff]")


def test_packaged_taxonomy_builds_without_findings() -> None:
    built = build_scheme(POLICY, run_id="packaged")
    assert built.publishable and built.findings == ()
    assert built.manifest["taxonomy"]["licence"]["name"] == "MIT"
    assert build_scheme(POLICY, run_id="again").scheme_id == built.scheme_id


def test_every_source_item_is_covered_exactly_once() -> None:
    coverage = build_scheme(POLICY, run_id="packaged").manifest["coverage"]
    assert {item["sourceId"]: (item["mapped"], item["items"]) for item in coverage} == {
        "openalex-construction-topics": (68, 68),
        "openalex-subfields": (252, 252),
    }
    assert {source.licence.name for source in POLICY.sources} == {"CC0 1.0"}


def test_structure_is_balanced_with_technical_domains_detailed() -> None:
    stats = build_scheme(POLICY, run_id="packaged").manifest["balance"]
    assert stats["leafDepth"] == 3 and stats["maxDomainLeafShare"] <= 0.25
    assert stats["fanOutMin"] >= 2 and stats["fanOutMax"] <= 16
    per_domain = stats["leavesPerDomain"]
    technical = sum(per_domain[f"tax:{code}"] for code in ("01", "02", "03", "04"))
    assert technical > sum(per_domain.values()) / 2
    fields = Counter(
        entry.code[:2] for entry in POLICY.taxonomy.entries if entry.code.count(".") == 1
    )
    assert fields["04"] >= 10


def test_captions_are_trilingual_and_the_file_is_ascii() -> None:
    for entry in POLICY.taxonomy.entries:
        captions = dict(entry.captions)
        assert set(captions) == {"en", "ru", "uk"}, entry.code
        assert captions["en"].isascii() and CYRILLIC.search(captions["ru"]), entry.code
        assert CYRILLIC.search(captions["uk"]), entry.code
    payload = (configs_root() / "classification" / "taxonomy.json").read_bytes()
    assert payload.isascii()
