import spacy
from spacy.matcher import PhraseMatcher
import sqlite3
import datetime
import progressbar
import argparse


nlp = spacy.load("en_core_web_sm")
matcher = PhraseMatcher(nlp.vocab, attr='LOWER')

parser = argparse.ArgumentParser(description='Parse NCI codes from the text')

parser.add_argument('--dbfilename', action='store', type=str, required=True)
args = parser.parse_args()
con = sqlite3.connect(args.dbfilename)

start_nlp_init = datetime.datetime.now()
print("Initializing NLP at ", start_nlp_init)
rs = []
sql = '''select code, synonyms from ncit 
where (concept_status is null or (concept_status not like '%Obsolete%' and concept_status not like '%Retired%') ) 
/* and (lower(synonyms) like '%chemotherapy%' or lower(synonyms) like '%ecog%' or lower(synonyms) like '%white blood cell%') */
'''
cur = con.cursor()
cur.execute(sql)
r = cur.fetchall()
for rec in r:
    c = rec[0]
    synonyms = rec[1].split('|')
    newlist = list(zip([c] * len(synonyms), synonyms))
    rs.extend(newlist)
   # print(rs)

terms = rs
# Only run nlp.make_doc to speed things up
patterns = [nlp.make_doc(v[1]) for v in rs]
matcher.add("TerminologyList", patterns)

end_nlp_init = datetime.datetime.now()
print("NLP Init complete at", end_nlp_init, " elapsed time = ", end_nlp_init - start_nlp_init)
cur.execute('delete from ncit_nlp_concepts')
con.commit()
#doc = nlp(
#"""
#Any form of primary or secondary immunodeficiency; must have recovered immune competence after chemotherapy or radiation therapy as evidenced by lymphocyte counts (> 500/mm^3), white blood cell (WBC) (> 3,000/mm^3) or absence of opportunistic infections (Turnstile II - Chemotherapy/Cell Infusion Exclusion Criteria)
#""")

get_crit_sql = """
    select nct_id, display_order, description  from trial_unstructured_criteria 
order by nct_id, display_order
/* limit 10000 */  
"""
ins_code_sql = """
    insert into ncit_nlp_concepts(nct_id, display_order, ncit_code, span_text, start_index, end_index) values (?,?,?,?,?,?)
"""
get_best_ncit_code_sql_for_span = """
select code from ncit where lower(pref_name) = ? and 
lower(pref_name) not in ('i', 'ii', 'iii', 'iv', 'v', 'set', 'all', 'at', 'is', 'and', 'or', 'to', 'a', 'be', 'for', 'an', 'as', 'in', 'of', 'x', 'are', 'no', 'any', 'on', 'who', 'have', 't', 'who', 'at') 
"""

get_ncit_code_sql_for_span = """
select distinct code from ncit_syns where l_syn_name = ? and
 l_syn_name not in ('i', 'ii', 'iii', 'iv', 'v', 'set', 'all' , 'at', 'is', 'and', 'or', 'to', 'a', 'be', 'for', 'an', 'as', 'in', 'of', 'x', 'are', 'no', 'any', 'on', 'who', 'have', 't', 'who', 'at') 
"""

cur.execute(get_crit_sql)
con.commit()
crits = cur.fetchall()
bar = progressbar.ProgressBar(maxval=len(crits),
                              widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
bar.start()
i=0

for crit in crits:
    doc = nlp(crit[2])


    matches = matcher(doc)
    spans = []
    for match_id, start, end in matches:
        span = doc[start:end]
        spans.append(doc[start:end])
      #  print(span.text)

   # ncit_set = set()
    filtered_spans = spacy.util.filter_spans(spans)
   # print(filtered_spans)
    for f in filtered_spans:
       # print(f.lower_)
        try:
            float(f.lower_)
            is_a_float = True
        except:
            is_a_float = False

        if(not is_a_float):
            cur.execute(get_best_ncit_code_sql_for_span, [f.lower_])
            bcodes = cur.fetchall()
            if len(bcodes) > 0:
                for one_code in bcodes :
                    cur.execute(ins_code_sql, [crit[0], crit[1], one_code[0], f.lower_, f.start_char, f.end_char])
            else:
                cur.execute(get_ncit_code_sql_for_span, [f.lower_])
                rcodes = cur.fetchall()
                for one_code in rcodes:
                    cur.execute(ins_code_sql, [crit[0], crit[1], one_code[0], f.lower_, f.start_char, f.end_char])
    con.commit()
    i += 1
    bar.update(i)

con.close()

run_done  = datetime.datetime.now()
print("run complete - at ", run_done, "elapsed time ", run_done - start_nlp_init)