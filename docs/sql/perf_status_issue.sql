with descendants as (
    select
        descendant
    from
        ncit_tc
    where
        parent in ('C25218', 'C1908', 'C62634', 'C163758')
),
descendants_to_remove as (
    select
        descendant
    from
        ncit_tc
    where
        parent in ('C25294', 'C102116')
)
select
    nlp.display_order,
    nlp.ncit_code,
    nlp.start_index,
    nlp.end_index,
    u.inclusion_indicator,
    substring(
        u.description,
        nlp.start_index,
        nlp.end_index - nlp.start_index + 1
    ),
    ncit.pref_name
from
    ncit_nlp_concepts nlp
    join descendants d on nlp.ncit_code = d.descendant
    and nlp.nct_id = 'NCT00801489'
    join trial_unstructured_criteria u on nlp.nct_id = u.nct_id
    and nlp.display_order = u.display_order
    and u.inclusion_indicator = true
    and nlp.ncit_code not in (
        select
            descendant as ncit_code
        from
            descendants_to_remove
    )
    join ncit on nlp.ncit_code = ncit.code
order by
    nlp.display_order,
    nlp.start_index;
