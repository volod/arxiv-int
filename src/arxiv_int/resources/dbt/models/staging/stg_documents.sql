{{
  config(
    materialized="view",
    tags=["fixture", "staging"]
  )
}}

select
  document_id,
  title,
  content_hash,
  generation_id as source_generation_id,
  contract_version,
  'corpus' as source_schema,
  'documents' as source_table
from {{ source("corpus", "documents") }}
