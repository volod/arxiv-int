{{
  config(
    materialized="table",
    tags=["projections"]
  )
}}

select
  fact_id as logical_id,
  fact_id,
  subject_object_id,
  predicate_id,
  object_object_id,
  document_id,
  span_id,
  chunk_id,
  status,
  generation_id as source_generation_id,
  contract_version,
  '{{ var("policy_version") }}' as policy_version,
  '{{ var("generation_id") }}' as derived_generation_id
from {{ source("kg", "facts") }}
where object_object_id is not null
  and status in ('accepted', 'proposed')
