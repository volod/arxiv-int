{{
  config(
    materialized="view",
    tags=["fixture", "staging", "reconcile"]
  )
}}

select
  tombstone_id,
  occurrence_id,
  silo_id,
  relative_path,
  content_hash,
  scan_id,
  generation_id,
  last_occurrence,
  reason,
  'ctl' as source_schema,
  'source_tombstone' as source_table
from {{ source("ctl_reconcile", "source_tombstone") }}
