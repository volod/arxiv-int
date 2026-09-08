{{
  config(
    materialized="incremental",
    unique_key="document_id",
    incremental_strategy="delete+insert",
    on_schema_change="sync_all_columns",
    tags=["fixture", "intermediate", "reconcile"]
  )
}}

select
  document_id,
  title,
  content_hash,
  source_generation_id,
  contract_version,
  source_schema,
  source_table,
  '{{ var("policy_version") }}' as policy_version,
  '{{ var("generation_id") }}' as derived_generation_id
from {{ ref("stg_documents") }}
where content_hash not in (
  select content_hash
  from {{ ref("stg_source_tombstones") }}
  where last_occurrence
)
