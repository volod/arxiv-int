{% macro generate_alias_name(custom_alias=none, node=none) -%}
    {%- if node is none or node.resource_type != "model" -%}
        {{ custom_alias if custom_alias is not none else node.name }}
    {%- else -%}
        {%- set generation = var("generation_id") -%}
        {%- set base = custom_alias if custom_alias is not none else node.name -%}
        {{ base }}__g_{{ generation }}
    {%- endif -%}
{%- endmacro %}
