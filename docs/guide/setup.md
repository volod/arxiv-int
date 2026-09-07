# Workstation Setup and Readiness

For the short target workflow and the full command chain, see
[Operator workflow and atomic commands](operator-workflow.md). `make setup` is the operator
entry. DAG commands exist; a default investigation run refuses unimplemented stages. Forecast and
report publication remain planned.

Install Git, Make, uv, Docker with the Compose plugin, and Python 3.12 or newer. From a checkout:

```bash
make setup
```

Edit `.env` when requested, then rerun `make setup`. At minimum, `.env` needs a readable
`ARCHIVE_DIR`, a writable `RESULTS_DIR`, a PostgreSQL-compatible `PGDATA_DIR`, and a
non-placeholder `POSTGRES_PASSWORD`. During development, point `ARCHIVE_DIR` at the authorized
representative slice and use ordinary pipeline or stage commands for proof runs. Compose runs the
database and
other artifact-writing services as the invoking user's UID/GID so those directories stay
host-writable. Archive directories may have ordinary host write permissions; the
pipeline's access contract prevents modification. Configure the selected local model identities as
they become relevant. The storage-class requirements and all derived root defaults are documented
in [Portable runtime](../impl/current/portable-runtime.md).
Rotational disks are acceptable for `PGDATA_DIR`, `MODEL_CACHE_DIR`, and `TMP_DIR`; readiness
records device type without warning about it. Filesystem, ownership, permissions, and capacity
requirements still apply.
If `.env` is absent, `make setup` or `make bootstrap` copies `.env.example` before continuing and
reports the required edits as blocking findings. On later runs they append newly introduced template
declarations while preserving every existing operator value and commented declaration. `make
bootstrap` remains available when only the locked contributor environment and a readiness audit are
required.

## Understanding the report

The readiness audit accumulates every applicable check instead of stopping at the first failure:

- `ready` exits `0`; the configured workstation is ready for the selected profile.
- `blocked` exits `1`; an unsafe or missing requirement must be corrected before a run.
- `degraded` exits `2`; the configuration is usable only with the reported limitation.

Interactive terminals show degraded lines in yellow and blocked lines in red. Redirected console
output and the JSON report contain no color control codes.

Every non-ready finding includes the next configuration change or command. Each configured root has
one line containing its resolved path, required storage class, filesystem, device id, rotational
flag, accessible free bytes, and combined readiness assessment. Capacity estimation for a specific
pipeline scope remains the forecast command's responsibility.

The console report is accompanied by an atomic, owner-readable JSON report at
`$RESULTS_DIR/reports/readiness.json`. An explicit path must still resolve beneath `RESULTS_DIR`:

```bash
arxiv-int readiness --profiles "core ui" --json-report "$RESULTS_DIR/reports/ui-readiness.json"
```

Use `--no-json-report` for a console-only check. Passwords, tokens, secrets, and database URLs are
never included in either rendering. Per-command and HTTP checks use the `--timeout` bound, which
defaults to three seconds.

## What the readiness audit changes

The readiness audit is read-only except for its JSON report. It does not create the runtime layout,
install packages, pull models, start containers, alter services, enable database extensions, or
apply migrations. It checks shipped contract and migration state when those assets exist; until
their owning capabilities ship them, the report identifies them as not currently applicable.

After correcting blocking findings, start the default pipeline service set and rerun the readiness
audit:

```bash
make services-up
make readiness
make services-down
```

`make services-down` keeps database and service-state directories for the next start. To wipe those
service data roots after stop, run `make services-reset` to preview paths, then
`make services-reset APPLY=1` to erase them. Pipeline outputs under `RESULTS_DIR` outside
`SERVICE_STATE_DIR` are not erased.

The default `pipeline` alias expands to `core ui observability`, while inference uses a running host
Ollama service with `qwen3.8:27b` as the default generation model. Readiness reports whether it is
installed; if absent, run `ollama pull qwen3.8:27b`. `GENERATION_MODEL` overrides the active model.
Supply a narrower `SERVICE_PROFILES` value when intentionally operating only part of
that set. To use vLLM instead, set `INFERENCE_BACKEND=vllm` and explicitly include `vllm`, for
example `SERVICE_PROFILES="pipeline vllm"`; `graph` and `cadvisor` are also explicit opt-ins.

The vLLM service uses `VLLM_MODEL` and `VLLM_MODEL_REVISION` defaults independently of Ollama tags.
When vLLM is the selected backend, explicit `GENERATION_MODEL` and `GENERATION_MODEL_REVISION`
overrides also configure that service.
