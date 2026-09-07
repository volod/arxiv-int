"""Binary refusal and residual source-identity leak checks."""

from pathlib import PurePosixPath

from arxiv_int.evaluation.export_errors import ExportLeakError, ExportUnsupportedError
from arxiv_int.evaluation.export_normalize import digit_string
from arxiv_int.evaluation.export_policy import (
    IDENTITIES_ARTIFACT,
    JSON_EXTENSIONS,
    JSONL_EXTENSIONS,
    TEXT_EXTENSIONS,
    UNSUPPORTED_EXTENSIONS,
)

_NUL = b"\x00"
_UTF8_SIG = b"\xef\xbb\xbf"


def classify_artifact(name: str, payload: bytes) -> str:
    """Return `text`, `json`, or `jsonl`, or refuse an unsupported binary."""
    if name == IDENTITIES_ARTIFACT:
        raise ExportUnsupportedError("raw identity catalogs stay local and untracked")
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in UNSUPPORTED_EXTENSIONS or _NUL in payload[:8192]:
        raise ExportUnsupportedError(f"unsupported export format: {name}")
    if suffix in JSONL_EXTENSIONS or name == "scores.jsonl":
        return "jsonl"
    if suffix in JSON_EXTENSIONS or name == "manifest.json":
        return "json"
    if suffix in TEXT_EXTENSIONS or _is_utf8_text(payload):
        return "text"
    raise ExportUnsupportedError(f"unsupported export format: {name}")


def decode_text(payload: bytes) -> str:
    """Decode UTF-8 text, accepting an optional BOM."""
    body = payload[len(_UTF8_SIG) :] if payload.startswith(_UTF8_SIG) else payload
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExportUnsupportedError("artifact is not UTF-8 text") from error


def refuse_leaks(payload: bytes, needles: tuple[str, ...]) -> None:
    """Refuse export when any source identity remains in the transformed bytes."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExportUnsupportedError("transformed artifact is not UTF-8 text") from error
    lowered = text
    digits = digit_string(text)
    for needle in needles:
        if needle and needle in lowered:
            raise ExportLeakError("transformed copy still contains a source identity")
        compact = digit_string(needle)
        if len(compact) >= 7 and compact in digits:
            raise ExportLeakError("transformed copy still contains a source identity")


def _is_utf8_text(payload: bytes) -> bool:
    if _NUL in payload[:8192]:
        return False
    try:
        decode_text(payload)
    except ExportUnsupportedError:
        return False
    return True
