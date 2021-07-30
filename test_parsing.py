import pyparsing as pp

import re
import sqlite3
import collections

def normalize_numeric_val(crit_num_val, exp, units_val, lower_nonsense, upper_nonsense):
    # Normalize to uL
    exp_multiplier_dict = {'x 10^9': 1000000000, 'x 109': 1000000000, 'x 10^3': 1000, '× 109': 1000000000, 'X 10^9': 1000000000, '*10^9' : 1000000000,
                        '* 10^9': 1000000000,  '*10^9': 1000000000,   '× 10^9': 1000000000, '×109': 1000000000, 'x 10': 10, '× 10^3': 1000, 'x109': 1000000000, 'x10^9': 1000000000,
                           'x10^3': 1000, '× 103': 1000, '×10^9': 1000000000, 'x 10E9': 1000000000, 'x 10^6': 1000000, 'X 109': 1000000000,
                           '×10⁹': 1000000000, 'x 10^4': 10000, '× 10⁹': 1000000000, 'x 10⁹': 1000000000, 'x10E9': 1000000000, 'x 103': 1000, 'x103': 1000}
    unit_normalizer_to_ul_dict = {'/mm^3': 1,  '/uL': 1, 'cells/mm^3': 1,  '/ul': 1,'/ mcL': 1, '/μL': 1, '/mcl': 1, '/mm3': 1, '/µL': 1,'cells/μL': 1,'/μl': 1,'/cu mm': 1,'cells/µl': 1,
                                  '/mcL': 1, '/Ul': 1,  '/cubic[ ]mm': 1, '/cubic millimeters': 1,
                                  '/mL': .001, '/ml': .001,
                                  'K/cumm': 1000, 'k/cumm': 1000, 'K/mcL': 1000, 'k/mcl': 1000, 'K/mm^3': 1000, 'K/uL' : 1000,'THO/uL':1000, 'k/uL': 1000, 'K/UL' : 1000,
                                  '/L': .000001,  '/l': .000001}

    if crit_num_val is not None:
        if crit_num_val >= lower_nonsense and crit_num_val <= upper_nonsense:
            # we have a normalized number already
            norm_num =  crit_num_val
        else:
            norm_num = crit_num_val
            if exp in exp_multiplier_dict:
                norm_num = norm_num * exp_multiplier_dict[exp]
            if units_val in unit_normalizer_to_ul_dict:
                norm_num = norm_num * unit_normalizer_to_ul_dict[units_val]
            norm_num = int(norm_num)
        if norm_num >= lower_nonsense and norm_num <= upper_nonsense:
            return int(norm_num)
        else:
            return None
    else:
        return None


def process_numeric_crit(rs, regex, con, cur, criteria_type_id, ncit_code, lower_nonsense, upper_nonsense):
    greater_than = ('>')
    greater_than_or_eq = (
    '=>', '>=', '≥', 'greater than or equal to', 'more or equal to', 'of at least', 'greater than')
    less_than = ('<', 'less than')
    less_than_or_eq = ('<=', '=<', '≤')

    exponents = collections.Counter()
    units = collections.Counter()

    for r in rs:
        t = r[3]
        parseable = re.sub('[,][0-9]{3}', lambda y: y.group()[1:],
                           t)  # get rid of the commas in numbers to help me stay sane
        g = regex.search(parseable)
        if g is not None:
            newgroups = [s.strip() if s is not None else None for s in g.groups()]
            new_normal_form = str(newgroups)
            new_expression = None
            print(t, newgroups)
            exponents[newgroups[3]] += 1  # gather exponents for analysis
            units[newgroups[4]] += 1  # gather units for analysis
            if newgroups[2] is not None:
                new_num = normalize_numeric_val(float(newgroups[2]), newgroups[3], newgroups[4], lower_nonsense, upper_nonsense)
                print(new_num)
                if newgroups[1] is not None:  # we have a relational
                    new_relational = None
                    if r[2] == 0:  # need to switch the sense from exclusion to inclusion
                        if newgroups[1] in less_than or newgroups[1] in less_than_or_eq:
                            new_relational = '>='
                        elif newgroups[1] in greater_than or newgroups[1] in greater_than_or_eq:
                            new_relational = '<='
                    else:
                        if newgroups[1] in less_than or newgroups[1] in less_than_or_eq:
                            new_relational = '<='
                        elif newgroups[1] in greater_than or newgroups[1] in greater_than_or_eq:
                            new_relational = '>='
                    if new_relational is not None:
                        new_expression = ncit_code + ' ' + new_relational + ' ' + str(new_num)

                        print("inc_exc", r[2], "new normal form ", new_normal_form, "new expression ", new_expression)
            cur.execute(
                """update candidate_criteria set candidate_criteria_norm_form = ?, candidate_criteria_expression = ? 
                   where nct_id = ? and criteria_type_id = ? and display_order = ?
                """, [new_normal_form, new_expression, r[0], criteria_type_id, r[4]])
            con.commit()
        else:
            print(t, "NO MATCH")

    print(exponents)
    print(units)

