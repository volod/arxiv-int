"""Second-opinion inputs are frozen, distinct, sufficiently sized, and leak-resistant."""

import json
import shutil
from pathlib import Path

import pytest

from arxiv_int.resources.paths import configs_root
from arxiv_int.retrieval.query_aliases import fold
from arxiv_int.retrieval.query_normalization import load_query_policy
from arxiv_int.retrieval.second_opinion.database import tokenizer_fingerprint
from arxiv_int.retrieval.second_opinion.filler import filler_rows
from arxiv_int.retrieval.second_opinion.model import SplitData
from arxiv_int.retrieval.second_opinion.protocol import index_text_fields, load_protocol
from arxiv_int.retrieval.second_opinion.run import reindex_required
from arxiv_int.retrieval.second_opinion.splits import (
    FrozenInputError,
    load_filler,
    load_split,
    require_distinct,
    require_minimums,
)
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_FINGERPRINT


def test_frozen_splits_load_and_stay_distinct() -> None:
    protocol = load_protocol()
    development = load_split(None, protocol, "development")
    final = load_split(None, protocol, "final")
    require_distinct(development, final)
    require_minimums(protocol, final)
    assert development.fingerprint == protocol.split_fingerprints["development"]
    assert final.fingerprint == protocol.split_fingerprints["final"]


def test_a_changed_final_split_is_refused(tmp_path: Path) -> None:
    source = configs_root() / "retrieval" / "second-opinion"
    overlay = tmp_path / "configs" / "retrieval" / "second-opinion"
    shutil.copytree(source, overlay)
    payload = json.loads((overlay / "final.json").read_text(encoding="ascii"))
    payload["cases"][0]["query"] = "tuned"
    (overlay / "final.json").write_text(json.dumps(payload), encoding="ascii")
    protocol = load_protocol(tmp_path)
    with pytest.raises(FrozenInputError, match="frozen final input changed"):
        load_split(tmp_path, protocol, "final")


def test_cohort_judgments_match_their_roles() -> None:
    protocol = load_protocol()
    for name in ("development", "final"):
        split = load_split(None, protocol, name)
        for case in split.cases:
            if case.cohort in protocol.cohorts["no_answer"] or case.cohort == "identifier_absent":
                assert not case.relevant and case.hard_negatives, case.case_id
            elif case.cohort in protocol.cohorts["quality"]:
                assert case.relevant, case.case_id
        assert any(case.forbidden for case in split.cases if case.cohort == "syntax")


def test_no_split_text_is_memorized_by_an_alias_dictionary() -> None:
    policy = load_query_policy()
    keys = {key for entries in policy.alias_sets.values() for key in entries}
    values = {
        fold(word)
        for entries in policy.alias_sets.values()
        for texts in entries.values()
        for text in texts
        for word in text.split()
    }
    protocol = load_protocol()
    for name in ("development", "final"):
        split = load_split(None, protocol, name)
        assert not {fold(case.query) for case in split.cases} & set(policy.alias_sets["legacy-v1"])
        _assert_ocr_errors_unmemorized(split, keys, values)


def _assert_ocr_errors_unmemorized(split: SplitData, keys: set[str], values: set[str]) -> None:
    chunks = {chunk.chunk_id: chunk for chunk in split.chunks}
    for case in split.cases:
        if case.cohort != "ocr_noise":
            continue
        query = fold(case.query)
        words = {fold(word) for chunk_id in case.relevant for word in chunks[chunk_id].body.split()}
        corrupted = {word for word in words if _corrupted_form(word, query)}
        assert corrupted, case.case_id
        assert query not in keys and not corrupted & values, case.case_id


def _corrupted_form(word: str, query: str) -> bool:
    # An OCR error keeps the query's length prefix with at most two substituted characters.
    prefix = word[: len(query)]
    return (
        len(prefix) == len(query)
        and prefix != query
        and sum(left != right for left, right in zip(prefix, query, strict=True)) <= 2
    )


def test_production_index_profile_needs_no_reindex() -> None:
    protocol = load_protocol()
    fields = index_text_fields(protocol.index_profiles["unicode-russian"])
    assert tokenizer_fingerprint(fields) == TOKENIZER_FINGERPRINT
    assert reindex_required(protocol, protocol.baseline) is False
    assert reindex_required(protocol, "icu-russian/russian-guarded-v2") is True


def test_filler_is_deterministic_and_disjoint_from_judged_words() -> None:
    protocol = load_protocol()
    vocabulary = load_filler(None, protocol)
    first = list(
        filler_rows(vocabulary, chunks=20, min_words=5, max_words=9, stopword_share=0.3, seed=3)
    )
    second = list(
        filler_rows(vocabulary, chunks=20, min_words=5, max_words=9, stopword_share=0.3, seed=3)
    )
    assert first == second and len(first) == 20
    judged: set[str] = set()
    for name in ("development", "final"):
        split = load_split(None, protocol, name)
        judged |= {fold(word) for chunk in split.chunks for word in chunk.body.split()}
        judged |= {fold(word) for case in split.cases for word in case.query.split()}
    assert not set(vocabulary.vocabulary) & judged
    words = {fold(word) for row in first for word in str(row["body"]).split()}
    assert words <= set(vocabulary.vocabulary) | set(vocabulary.stopwords)
