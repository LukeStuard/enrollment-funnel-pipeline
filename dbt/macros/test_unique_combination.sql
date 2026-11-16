{#- Fails for any combination of the given columns that appears more than once.
    A small stand-in for dbt_utils.unique_combination_of_columns, so the project
    needs no packages. -#}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as row_count
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
