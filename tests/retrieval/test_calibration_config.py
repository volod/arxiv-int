"""The final lexical split and profile comparison are frozen and complete."""

import json

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.retrieval.calibration.config import (
    REQUIRED_CATEGORIES,
    load_calibration_config,
    profile_text_fields,
)
from arxiv_int.retrieval.query_normalization import SELECTED_QUERY_PROFILE
from arxiv_int.stores.projections.adapters.lexical import (
    SELECTED_INDEX_PROFILE,
    TOKENIZER_FINGERPRINT,
)


def test_calibration_freezes_final_categories_and_predeclared_pair() -> None:
    config = load_calibration_config()
    assert {item.category for item in config.queries} == REQUIRED_CATEGORIES
    assert {item.split for item in config.queries} == {"final"}
    assert config.baseline_profile == SELECTED_INDEX_PROFILE
    assert config.candidate_profile == "unicode-russian-safe-v1"
    assert len(config.queries) >= 6
    assert len(config.fingerprint) == 64


def test_adopted_index_declaration_matches_the_production_fingerprint() -> None:
    config = load_calibration_config()
    candidate = next(
        item for item in config.profiles if item.profile_id == config.candidate_profile
    )
    fields = profile_text_fields(candidate)
    fingerprint = sha256_text(json.dumps(fields, ensure_ascii=True, sort_keys=True))
    assert candidate.query_profile == SELECTED_QUERY_PROFILE
    assert fingerprint == TOKENIZER_FINGERPRINT
