"""Behavior tests for the deterministic hierarchical classifier."""

from arxiv_int.classification.features import CaptionClassifier
from arxiv_int.classification.model import DocumentText, PhysicalFile
from arxiv_int.classification.policy import load_classifier_policy
from arxiv_int.classification.vocabulary.build import build_scheme
from arxiv_int.classification.vocabulary.model import Scheme
from arxiv_int.classification.vocabulary.policy import load_scheme_policy
from arxiv_int.classification.vocabulary.snapshot import rows_to_classes


def _classifier() -> CaptionClassifier:
    built = build_scheme(load_scheme_policy(), run_id="run-test")
    return CaptionClassifier(Scheme.of(rows_to_classes(built.rows)), load_classifier_policy())


def _file(text: str, *, status: str = "ready", reason: str | None = None) -> PhysicalFile:
    documents = () if status != "ready" else (DocumentText("doc", "normalized", text, text),)
    return PhysicalFile("occ", "one", "folder/source.txt", "a" * 64, status, reason, documents, ())


def test_specific_multilingual_caption_evidence_selects_leaf_and_ancestors() -> None:
    classifier = _classifier()
    texts = (
        "Machine learning and artificial intelligence data science neural network",
        "\u041c\u0430\u0448\u0438\u043d\u043d\u043e\u0435 \u043e\u0431\u0443\u0447\u0435\u043d\u0438\u0435",
        "\u041c\u0430\u0448\u0438\u043d\u043d\u0435 \u043d\u0430\u0432\u0447\u0430\u043d\u043d\u044f",
    )
    results = tuple(classifier.classify(_file(text)) for text in texts)
    result = results[0]

    assert all(item.primary == "tax:02.03.01" for item in results)
    assert result.primary == "tax:02.03.01"
    assert result.path == ("tax:02", "tax:02.03", "tax:02.03.01")
    assert result.confidence >= load_classifier_policy().primary_threshold
    assert {str(item["term"]) for item in result.evidence} >= {"machine", "learning"}
    prototype = next(item for item in classifier.prototypes if item.class_id == result.primary)
    assert prototype.features["w:computing"] == load_classifier_policy().weights.ancestor_caption


def test_low_signal_content_is_not_forced_into_the_taxonomy() -> None:
    result = _classifier().classify(_file("xqz random unrelated gibberish 193847"))

    assert result.primary == "unclassified"
    assert result.path == ("unclassified",)
    assert result.failure_reason == "below-threshold-or-margin"


def test_unreadable_requires_recorded_upstream_failure() -> None:
    result = _classifier().classify(_file("", status="quarantined", reason="encrypted"))

    assert result.primary == "unreadable"
    assert result.confidence == 1.0
    assert result.failure_reason == "inventory-encrypted"
