{{
  config(
    materialized="table",
    tags=["projections"]
  )
}}

select
  embedding_id as logical_id,
  embedding_id,
  target_id,
  target_kind,
  profile_id,
  dimensions,
  model_digest,
  vector_ref,
  generation_id as source_generation_id,
  contract_version,
  '{{ var("policy_version") }}' as policy_version,
  '{{ var("generation_id") }}' as derived_generation_id
from {{ source("search", "embeddings") }}
where profile_id is not null
