"""Typed failures for fixtures, scoring, evaluate publication, and proofs."""


class EvaluationError(ValueError):
    """Base class for evaluation-foundation failures."""


class MissingEvidenceError(EvaluationError):
    """Raised when a verdict is requested without required metric evidence."""


class SplitLeakError(EvaluationError):
    """Raised when tuning and final items share identity or gold content."""


class FixtureCatalogError(EvaluationError):
    """Raised when a frozen fixture family is missing or malformed."""


class ProofError(EvaluationError):
    """Base class for typed proof-bundle failures."""


class ProofUnknownCapabilityError(ProofError):
    """Raised when the dispatcher is asked for an unregistered capability."""


class ProofStaleError(ProofError):
    """Raised when recorded fingerprints no longer match current inputs."""


class ProofIntegrityError(ProofError):
    """Raised when checksums, validators, or usable stages are incomplete."""


class ProofRedactionError(ProofError):
    """Raised when a repository summary leaks private paths or corpus text."""
