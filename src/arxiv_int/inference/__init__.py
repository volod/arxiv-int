"""Local inference scheduling and provider implementations."""

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.client.errors import LeaseCancelledError, LeaseConflictError, ModelFitError
from arxiv_int.inference.client.factory import client_from_config, scheduler_from_config
from arxiv_int.inference.client.types import (
    EmbeddingRequest,
    EmbeddingResult,
    HealthStatus,
    ModelIdentity,
)
from arxiv_int.inference.scheduler import GrantedSession, ModelResourceScheduler
from arxiv_int.inference.scheduler.scheduling import (
    DevicePlacement,
    ModelPlacement,
    ModelRequirement,
    ModelScheduler,
)

__all__ = [
    "DevicePlacement",
    "EmbeddingRequest",
    "EmbeddingResult",
    "GrantedSession",
    "HealthStatus",
    "LeaseCancelledError",
    "LeaseConflictError",
    "LocalInferenceClient",
    "ModelFitError",
    "ModelIdentity",
    "ModelPlacement",
    "ModelRequirement",
    "ModelResourceScheduler",
    "ModelScheduler",
    "client_from_config",
    "scheduler_from_config",
]
