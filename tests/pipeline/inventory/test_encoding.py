"""Conservative MIME, encoding and encryption metadata."""

import codecs

import pytest

from arxiv_int.pipeline.inventory.detect import detect


@pytest.mark.parametrize(
    "sample,encoding",
    [
        (b"text", "ascii"),
        ("\u0442\u0435\u043a\u0441\u0442".encode(), "utf-8"),
        (codecs.BOM_UTF16_LE + b"t\x00", "utf-16"),
        (b"\x00\x01\x02", None),
    ],
)
def test_encoding_metadata(sample: bytes, encoding: str | None) -> None:
    assert detect(sample, "input")[1] == encoding


def test_legacy_russian_encodings_are_detected() -> None:
    text = (
        "\u041f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440. "
        "\u042d\u0442\u043e \u0440\u0443\u0441\u0441\u043a\u0438\u0439 "
        "\u0442\u0435\u043a\u0441\u0442 \u0434\u043b\u044f "
        "\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 "
        "\u043a\u043e\u0434\u0438\u0440\u043e\u0432\u043a\u0438. "
    ) * 20
    for encoding in ("cp1251", "koi8_r"):
        assert detect(text.encode(encoding), "text")[1] == encoding
