"""Semantic adapters reuse ontology/domain validators; missing attachments cannot pass."""

from decimal import Decimal

import polars as pl

from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
from arxiv_int.data_quality.rules.semantic import (
    FACTS_ONTOLOGY_RULE,
    fact_assertion_result,
    missing_semantic_result,
    semantic_rule,
    shacl_not_run,
)
from arxiv_int.ontology.validate import FactAssertion
from arxiv_int.resources.paths import ontology_root
from tests.data_quality._builders import compile_rows_catalog, decimal_frame


def test_unattached_required_semantic_check_cannot_pass() -> None:
    rule = semantic_rule(FACTS_ONTOLOGY_RULE, "Fact assertions must be attached.")
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            related={"documents": pl.DataFrame({"document_id": ["d1"]})},
            attached=(missing_semantic_result(rule),),
            run_id="semantic-missing",
        )
    )
    attached = next(item for item in result.checks if item.rule_id == FACTS_ONTOLOGY_RULE)
    assert attached.status == "not-run"
    assert result.publishable is False


def test_shacl_absence_is_explicit_not_run() -> None:
    result = shacl_not_run("facts")
    assert result.status == "not-run"
    assert "SHACL" in (result.reason or "")


def test_fact_adapter_reuses_ontology_validation() -> None:
    from arxiv_int.ontology.load import load_ontology_catalog

    catalog = load_ontology_catalog(ontology_root())
    assertion = FactAssertion(
        subject_id="s1",
        subject_types=("urn:arxiv-int:class:Object",),
        predicate="unknown-predicate",
        object_id="o1",
        object_types=("urn:arxiv-int:class:Object",),
    )
    result = fact_assertion_result((assertion,), catalog)
    assert result.status == "fail"
    assert result.failed_count >= 1
