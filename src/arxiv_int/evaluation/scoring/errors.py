"""Typed failures raised by reusable evaluation metrics."""


class MissingEvidenceError(ValueError):
    """Raised when a metric or verdict lacks required evidence."""
