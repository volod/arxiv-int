"""Layered project configuration."""

from collections.abc import Mapping


def merge_config_layers(
    defaults: Mapping[str, str],
    dotenv: Mapping[str, str | None],
    environment: Mapping[str, str],
    cli: Mapping[str, str | None],
) -> dict[str, str]:
    """Merge configuration from lowest to highest precedence.

    ``None`` means that a layer did not provide a value. An empty string is an
    explicit value and therefore remains eligible to override a lower layer.
    """
    merged = dict(defaults)
    for layer in (dotenv, environment, cli):
        merged.update({key: value for key, value in layer.items() if value is not None})
    return merged
