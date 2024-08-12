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
        -- For example, C161964 is unrelated to Performance Status, but one of its synonyms matches ECOG (performance status).
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
    join descendants d on nlp.ncit_code = d.descendant -- Keep NLP concepts that are descendants of parent classifier code
    and nlp.nct_id = :nct_id -- for the given NCT trial ID
    join trial_unstructured_criteria u on nlp.nct_id = u.nct_id -- Gather the unstructured criteria from which the code/span originates
    and nlp.display_order = u.display_order -- Display order helps narrow down the original unstructured criterion
    and u.inclusion_indicator = :inc_indicator -- as does inclusion indicator
    and nlp.ncit_code not in (
        select
            descendant as ncit_code
        from
            descendants_to_remove -- Drop any NLP concepts that match descendants to remove
    );
