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
