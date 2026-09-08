"""Typed failures for Git-bound proof identity export."""


class ExportError(Exception):
    """A Git-bound proof copy cannot be produced."""


class ExportCatalogError(ExportError):
    """The source identity catalog is missing or malformed."""


class ExportCollisionError(ExportError):
    """Two source identities hashed to one substitute."""


class ExportLeakError(ExportError):
    """A transformed copy still contains a source identity."""


class ExportSpanError(ExportError):
    """A text span is stale, overlapping, or cannot be remapped."""


class ExportUnsupportedError(ExportError):
    """A selected artifact cannot be rendered from transformed data."""


class ExportPathError(ExportError):
    """An export destination would mutate a protected original."""
