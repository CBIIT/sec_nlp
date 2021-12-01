import spacy
from spacy.matcher import PhraseMatcher
import sqlite3
import datetime
import argparse



def check_for_concepts(con, nct_id, criteria_type_id, ncit_codes, inclusion_indicator, ncit_codes_to_remove = '', include_descendants = True):

    if include_descendants:
        desc_sql = """
        with descendants as
            (
                select descendant from ncit_tc where parent in ({desc_1}) 
            ),
        descendants_to_remove as
            (
                select descendant from ncit_tc where parent in ({desc_to_remove}) 
            )    
       
          select
        nlp.nct_id, nlp.display_order, nlp.ncit_code, nlp.start_index, nlp.end_index ,u.inclusion_indicator,  u.description
    from ncit_nlp_concepts nlp join descendants d on nlp.ncit_code = d.descendant and nlp.nct_id = ?
    join trial_unstructured_criteria u on nlp.nct_id = u.nct_id  and nlp.display_order = u.display_order and u.inclusion_indicator = ?
        and nlp.ncit_code not in (select descendant as ncit_code from descendants_to_remove) 
        """.format(desc_1=', '.join(['?'] * len(ncit_codes)),
                   desc_to_remove=', '.join(['?'] * len(ncit_codes_to_remove)))
    else:
        desc_sql = """
        select
               nlp.nct_id, nlp.display_order, nlp.ncit_code, nlp.start_index, nlp.end_index ,u.inclusion_indicator,  u.description
           from ncit_nlp_concepts nlp 
           join trial_unstructured_criteria u on nlp.nct_id = u.nct_id  and nlp.display_order = u.display_order and u.inclusion_indicator = ?
               and nlp.ncit_code in ( {good_codes} ) and nlp.ncit_code not in ({codes_to_remove}) 
                and nlp.nct_id = ?
                """.format(good_codes=', '.join(['?'] * len(ncit_codes)),
                          codes_to_remove=', '.join(['?'] * len(ncit_codes_to_remove)))

    cur = con.cursor()
    if len(ncit_codes_to_remove) == 0:
        if include_descendants:
            cur.execute(desc_sql, [*ncit_codes, nct_id, inclusion_indicator])
        else:
            cur.execute(desc_sql, [inclusion_indicator, *ncit_codes, nct_id])
    else:
        if include_descendants:
            cur.execute(desc_sql, [*ncit_codes, *ncit_codes_to_remove, nct_id, inclusion_indicator])
        else:
            cur.execute(desc_sql, [inclusion_indicator, *ncit_codes,  *ncit_codes_to_remove,nct_id])
    d = cur.fetchall()
   # print(d)

    num_crits_for_trial_sql = """
    select count(*) as num_crits from trial_unstructured_criteria where nct_id = ? and inclusion_indicator = ?
    """
    cur = con.cursor()
    cur.execute(num_crits_for_trial_sql, [nct_id,inclusion_indicator])
    num_crits = cur.fetchone()[0]
    #print(num_crits)
    if num_crits >= 1:
        # Iterate through and get the distinct criteria
        t = set()
        for crit in d:
            t.add( (crit[6], crit[1], crit[5] ))

        for c in t:
           # print(crit)
            ins_sql = """
            insert into candidate_criteria(nct_id, criteria_type_id,  candidate_criteria_text, display_order,inclusion_indicator) values (?,?,?,?,?)
            """
            cur.execute(ins_sql, [nct_id, criteria_type_id, '('+ str(ncit_codes) + ')--- '+c[0],c[1] , c[2]])
        con.commit()


    return []


def get_descendants(con, ncit_code):

    sql = """
    select descendant from ncit_tc where parent = $1
    """
    cur = con.cursor()
    cur.execute(sql, [ncit_code])
    rs = cur.fetchall()
    con.commit()
    return rs

#
#
#

parser = argparse.ArgumentParser(description='Create candidate criteria texts')

parser.add_argument('--dbfilename', action='store', type=str, required=True)
args = parser.parse_args()

con = sqlite3.connect(args.dbfilename)

get_trials_sql = """
select t.nct_id , t.record_verification_date, t.amendment_date,td.tokenized_date, td.classification_date from trials t 
left outer join trial_nlp_dates td on t.nct_id = td.nct_id 
where td.classification_date is null or td.classification_date <= td.tokenized_date
"""

cur = con.cursor()
cur.execute("""
select count(distinct nct_id) as num_trials_to_delete  from candidate_criteria cc where cc.nct_id not in (select nct_id from trials)
""")
num_to_delete = cur.fetchone()[0]
print("there are ", num_to_delete, 'trials that are no longer that have NLP derived criteria. Deleting those.')
cur.execute("""
delete from candidate_criteria where nct_id not in (select nct_id from trials)
""")
con.commit()

cur.execute(get_trials_sql)
trials_to_classify = cur.fetchall()
print("there are ", len(trials_to_classify), " trials to classify ")
print(f"{'Count' : <8}{'  NCT ID': <15}{'RVD' : ^30}{'Amendment Date' : ^30}{'Tokenized Date' : ^30}{'Prior Classification Date' : ^30}")
#sys.exit()
#cur.execute('delete from candidate_criteria')
con.commit()
i = 1
for trial in trials_to_classify:
    nct_id = trial[0]
    print(f"{i: <8}{trial[0]: <15}{trial[1] or '': ^30}{trial[2] or '': ^30}{trial[3] or '': ^30}{trial[4] or '': ^30}")

    cur.execute("delete from candidate_criteria where nct_id = ? ", [nct_id])

    check_for_concepts(con, nct_id, 8, ['C20641'],1, ncit_codes_to_remove=['C116664', 'C161964'])   # Performance status
    check_for_concepts(con, nct_id, 7, ['C51948'],1, include_descendants=False) # WBC
    check_for_concepts(con, nct_id, 6, ['C51951'],1)    # PLT
    check_for_concepts(con, nct_id, 5, ['C14219'],0)    # HIV
    check_for_concepts(con, nct_id, 35, ['C4015'],0)    # BMETS
    #check_for_concepts(con, nct_id, 1, ['C3910','C16612'],0, ncit_codes_to_remove= ['C90505'] )    # BIOMARKER EXC
    check_for_concepts(con, nct_id, 1, ['C3910','C16612', 'C26548'],0, ncit_codes_to_remove= ['C90505'])    # BIOMARKER EXC
    check_for_concepts(con, nct_id, 2, ['C3910','C16612', 'C26548'],1, ncit_codes_to_remove= ['C90505'] )    # BIOMARKER INC


    # PT -- need to split these out for inc/exclusion
    check_for_concepts(con, nct_id , 36, ['C62634','C15313', 'C15329'],1)  # PT INC
    check_for_concepts(con, nct_id , 37, ['C62634','C15313', 'C15329'],0)  # PT EXC


    cur.execute('select count(*) from trial_nlp_dates where nct_id = ?', [nct_id] )
    hm = cur.fetchone()[0]
    if hm == 1:
        cur.execute("update trial_nlp_dates set classification_date = ?  where nct_id = ?" ,[datetime.datetime.now() , nct_id])
    else:
        cur.execute("insert into trial_nlp_dates(nct_id, classification_date) values(?,?)", [nct_id, datetime.datetime.now()])
    con.commit()
    i = i + 1


con.close()
