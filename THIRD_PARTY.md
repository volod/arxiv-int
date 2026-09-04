# Third-Party Software

## selfsuvis runtime-policy extraction

- Source: <https://github.com/volod/selfsuvis>
- Revision: `bd0f4447bf20a72e9421c93f208ce1f52f1c622b`
- Licence: MIT; the licence text is reproduced in `NOTICE`.
- Form: attributed functional extraction, adapted to project typing and standard-library-only use.

| Local file | Upstream basis | Local changes |
| --- | --- | --- |
| `src/arxiv_int/config.py` | `pipeline/core/env.py` | Recast environment mutation as explicit mapping-based layer precedence. |
| `src/arxiv_int/paths.py` | `pipeline/core/utils.py` | Recast configured index roots as explicit allowed roots with real-path containment. |
| `src/arxiv_int/doctor/report.py` | `pipeline/core/preflight.py` | Retain accumulated ready, degraded, and blocked findings without application-specific probes. |
| `src/arxiv_int/pipeline/steps.py` | `ssv_vdp/pipeline/state.py` | Recast merged statistics as monotonic step records that preserve earlier results. |
| `src/arxiv_int/observability/logging.py` | `pipeline/core/logging.py` | Recast global root configuration as a bounded, reversible session over a supplied logger and sink. |
| `src/arxiv_int/inference/scheduling.py` | `pipeline/core/gpu_utils.py` and `ssv_vdp/steps/caption_helpers/vram.py` | Recast Torch/Ollama-specific probes and unloads as backend-neutral placement and guaranteed release callbacks. |

The extraction intentionally excludes the video and IoT pipelines, Qdrant, LangGraph orchestration,
model implementations, service clients, and upstream compatibility aliases. The code lives in its
owning functional packages, is maintained as a project-owned fork, and is refreshed only by a
deliberate re-extraction and repeat measurement.

## fl-op contract-governance extraction

- Source: <https://github.com/volod/fl-op>
- Revision: `1f452ecaeded92c6bbbd4a86de9ded1ea7444e60`
- Licence: MIT; the licence text is reproduced in `NOTICE`.
- Form: attributed functional extraction, adapted to project typing and contract boundaries.

| Local file | Upstream basis | Local changes |
| --- | --- | --- |
| `src/arxiv_int/contracts/_yaml.py` | `fl_op/contracts/odcs_loader.py`, `registry.py` | Isolate typed mapping loading behind the contracts extra. |
| `src/arxiv_int/contracts/canonical.py` | `fl_op/contracts/canonical_model.py` | Replace fleet constants and Pydantic models with explicit-root immutable project types. |
| `src/arxiv_int/contracts/registry.py` | `fl_op/contracts/registry.py` | Retain portable ODCS/mapping lookup and metadata-drift checks; remove profiles, plugins, domains, and generated-format coupling. |
| `src/arxiv_int/contracts/fingerprint.py` | `fl_op/contracts/fingerprint.py` | Retain normalized semantic hashing without the native FastAvro dependency. |
| `src/arxiv_int/contracts/generate.py` | `fl_op/contracts/schema_gen.py`, `gen/base.py` | Retain explicit registered dispatch as a protocol; defer project generators to contract governance. |
| `src/arxiv_int/contracts/evolution.py` | `fl_op/contracts/evolution.py` | Retain physical snapshots, change classes, version gates, and deterministic history writes without fleet mappings. |

The extraction intentionally excludes fleet-domain contracts and profiles, optimization metadata,
solver and planning models, plugins, Protobuf compilation, Elasticsearch generation, and all
upstream runtime dependencies other than the PyYAML capability already selected by the local
`contracts` extra.