database_file = "/Users/hickmanhb/sqlite/sec_poc.db"
con = sqlite3.connect(database_file)

cand_sql = """
select nct_id, criteria_type_id, inclusion_indicator, candidate_criteria_text, display_order from
candidate_criteria where criteria_type_id = ? order by nct_id
"""
cur = con.cursor()
cur.execute("update candidate_criteria set candidate_criteria_norm_form = NULL, candidate_criteria_expression = NULL where criteria_type_id = ?",
            [6])
cur.execute(cand_sql, [6])
rs = cur.fetchall()
con.commit()
print("candidate criteria to process: ", len(rs))

tests = ['Platelets ≥ 100 × 10⁹/L;','Platelet count   => 100,000/µL','Platelet count   => 100,000,000,000/µL',
         'Platelets ≥ 10000000000000 × 10⁹/L;',
'Platelets ≥ 10000000000000 × 10^9/L;',
'Platelets ≥ 10000000000000 x 10⁹/L;',
         '(C51951)--- Platelets (PLT) >= 100,000/mm^3',
         '(C51951)--- Platelets >= 100 x 10^9/L',
         '(C51951)--- Platelets >= 100,000/mm^3 (within 7 days prior to leukapheresis)'
         ]



platelets = re.compile(r"""(platelet[ ]count[ ]of|platelet[ ]count[ ]is|platelet[ ]count:|platelets:|platelets|platelet[ ]count|platelets\s*\(plt\))      # first group -  description of test used
                   \s*                             # White space 
                   (\=\>|\>\=|\=\<|\<\=|\<|\>|≥|≤|greater[ ]than[ ]or[ ]equal[ ]to|more[ ]or[ ]equal[ ]to|less[ ]than|of[ ]at[ ]least|greater[ ]than)               # Relational operators
                   \s*                              # More white space
                    (\d+\.?\d*)?    # number
                    
                    \s*([x|×|*]?\s*\d+\^?⁹?E?\*?\d*\s*)?   # scientific notation indicator
                    [ ]?(K/cumm|platelets[ ]per[ ]L|THO/uL|K/uL|[K|[ ]}?/mcL|K/mm\^3|K/cells/mm\^3|/uL|cells[ ]/mm3|/cu[ ]mm|/L|/µL|/mm\^3|cells/µl|/mm3|/[ ]mcL|/mcl|/ml|/l|/cubic[ ]millimeters|/cubic[ ]mm|uL)?
                    
"""
               , re.VERBOSE | re.IGNORECASE | re.UNICODE | re.MULTILINE)

wbc = re.compile(r"""(Leukocyte[ ]count|White[ ]blood[ ]cells[ ]\(WBC\)|White[ ]blood[ ]cell[ ]count[ ]\(WBC\) |White[ ]blood[ ]count[ ]\(WBC\)|White[ ]blood[ ]cell[ ]count[ ]|Leukocytes)   # first group -  description of test used
                   \s*                             # White space 
                   (\=\>|\>\=|\=\<|\<\=|\<|\>|≥|≤|greater[ ]than[ ]or[ ]equal[ ]to|more[ ]or[ ]equal[ ]to|less[ ]than|of[ ]at[ ]least|greater[ ]than)               # Relational operators
                   \s*                              # More white space
                    (\d+\.?\d*)?    # number

                    \s*([x|×|*]?\s*\d+\^?⁹?E?\d*\s*)?   # scientific notation indicator
                    [ ]?(K/cumm|per[ ]L|THO/uL|K/uL|[K|[ ]}?/mcL|K/mm\^3|K/cells/mm\^3|/uL|cells[ ]/mm3|/cu[ ]mm|/L|/µL|/mm\^3|cells/µl|/mm3|/[ ]mcL|/mcl|/ml|/l|/cubic[ ]millimeters|/cubic[ ]mm|uL)?

"""
                       , re.VERBOSE | re.IGNORECASE | re.UNICODE | re.MULTILINE)

process_numeric_crit(rs, platelets, con, cur, 6, 'C51951', 10000, 250000)

cur = con.cursor()
cur.execute("update candidate_criteria set candidate_criteria_norm_form = NULL, candidate_criteria_expression = NULL where criteria_type_id = ?",
            [7])
cur.execute(cand_sql, [7])  # WBC
rs = cur.fetchall()
con.commit()
process_numeric_crit(rs, wbc, con, cur, 7, 'C51948', 500, 500000)

con.close()
