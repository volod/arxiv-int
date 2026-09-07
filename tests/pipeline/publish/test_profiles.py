"""Profile declarations stay aligned with setup and lexical is a smaller subset."""

from pathlib import Path

from arxiv_int.pipeline.publish.profiles import (
    DEFAULT_PROFILES,
    check_profile_alignment,
    load_profile,
)
from arxiv_int.pipeline.publish.schema import check_schema_drift
from arxiv_int.pipeline.stages import OPTIONAL_STAGES, profile_stage_names
from arxiv_int.runtime.setup.requirements import PROFILE_STAGES

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_investigation_and_lexical_match_setup_profile_stages() -> None:
    assert check_profile_alignment() == ()
    assert DEFAULT_PROFILES["investigation"].required_stages == PROFILE_STAGES["investigation"]
    assert DEFAULT_PROFILES["lexical"].required_stages == PROFILE_STAGES["lexical"]
    assert DEFAULT_PROFILES["investigation"].required_stages == profile_stage_names("investigation")
    assert set(DEFAULT_PROFILES["investigation"].optional_stages) == set(OPTIONAL_STAGES)


def test_lexical_profile_is_visibly_smaller() -> None:
    investigation = load_profile("investigation", PROJECT_ROOT)
    lexical = load_profile("lexical", PROJECT_ROOT)
    assert len(lexical.required_stages) < len(investigation.required_stages)
    inv_required = {item.family_id for item in investigation.families if item.required}
    lex_required = {item.family_id for item in lexical.families if item.required}
    assert lex_required < inv_required
    assert "facts" in inv_required
    assert "facts" not in lex_required
    assert "report" in lex_required


def test_committed_pipeline_assets_match_python_defaults() -> None:
    assert check_schema_drift(PROJECT_ROOT) == ()
