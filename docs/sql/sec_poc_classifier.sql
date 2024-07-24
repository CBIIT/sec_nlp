with descendants as (
    select
        descendant
    from
        ncit_tc
    where
        parent in :classifier_codes -- Get descendants of the classifier codes.
        -- The classifier code for Performance Status, for example, would be C20641.
        -- Likewise, the classifier codes for Biomarkers, for example, are C3910, C16612, and C26548.
),
descendants_to_remove as (
    select
        descendant
    from
        ncit_tc
    where
        parent in :classifier_codes_to_omit -- Some descendants are omitted from classification for various reasons.
)
select
    nlp.nct_id,
    nlp.display_order,
    nlp.ncit_code,
    nlp.start_index,
    nlp.end_index,
    u.inclusion_indicator,
    u.description
from
    -- For a given NCT ID, join its NLP concepts with any descendants of the classifier code(s).
    ncit_nlp_concepts nlp
    join descendants d on nlp.ncit_code = d.descendant
    and nlp.nct_id = :nct_id
    join trial_unstructured_criteria u on nlp.nct_id = u.nct_id -- Join the unstructured criteria from which the code/span of text originates
    and nlp.display_order = u.display_order
    and u.inclusion_indicator = :inc_indicator
    and nlp.ncit_code not in (
        select
            descendant as ncit_code
        from
            descendants_to_remove
    );
