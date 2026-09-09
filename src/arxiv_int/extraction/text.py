"""Bounded direct decoding for already identified plain text."""

from pathlib import Path

from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.interfaces.sources import SourceAnchor, SourceOccurrence


class PlainTextExtractor:
    """Preserve known text encodings when Tika is unnecessary."""

    name = "plain-text"
    feature = "extraction"

    def __init__(self, policy: ExtractionPolicy, encoding: str | None) -> None:
        self.policy = policy
        self.encoding = encoding or "utf-8"

    def supports(self, media_type: str) -> bool:
        return media_type == "text/plain"

    def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        payload = source.read_bytes()
        if len(payload) > self.policy.input_bytes:
            raise ExtractionError(
                "input-size-limit",
                f"source exceeds extraction limit of {self.policy.input_bytes} bytes",
            )
        try:
            text = payload.decode(self.encoding)
        except (LookupError, UnicodeDecodeError) as error:
            raise ExtractionError(
                "decode-failed", f"cannot decode text with inventory encoding {self.encoding}"
            ) from error
        anchor = SourceAnchor(
            occurrence,
            start_char=0,
            end_char=len(text),
            page=1,
            kind="text",
        )
        return ExtractedDocument(
            text=text,
            media_type="text/plain",
            occurrence=occurrence,
            extractor_profile=self.name,
            anchors=(anchor,),
            metadata={"encoding": self.encoding, "tool_version": "python-codecs"},
        )
