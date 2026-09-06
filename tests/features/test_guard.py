import pytest

from arxiv_int.features import guard
from arxiv_int.features.guard import (
    INSTALLED,
    MISSING,
    RESERVED,
    MissingFeatureError,
    group_status,
    install_command,
    module_available,
    require_module,
)
from arxiv_int.features.model import FeatureGroup, Requirement

POPULATED = FeatureGroup(
    name="lake",
    summary="test group",
    owner="corpus-foundation",
    requirements=(Requirement("pyarrow", "pyarrow", "Apache-2.0", "read artifacts"),),
)
RESERVED_GROUP = FeatureGroup(name="nlp", summary="test group", owner="russian-nlp")


def test_install_command_names_the_distribution_and_extra() -> None:
    assert install_command(POPULATED) == "uv pip install 'arxiv-int[lake]'"


def test_module_available_reports_a_missing_module() -> None:
    assert module_available("json") is True
    assert module_available("arxiv_int_missing_module") is False


def test_module_available_survives_an_unimportable_parent() -> None:
    assert module_available("json.missing.child") is False


def test_group_status_reports_reserved_installed_and_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    assert group_status(RESERVED_GROUP) == RESERVED

    monkeypatch.setattr(guard, "module_available", lambda name: True)
    assert group_status(POPULATED) == INSTALLED

    monkeypatch.setattr(guard, "module_available", lambda name: False)
    assert group_status(POPULATED) == MISSING


def test_require_module_imports_a_declared_module(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(guard, "import_module", lambda name: name)

    assert require_module("pyarrow") == "pyarrow"


def _unavailable(name: str) -> object:
    raise ImportError(f"No module named {name!r}")


def test_missing_optional_module_names_its_group_and_install_command(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(guard, "import_module", _unavailable)

    with pytest.raises(MissingFeatureError) as error:
        require_module("pyarrow")

    message = str(error.value)
    assert "'pyarrow' is not installed" in message
    assert "'lake' feature group" in message
    assert "uv pip install 'arxiv-int[lake]'" in message
    assert error.value.group == "lake"
    assert error.value.module == "pyarrow"


def test_requiring_an_undeclared_module_is_a_programming_error() -> None:
    with pytest.raises(LookupError):
        require_module("pandas")
