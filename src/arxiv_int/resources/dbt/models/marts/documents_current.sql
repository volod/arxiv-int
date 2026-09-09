{{
  config(
    materialized="table",
    tags=["fixture", "marts"]
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
  policy_version,
  derived_generation_id
from {{ ref("int_documents_current") }}
