"""Typed failures for model fit and host-wide GPU leases."""


class ModelFitError(RuntimeError):
    """The requested model cannot run on this host snapshot."""


class LeaseCancelledError(RuntimeError):
    """Waiting for or holding the GPU lease was cancelled."""


class LeaseConflictError(RuntimeError):
    """Another GPU-heavy workload still holds the exclusive host lease."""
