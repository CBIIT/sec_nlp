import spacy
from spacy.matcher import PhraseMatcher
import sqlite3
import datetime
import progressbar
import argparse



def check_for_concepts(con, nct_id, criteria_type_id, ncit_codes, inclusion_indicator):

    desc_sql = """
    with descendants as
        (
            select descendant from ncit_tc where parent in ({}) 
        )
    select
     nlp.nct_id, nlp.display_order, nlp.ncit_code, nlp.start_index, nlp.end_index ,u.inclusion_indicator,  u.description
 from ncit_nlp_concepts nlp join descendants d on nlp.ncit_code = d.descendant and nlp.nct_id = ? 
 join trial_unstructured_criteria u on nlp.nct_id = u.nct_id  and nlp.display_order = u.display_order and u.inclusion_indicator = ? 
    """.format(', '.join(['?'] * len(ncit_codes)))
    cur = con.cursor()
    cur.execute(desc_sql, [*ncit_codes, nct_id, inclusion_indicator])
    d = cur.fetchall()
   # print(d)

    num_crits_for_trial_sql = """
    select count(*) as num_crits from trial_unstructured_criteria where nct_id = ? and inclusion_indicator = ?
    """
    cur = con.cursor()
    cur.execute(num_crits_for_trial_sql, [nct_id,inclusion_indicator])
    num_crits = cur.fetchone()[0]
    #print(num_crits)
    if num_crits > 1:
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
    elif num_crits == 1:
        # get the min and max and get sentences

        pass

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





#d = check_for_concepts(con, 'NCT00075387', 8, test_code)

#print(d)




get_trials_sql = """
select t.nct_id from trials t left outer join trial_nlp_dates td on t.nct_id = td.nct_id where td.classification_date is null or td.classification_date <= max(t.record_verification_date, t.amendment_date)
"""

cur = con.cursor()
cur.execute(get_trials_sql)
trials_to_classify = cur.fetchall()
print("there are ", len(trials_to_classify), " trials to classify ")
#sys.exit()
#cur.execute('delete from candidate_criteria')
con.commit()
i = 1
for trial in trials_to_classify:
    nct_id = trial[0]
    print("processing ", nct_id, " trial ", i , " of ", len(trials_to_classify))
    cur.execute("delete from candidate_criteria where nct_id = ? ", [nct_id])

    check_for_concepts(con, nct_id, 8, ['C20641'],1)
    check_for_concepts(con, nct_id, 7, ['C51948'],1)
    check_for_concepts(con, nct_id, 6, ['C51951'],1)
    check_for_concepts(con, nct_id, 5, ['C14219'],0)
    check_for_concepts(con, nct_id, 35, ['C4015'],1)
    check_for_concepts(con, nct_id, 1, ['C3910','C16612'],1)


    # PT -- need to split these out for inc/exclusion
    check_for_concepts(con, nct_id , 36, ['C62634','C15313', 'C15329'],1)

    cur.execute('select count(*) from trial_nlp_dates where nct_id = ?', [nct_id] )
    hm = cur.fetchone()[0]
    if hm == 1:
        cur.execute("update trial_nlp_dates set classification_date = ?  where nct_id = ?" ,[datetime.datetime.now() , nct_id])
    else:
        cur.execute("insert into trial_nlp_dates(nct_id, classification_date) values(?,?)", [nct_id, datetime.datetime.now()])
    con.commit()



con.close()
