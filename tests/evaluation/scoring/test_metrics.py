from arxiv_int.evaluation.scoring.metrics import extraction_metrics, normalize_text, text_metrics


def test_text_metrics_normalize_and_measure_token_overlap() -> None:
    assert normalize_text("Kyiv, CAPITAL!") == "kyiv capital"
    assert text_metrics("Kyiv.", "kyiv").exact == 1.0

    partial = text_metrics("capital of Ukraine Kyiv", "Kyiv capital")

    assert partial.precision == 0.5
    assert partial.recall == 1.0
    assert partial.f1 == 2.0 / 3.0


def test_empty_reference_is_not_an_exact_match() -> None:
    assert text_metrics("", "").exact == 0.0


def test_extraction_metrics_penalize_missing_extra_and_duplicate_values() -> None:
    metrics = extraction_metrics(["a", "a", "extra"], ["a", "a", "missing"])

    assert metrics.expected == metrics.predicted == 3
    assert metrics.matched == 2
    assert metrics.precision == metrics.recall == metrics.f1 == 2.0 / 3.0


def test_extraction_metrics_define_empty_inputs_as_zero_evidence() -> None:
    assert extraction_metrics([], []).precision == 0.0
    assert extraction_metrics([], []).recall == 0.0
    assert extraction_metrics([], []).f1 == 0.0
