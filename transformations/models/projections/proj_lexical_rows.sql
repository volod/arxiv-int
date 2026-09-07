{{
  config(
    materialized="table",
    tags=["projections"]
  )
}}

select
  c.chunk_id as logical_id,
  c.chunk_id,
  c.document_id,
  d.title,
  c.text as body,
  c.chunk_id as identifiers,
  d.language,
  c.chunker_id,
  c.generation_id as source_generation_id,
  c.contract_version,
  '{{ var("policy_version") }}' as policy_version,
  '{{ var("generation_id") }}' as derived_generation_id
from {{ source("corpus", "chunks") }} as c
left join {{ source("corpus", "documents") }} as d using (document_id)
