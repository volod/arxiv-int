# Development Guide

## Setup

Install Git, Make, and uv, then run:

```bash
make bootstrap
make doctor
make run
```

The lockfile is committed. After changing dependencies in `pyproject.toml`, run `make lock` and
include the resulting `uv.lock` change.

## Feature groups

The core install carries no runtime dependency. Optional stacks are installed by name:

```bash
uv pip install 'arxiv-int[lake]'
make features
make features STAGE=extract
```

`make features` lists every group with its status, the pipeline stages that activate it, its
install command, the licence and purpose of each declared distribution, and the system dependencies
it expects. Populated groups are `contracts`, `graph`, `inference`, `lake`, and `store`. The
`embeddings`, `evaluation`, `extraction`, `gpu`, `nlp`, and `ui` groups are declared and reserved
for the capability that will choose their components.

System dependencies are not installed by an extra. The `extraction` group expects a reachable
Apache Tika server plus `tesseract-ocr` and `ocrmypdf` for the scanned-PDF lane, `store` expects a
reachable PostgreSQL service, `inference` expects an Ollama system service or the optional vLLM
profile, `gpu` expects a matching NVIDIA driver and CUDA runtime, and `ui` expects Docker.

Adding a dependency means adding it to the group that owns it in
`src/arxiv_int/features/catalog.py` and to the matching extra in `pyproject.toml`, then running
`make lock`. Never add one to the core `dependencies` list, and never import an optional module
directly: call `arxiv_int.features.require_module()` so a missing stack reports its install command
instead of a traceback.

## Quality workflows

`make ci` is the required fast gate and is the command GitHub Actions runs on Python 3.12 and 3.13.
It checks formatting, Ruff rules, mypy, complexity, shell scripts, documentation links, specification
and plan integrity, and tests.

`make quality` adds branch coverage, Markdown style, and source/wheel builds. Run it before release
or after changing project infrastructure. `make quality-report` reports files over the 250-line soft
limit without turning cohesion into a numeric failure.

## Direct uv commands

Make targets are the stable workflow. For one-off dependency debugging:

```bash
source scripts/shared/common.sh
arxiv_int_load_env
uv <command>
```

This resolves `DATA_DIR`, moves supported tool caches with it, and avoids cross-filesystem link
warnings.

## Runtime artifacts

Write generated data under `$DATA_DIR/<method>/<run-id>/`. Use a stable method name and a unique run
id. Keep fixtures under `tests/` only when they are small, deterministic, safe to publish, and
required for CI.
