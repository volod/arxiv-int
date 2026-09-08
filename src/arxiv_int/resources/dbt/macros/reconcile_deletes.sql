{% macro reconcile_deletes(key_column, source_relation) -%}
    {% if is_incremental() and var("reconcile_deletes", true) %}
        delete from {{ this }}
        where {{ key_column }} not in (select {{ key_column }} from {{ source_relation }})
    {% endif %}
{%- endmacro %}
