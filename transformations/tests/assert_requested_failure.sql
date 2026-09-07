{{ config(tags=["quality"]) }}

select 1 as forced_failure
where '{{ var("fail_tests", "false") }}' = 'true'
