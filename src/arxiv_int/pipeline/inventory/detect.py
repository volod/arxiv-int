"""Conservative bounded magic and encoding detection; no document extraction."""

import codecs
from pathlib import PurePosixPath

from arxiv_int.features import require_module

MAGIC = (
    (b"PK\x03\x04", "application/zip"),
    (b"PK\x05\x06", "application/zip"),
    (b"%PDF-", "application/pdf"),
    (b"\x1f\x8b", "application/gzip"),
    (b"7z\xbc\xaf\x27\x1c", "application/x-7z-compressed"),
    (b"Rar!", "application/vnd.rar"),
    (b"\xd0\xcf\x11\xe0", "application/x-ole-storage"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def detect(sample: bytes, name: str) -> tuple[str, str | None]:
    """Return a magic MIME and a defensible encoding, or explicit unknown."""
    for magic, mime in MAGIC:
        if sample.startswith(magic):
            return mime, None
    if sample[257:262] == b"ustar" or PurePosixPath(name).suffix.lower() == ".tar":
        return "application/x-tar", None
    for bom, encoding in (
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    ):
        if sample.startswith(bom):
            return "text/plain", encoding
    return _text(sample)


def _text(sample: bytes) -> tuple[str, str | None]:
    if b"\x00" in sample:
        return "application/octet-stream", None
    try:
        text = codecs.getincrementaldecoder("utf-8")().decode(sample, final=False)
    except UnicodeDecodeError:
        detector = require_module("charset_normalizer")
        candidate = detector.from_bytes(
            sample, cp_isolation=["cp1251", "koi8_r"], threshold=0.1
        ).best()
        return "text/plain", str(candidate.encoding) if candidate is not None else "unknown"
    if any(ord(char) < 32 and char not in "\t\r\n\f" for char in text):
        return "application/octet-stream", None
    return "text/plain", "ascii" if sample.isascii() else "utf-8"
