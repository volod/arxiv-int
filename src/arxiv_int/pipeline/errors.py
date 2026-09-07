"""Errors raised by the stage registry, DAG planner, and orchestrator."""


class PipelineError(RuntimeError):
    """Operator-visible pipeline control failure."""

    exit_code = 1


class UnknownStageError(PipelineError):
    """A requested stage name is not in the registry."""


class CyclicDependencyError(PipelineError):
    """Stage dependencies contain a cycle."""


class InvalidRangeError(PipelineError):
    """`--from` / `--to` does not select a connected dependency closure."""


class UnregisteredStageError(PipelineError):
    """A required stage has no runner."""

    def __init__(self, stages: tuple[str, ...]) -> None:
        listed = ", ".join(stages)
        super().__init__(f"unregistered required stage(s): {listed}")
        self.stages = stages


class ConfigDriftError(PipelineError):
    """A later atomic command does not match the frozen run configuration."""


class StaleUpstreamError(PipelineError):
    """Required upstream manifests are missing, stale, or no longer validate."""


class QualityBoundaryError(PipelineError):
    """A declared Pandera or dbt producer check failed or did not run."""
