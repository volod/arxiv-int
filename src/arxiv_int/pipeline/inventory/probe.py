"""Shared bounded byte inspection for physical files and container members."""

from dataclasses import dataclass


@dataclass(slots=True)
class ContentProbe:
    """Retain a MIME/encoding sample and conservative PDF encryption marker evidence."""

    sample_limit: int
    sample: bytes = b""
    tail: bytes = b""
    encrypted: bool = False

    def add(self, chunk: bytes) -> None:
        self.sample += chunk[: max(0, self.sample_limit - len(self.sample))]
        self.encrypted = self.encrypted or b"/Encrypt" in self.tail + chunk
        self.tail = chunk[-16:]


def quarantine_reason(mime: str, encrypted: bool) -> str | None:
    """Apply one supported-format policy to both physical files and members."""
    if mime == "application/pdf" and encrypted:
        return "encrypted-pdf-marker"
    if mime in {
        "application/octet-stream",
        "application/vnd.rar",
        "application/x-7z-compressed",
        "application/x-ole-storage",
    }:
        return "unsupported-format"
    return None
