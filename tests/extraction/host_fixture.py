"""Generate a synthetic multi-format archive for real extraction tool runs."""

import sys
import zipfile
from pathlib import Path


def build(root: Path) -> None:
    """Create text, spreadsheet, digital/scanned PDF, image, and failure inputs."""
    root.mkdir(parents=True, exist_ok=False)
    (root / "plain.txt").write_text("Contract number 42\nAmount 100 kg\n", encoding="utf-8")
    (root / "duplicate.txt").write_text("Contract number 42\nAmount 100 kg\n", encoding="utf-8")
    (root / "table.pdf").write_bytes(_digital_pdf())
    (root / "corrupt.pdf").write_bytes(b"%PDF-corrupt")
    (root / "encrypted.pdf").write_bytes(b"%PDF-1.4\n/Encrypt fixture")
    _image_inputs(root)
    _workbook(root)
    with zipfile.ZipFile(root / "members.zip", "w") as archive:
        archive.writestr("nested/member.txt", b"Container member evidence 77")


def _image_inputs(root: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1400, 300), "white")
    drawing = ImageDraw.Draw(image)
    drawing.text((80, 100), "SCANNED INVOICE 42 AMOUNT 100 KG", fill="black", font_size=48)
    image.save(root / "scan.png")
    image.save(root / "scan.pdf", "PDF", resolution=150)


def _workbook(root: Path) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Invoice"
    sheet.append(["Item", "Amount"])
    sheet.append(["Bolt", "100 kg"])
    workbook.save(root / "table.xlsx")


def _digital_pdf() -> bytes:
    stream = (
        b"BT /F1 18 Tf 72 740 Td (Invoice 42) Tj ET\n"
        b"BT /F1 12 Tf 72 700 Td (Item) Tj 180 0 Td (Amount) Tj ET\n"
        b"BT /F1 12 Tf 72 675 Td (Bolt) Tj 180 0 Td (100 kg) Tj ET\n"
        b"70 665 300 60 re S 70 695 m 370 695 l S 220 665 m 220 725 l S\n"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(item)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode(
            "ascii"
        )
    )
    return bytes(output)


if __name__ == "__main__":
    build(Path(sys.argv[1]))
