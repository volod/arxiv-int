from arxiv_int.pipeline.normalize.language import UNKNOWN, detect_language, profile_fingerprint

RUSSIAN = (
    "\u0414\u043e\u0433\u043e\u0432\u043e\u0440 \u043d\u0430 "
    "\u043f\u043e\u0441\u0442\u0430\u0432\u043a\u0443 \u0442\u043e\u0432\u0430\u0440\u0430. "
    "\u0421\u0443\u043c\u043c\u0430 \u0438 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442"
    "\u0432\u043e \u0443\u043a\u0430\u0437\u0430\u043d\u044b \u0432 "
    "\u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0438."
)
UKRAINIAN = (
    "\u0414\u043e\u0433\u043e\u0432\u0456\u0440 \u043d\u0430 "
    "\u043f\u043e\u0441\u0442\u0430\u0432\u043a\u0443 \u0442\u043e\u0432\u0430\u0440\u0443. "
    "\u0421\u0443\u043c\u0430 \u0456 \u043a\u0456\u043b\u044c\u043a\u0456\u0441\u0442"
    "\u044c \u0432\u0456\u0434 \u0442\u043e\u0432\u0430\u0440\u0438\u0441\u0442\u0432\u0430."
)
ENGLISH = "The invoice total and the contract amount are stated in the annex for this item."


def _detect(text: str) -> tuple[str, float]:
    result = detect_language(text, sample_chars=4000, min_letters=20, min_confidence=0.3)
    return result.language, result.confidence


def test_detects_declared_languages_from_script_and_stopwords() -> None:
    assert _detect(RUSSIAN)[0] == "rus"
    assert _detect(UKRAINIAN)[0] == "ukr"
    assert _detect(ENGLISH)[0] == "eng"


def test_reports_unknown_for_samples_without_enough_letters() -> None:
    language, confidence = _detect("42 100 7 -- 13")

    assert language == UNKNOWN
    assert confidence == 0.0


def test_detection_is_deterministic_and_profile_bound() -> None:
    assert _detect(RUSSIAN) == _detect(RUSSIAN)
    assert len(profile_fingerprint()) == 64
