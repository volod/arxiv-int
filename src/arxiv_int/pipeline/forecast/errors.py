"""Forecast refusal and freshness errors."""

from arxiv_int.pipeline.run.errors import PipelineError

EXIT_RESOURCE = 3


class ForecastRefusedError(PipelineError):
    """Requested work is blocked by a forecast or free-space recheck."""

    exit_code = EXIT_RESOURCE


class StaleForecastError(ForecastRefusedError):
    """Stored forecast does not cover the current configuration or plan."""
