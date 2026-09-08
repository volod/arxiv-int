"""Typed Pydantic loaders for ODCS and mapping documents."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _ExtraModel(BaseModel):
    """Base model that preserves unknown metadata fields."""

    model_config = ConfigDict(extra="allow")


class OdcsDocument(_ExtraModel):
    """One ODCS 3.1 data contract document."""

    apiVersion: str
    kind: str
    id: str
    version: str
    status: str
    name: str | None = None
    domain: str | None = None
    description: dict[str, Any] | None = None
    team: dict[str, Any] | list[Any] | None = None
    servers: list[dict[str, Any]] = Field(default_factory=list)
    schema_: list[dict[str, Any]] = Field(default_factory=list, alias="schema")
    customProperties: list[dict[str, Any]] = Field(default_factory=list)


class MappingDocument(_ExtraModel):
    """One physical-to-canonical mapping document."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    fieldMappings: list[dict[str, Any]] = Field(default_factory=list)


class RegistryDocument(_ExtraModel):
    """Root registry index."""

    contracts: dict[str, dict[str, Any]]


def load_odcs_document(raw: dict[str, Any]) -> OdcsDocument:
    """Validate and load one ODCS mapping while preserving unknown keys."""
    return OdcsDocument.model_validate(raw)


def load_mapping_document(raw: dict[str, Any]) -> MappingDocument:
    """Validate and load one mapping document while preserving unknown keys."""
    return MappingDocument.model_validate(raw)


def load_registry_document(raw: dict[str, Any]) -> RegistryDocument:
    """Validate and load the registry index while preserving unknown keys."""
    return RegistryDocument.model_validate(raw)
