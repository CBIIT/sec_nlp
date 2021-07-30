import pyparsing as pp

import re
import sqlite3
import collections
def gen_plt_expression(in_exc_flag, normalized_input):
    pass

database_file = "/Users/hickmanhb/sqlite/sec_poc.db"
con = sqlite3.connect(database_file)

cand_sql = """
select nct_id, criteria_type_id, inclusion_indicator, candidate_criteria_text from
candidate_criteria where criteria_type_id = ? order by nct_id
"""
cur = con.cursor()
cur.execute(cand_sql, [6])
rs = cur.fetchall()
con.commit()
con.close()
print("candidate criteria to process: ", len(rs))

tests = ['Platelets ≥ 100 × 10⁹/L;','Platelet count   => 100,000/µL','Platelet count   => 100,000,000,000/µL',
         'Platelets ≥ 10000000000000 × 10⁹/L;',
'Platelets ≥ 10000000000000 × 10^9/L;',
'Platelets ≥ 10000000000000 x 10⁹/L;',
         '(C51951)--- Platelets (PLT) >= 100,000/mm^3',
         '(C51951)--- Platelets >= 100 x 10^9/L',
         '(C51951)--- Platelets >= 100,000/mm^3 (within 7 days prior to leukapheresis)'
         ]



platelets = re.compile(r"""(platelet[ ]count[ ]of|platelets|platelet[ ]count|platelets\s*\(plt\))      # first group -  description of test used
                   \s*                             # White space 
                   (\=\>|\>\=|\=\<|\<\=|\<|\>|≥|≤|greater[ ]than[ ]or[ ]equal[ ]to|more[ ]or[ ]equal[ ]to)               # Relational operators
                   \s*                              # More white space
                    (\d+\.?\d*)?    # number
                    
                    (\s*[x|×]?\s*\d+\^?⁹?E?\d*\s*)?   # scientific notation indicator
                    [ ]?(K/cumm|[K|[ ]}?/mcL|cells/mm\^3|/uL|cells[ ]/mm3|/cu[ ]mm|/L|/µL|/mm\^3|cells/µl|/mm3|/[ ]mcL|/mcl|/ml|/l)?
                    
"""
               , re.VERBOSE | re.IGNORECASE | re.UNICODE | re.MULTILINE)


greater_than = ('>')
greater_than_or_eq = ('=>','>=','≥', 'greater than or equal to', 'more or equal to' )
less_than = ('<')
less_than_or_eq = ('<=', '=<', '≤')

exponents = collections.Counter()
units = collections.Counter()

for r in rs:
    t = r[3]
    parseable = re.sub('[,][0-9]{3}', lambda y: y.group()[1:], t) # get rid of the commas in numbers to help me stay sane
    g = platelets.search(parseable)
    if g is not None:
        print(t, g.groups())
        exponents[g[3]] += 1
        units[g[4]] += 1
    else:
        print(t, "NO MATCH")

print(exponents)
print(units)