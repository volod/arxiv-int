{{
  config(
    materialized="incremental",
    unique_key="document_id",
    incremental_strategy="delete+insert",
    on_schema_change="sync_all_columns",
    pre_hook=["{{ reconcile_deletes('document_id', ref('stg_documents')) }}"],
    tags=["fixture", "intermediate"]
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
