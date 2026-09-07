"""Acquire or cache-check configured local model assets for the selected backend."""

from collections.abc import Callable
from subprocess import CompletedProcess

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.inference_config import selected_backend
from arxiv_int.runtime.setup.model import RETRY_COMMAND, PhaseResult, reused_or_ready
from arxiv_int.runtime.setup.state import fingerprint_for

CommandRunner = Callable[..., CompletedProcess[str]]


def parse_ollama_list(stdout: str) -> set[str]:
    """Parse `ollama list` names from the first column, skipping the header."""
    names: set[str] = set()
    for line in stdout.splitlines()[1:]:
        token = line.split()[0] if line.split() else ""
        if token:
            names.add(token)
    return names


def configured_models(config: RuntimeConfig) -> tuple[str, ...]:
    """Return configured embedding, generation, and rerank identities."""
    values = dict(config.values)
    names = ("EMBEDDING_MODEL", "GENERATION_MODEL", "RERANK_MODEL")
    return tuple(values[name].strip() for name in names if values.get(name, "").strip())


def _list_available(
    config: RuntimeConfig, backend: str, runner: CommandRunner, listed: set[str] | None
) -> set[str]:
    if listed is not None:
        return listed
    if backend != "ollama":
        return set()
    completed = runner(("ollama", "list"), cwd=config.project_root)
    if completed.returncode != 0:
        return set()
    return parse_ollama_list(completed.stdout)


def _acquire_missing(
    config: RuntimeConfig,
    backend: str,
    missing: list[str],
    runner: CommandRunner,
    digest: str,
    verified: dict[str, str] | None,
) -> PhaseResult:
    if backend == "ollama":
        completed = runner(("ollama", "pull", missing[0]), cwd=config.project_root)
        if completed.returncode != 0:
            return PhaseResult(
                "models",
                "blocked",
                f"ollama pull failed for {missing[0]}",
                action="start the host Ollama service, then " + RETRY_COMMAND,
            )
        return PhaseResult("models", "ready", f"acquired {missing[0]}", fingerprint=digest)
    snapshot = config.model_cache_dir / "hub"
    if snapshot.is_dir() and any(snapshot.iterdir()):
        return PhaseResult(
            "models",
            reused_or_ready(verified, "models", digest),
            "vLLM model cache is present",
            fingerprint=digest,
        )
    return PhaseResult(
        "models",
        "ready",
        "vLLM will fetch missing weights into MODEL_CACHE_DIR on service start",
        fingerprint=digest,
    )


def run_models_phase(
    config: RuntimeConfig,
    *,
    downloads: bool,
    runner: CommandRunner,
    listed: set[str] | None = None,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Pull missing Ollama tags or require a vLLM cache hit."""
    backend = selected_backend(dict(config.values))
    wanted = configured_models(config)
    digest = fingerprint_for(backend, *wanted)
    if not wanted:
        return PhaseResult(
            "models",
            "blocked",
            "no generation model is configured",
            action="set GENERATION_MODEL in .env",
        )
    missing = [
        name for name in wanted if name not in _list_available(config, backend, runner, listed)
    ]
    if not missing:
        return PhaseResult(
            "models",
            reused_or_ready(verified, "models", digest),
            "configured models are available",
            fingerprint=digest,
        )
    if not downloads:
        return PhaseResult(
            "models",
            "blocked",
            "offline cache miss: " + ", ".join(missing),
            action="set SETUP_DOWNLOADS=1 or place the models in the backend cache",
        )
    return _acquire_missing(config, backend, missing, runner, digest, verified)
