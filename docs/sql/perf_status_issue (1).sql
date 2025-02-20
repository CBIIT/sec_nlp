with d_codes as (
    select
        code as ncit_code
    from
        good_pt_codes
)
select
    distinct sv.ncit_code,
    sv.display_order,
    sv.pref_name
from
    nlp_data_tab sv
    join d_codes d on sv.ncit_code = d.ncit_code
where
    nct_id = 'NCT00801489'
    and display_order = 3
    and length(sv.span_text) > 3;

-- ncit_code,pref_name,span_text,inclusion_indicator
