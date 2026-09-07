"""Local inference scheduling and provider implementations."""

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.factory import client_from_config
from arxiv_int.inference.scheduling import (
    DevicePlacement,
    ModelPlacement,
    ModelRequirement,
    ModelScheduler,
)
from arxiv_int.inference.types import (
    EmbeddingRequest,
    EmbeddingResult,
    HealthStatus,
    ModelIdentity,
)

__all__ = [
    "DevicePlacement",
    "EmbeddingRequest",
    "EmbeddingResult",
    "HealthStatus",
    "LocalInferenceClient",
    "ModelIdentity",
    "ModelPlacement",
    "ModelRequirement",
    "ModelScheduler",
    "client_from_config",
]
