{{
  config(
    materialized="table",
    tags=["projections"]
  )
}}

select
  object_id as logical_id,
  object_id,
  object_type,
  preferred_label,
  review_state,
  generation_id as source_generation_id,
  contract_version,
  '{{ var("policy_version") }}' as policy_version,
  '{{ var("generation_id") }}' as derived_generation_id
from {{ source("kg", "objects") }}
