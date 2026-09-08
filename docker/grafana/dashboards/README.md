# Provisioned Dashboards

Repository-owned Grafana dashboards live here. Grafana mounts this directory read-only;
mutable UI state belongs under `SERVICE_STATE_DIR`.

Pipeline control provisions:

- `pipeline-progress.json` -- stage throughput, backlog, worker states, and error counts
  from `ctl.stage_progress`
- `resource-pressure.json` -- CPU/RAM/disk/GPU and Postgres size/WAL from progress rows
  plus postgres-exporter Prometheus series

Topic, entity, fact, and graph panels remain with discovery-visualization. Queries read
`ctl.stage_progress` through the provisioned PostgreSQL datasource `arxiv-int-postgres`.
Metric labels stay on the bounded name set `stage`, `event`, `worker_state`, `device`, and
`failure_class`. Run ids and shard tokens are table columns, not Prometheus labels.
