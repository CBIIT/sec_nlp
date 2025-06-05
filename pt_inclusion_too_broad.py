# %%
"""
Collect data
"""

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
import re

engine = create_engine("postgresql://secapp@host.docker.internal:5433/sec")

"""
1. Identify 100 ground truth, inclusion prior therapies (i.e., from CTS API)
"""

pt_inclusions = pd.read_sql(
    """with ideal_trials as (select nct_id from trial_unstructured_criteria group by nct_id having count(*) > 1)
    select nct_id, name, 'n,a' as source from trial_prior_therapies
    where inclusion_indicator = 'TRIAL' and eligibility_criterion = 'inclusion' and nct_id in (select * from ideal_trials)
    order by nct_id limit 100""",
    engine,
)
pt_inclusions.to_csv("pt_inclusions.txt", encoding="utf_8_sig", index=False)

"""
2. Identify the predicted inclusion prior therapies for the same set of trials (i.e., from NLP pipeline)
"""
pt_pred_inclusions = pd.read_sql(
    text(
        "select nct_id, candidate_criteria_text from candidate_criteria where criteria_type_id = 12 and inclusion_indicator = true and nct_id in :nct_ids order by nct_id, display_order"
    ),
    engine,
    params={"nct_ids": tuple(pt_inclusions["nct_id"])},
)
pt_pred_inclusions["candidate_criteria_text"] = pt_pred_inclusions[
    "candidate_criteria_text"
].apply(lambda x: re.sub(r"\(.+\)--- ?", "", x))
pt_pred_inclusions.to_csv("pt_pred_inclusions.txt", encoding="utf_8_sig", index=False)

# %%


def get_unstructured_criteria(nct_id: str):
    return pd.read_sql(
        "select description from trial_unstructured_criteria where nct_id = %s and inclusion_indicator=true order by display_order",
        engine,
        params=(nct_id,),
    )


def get_unstructured_criteria_excl(nct_id: str):
    return pd.read_sql(
        "select description from trial_unstructured_criteria where nct_id = %s and inclusion_indicator=false order by display_order",
        engine,
        params=(nct_id,),
    )


def get_candidate_criteria(nct_id: str):
    return pd.read_sql(
        "select display_order, candidate_criteria_text from candidate_criteria where nct_id = %s and criteria_type_id = 12 order by display_order",
        engine,
        params=(nct_id,),
    )


# %%
nct_id = "NCT05002816"

"""
2. Locate the unstructured eligibility for each trial which serves as the source of truth for the CTRO-identified inclusion prior therapies (`trial_unstructured_criteria`). Useful for checking the derivation of prior therapy abstraction.
"""
get_unstructured_criteria(nct_id).to_csv("tmp.txt", index=False)
# """
# 3. Locate the candidate criteria (`candidate_criteria`) which contain recommended inclusion prior therapies. Helpful for identifying false positives (i.e., "is allowed's but not required's").
# """
# get_candidate_criteria(nct_id).to_csv("tmp2.txt", index=False)

# %%
"""If source is not found, you can check in exclusion criteria."""

get_unstructured_criteria_excl(nct_id).to_csv("tmp.txt", mode="a", index=False)
