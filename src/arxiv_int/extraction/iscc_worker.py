"""Subprocess entry point isolating native iscc-tika parsing."""

import json
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any


def main() -> int:
    """Extract one scratch file with active content and OCR disabled."""
    if len(sys.argv) != 5:
        return 2
    source = Path(sys.argv[1])
    output_bytes = int(sys.argv[2])
    ocr_enabled = sys.argv[3] == "ocr"
    from iscc_tika import (  # type: ignore[import-untyped]
        Extractor,
        OfficeParserConfig,
        PdfOcrStrategy,
        PdfParserConfig,
        TesseractOcrConfig,
    )

    pdf_strategy = PdfOcrStrategy.OCR_ONLY if ocr_enabled else PdfOcrStrategy.NO_OCR
    extractor = (
        Extractor()
        .set_extract_string_max_length(output_bytes)
        .set_office_config(OfficeParserConfig().set_extract_macros(False))
        .set_pdf_config(
            PdfParserConfig().set_ocr_strategy(pdf_strategy).set_extract_inline_images(False)
        )
        .set_ocr_config(
            TesseractOcrConfig()
            .set_skip_ocr(not ocr_enabled)
            .set_language(sys.argv[4] if ocr_enabled else "eng")
        )
    )
    text, metadata = extractor.extract_file_to_string(str(source))
    payload: dict[str, Any] = {
        "metadata": dict(metadata),
        "text": text,
        "version": version("iscc-tika"),
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if len(encoded.encode("ascii")) > output_bytes * 2:
        raise ValueError("encoded iscc-tika output exceeds worker limit")
    sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
