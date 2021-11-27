import re
import sqlite3
import collections
import argparse
import datetime
from create_performance_expression import parse_performance_string



def normalize_numeric_val(crit_num_val, exp, units_val, lower_nonsense, upper_nonsense):
    # Normalize to uL
    exp_multiplier_dict = {'x 10^9': 1000000000, 'x 109': 1000000000, 'x 10^3': 1000, '× 109': 1000000000,
                           'X 10^9': 1000000000, '*10^9': 1000000000,
                           '* 10^9': 1000000000, '*10^9': 1000000000, '× 10^9': 1000000000, '×109': 1000000000,
                           'x 10': 10, '× 10^3': 1000, 'x109': 1000000000, 'x10^9': 1000000000,
                           'x10^3': 1000, '× 103': 1000, '×10^9': 1000000000, 'x 10E9': 1000000000, 'x 10^6': 1000000,
                           'X 109': 1000000000,
                           '×10⁹': 1000000000, 'x 10^4': 10000, '× 10⁹': 1000000000, 'x 10⁹': 1000000000,
                           'x10E9': 1000000000, 'x 103': 1000, 'x103': 1000}
    unit_normalizer_to_ul_dict = {'/mm^3': 1, '/uL': 1, 'cells/mm^3': 1, '/ul': 1, '/ mcL': 1, '/μL': 1, '/mcl': 1,
                                  '/mm3': 1, '/µL': 1, 'cell/uL': 1, 'cells/μL': 1, '/μl': 1, '/cu mm': 1, 'cells/µl': 1,
                                  '/mcL': 1, '/Ul': 1, '/cubic[ ]mm': 1, '/cubic millimeters': 1,
                                  '/mL': .001, '/ml': .001,
                                  'K/cumm': 1000, 'k/cumm': 1000, 'K/mcL': 1000, 'k/mcl': 1000, 'K/mm^3': 1000,
                                  'K/uL': 1000, 'THO/uL': 1000, 'k/uL': 1000, 'K/UL': 1000,
                                  '/L': .000001, '/l': .000001}

    if crit_num_val is not None:
        if crit_num_val >= lower_nonsense and crit_num_val <= upper_nonsense:
            # we have a normalized number already
            norm_num = crit_num_val
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
        '=>', '>=', '≥', '>','greater than or equal to', 'more or equal to', 'of at least', 'greater than')
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
            newgroups_all = [s.strip() if s is not None else None for s in g.groups()]
            newgroups = list(dict.fromkeys([i for i in newgroups_all if i]))
            new_normal_form = str(newgroups)
            new_expression = None
            print(t, newgroups)
           # exponents[newgroups[3]] += 1  # gather exponents for analysis
           # units[newgroups[4]] += 1  # gather units for analysis
            exponent = None
            units = None
            if len(newgroups) == 4:
                exponent = None
                units = newgroups[3]
            elif len(newgroups) == 5:
                exponent = newgroups[3]
                units = newgroups[4]
            elif len(newgroups) == 3:
                exponent = None
                units = None
            if len(newgroups) >=3 and newgroups[2] is not None and newgroups[2].isnumeric():
                new_num = normalize_numeric_val(float(newgroups[2]), exponent, units, lower_nonsense,
                                                upper_nonsense)
            #    print(new_num)
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
                """update candidate_criteria set candidate_criteria_norm_form = ?, candidate_criteria_expression = ? , 
                generated_date = ?, marked_done_date = NULL 
                 
                   where nct_id = ? and criteria_type_id = ? and display_order = ?
                """, [new_normal_form, new_expression, datetime.datetime.now(), r[0], criteria_type_id, r[4]])
            #con.commit()
        else:
            print(t, "NO MATCH")
            cur.execute(
                """update candidate_criteria set candidate_criteria_norm_form = ?, candidate_criteria_expression = ? , 
                generated_date = ?, marked_done_date = NULL 

                   where nct_id = ? and criteria_type_id = ? and display_order = ?
                """, ['NO MATCH', 'NO MATCH', datetime.datetime.now(), r[0], criteria_type_id, r[4]])

    #print(exponents)
    #print(units)


parser = argparse.ArgumentParser(description='Generate candidate expressions')

parser.add_argument('--dbfilename', action='store', type=str, required=True)
args = parser.parse_args()
con = sqlite3.connect(args.dbfilename)
cur = con.cursor()

trials_to_process_sql = """
select distinct cc.nct_id
from candidate_criteria cc join trial_nlp_dates nlp on cc.nct_id = nlp.nct_id
where (cc.generated_date is  NULL or cc.generated_date < nlp.classification_date) and cc.criteria_type_id in (6,7)
"""

cur.execute(trials_to_process_sql)
trials = cur.fetchall()

print("There are ", len(trials), " with criteria to process")

platelets = re.compile(r"""(platelet[ ]count[ ]of|platelet[ ]count[ ]is|platelet[ ]count:|platelets:|platelets|platelet[ ]count|platelets\s*\(plt\))      # first group -  description of test used
                   \s*                             # White space 
                   (\=\>|\>\=|\=\<|\<\=|\<|\>|≥|≤|greater[ ]than[ ]or[ ]equal[ ]to|more[ ]or[ ]equal[ ]to|less[ ]than|of[ ]at[ ]least|greater[ ]than)               # Relational operators
                   \s*                              # More white space
                    (\d+\.?\d*)?    # number

                    \s*([x|×|*]?\s*\d+\^?⁹?E?\*?\d*\s*)?   # scientific notation indicator
                    [ ]?(K/cumm|platelets[ ]per[ ]L|THO/uL|K/uL|[K|[ ]}?/mcL|K/mm\^3|K/cells/mm\^3|/uL|cells[ ]/mm3|/cu[ ]mm|/L|/µL|/mm\^3|cells/µl|/mm3|/[ ]mcL|/mcl|/ml|/l|/cubic[ ]millimeters|/cubic[ ]mm|uL)?

"""
                       , re.VERBOSE | re.IGNORECASE | re.UNICODE | re.MULTILINE)

wbc = re.compile(r"""(Leukocyte[ ]count
                       |Total[ ]White[ ]Blood[ ]Cell[ ]count[ ]\(WBC\) 
                       |White[ ]blood[ ]cells[ ]\(WBC\)
                       |White[ ]blood[ ]cell[ ]\(WBC\)
                       |White[ ]blood[ ]cells[ ]\(WBC\)[ ]counts 
                       |White[ ]blood[ ]cell[ ]\(WBC\)[ ]counts
                       |White[ ]blood[ ]cells
                       |White[ ]blood[ ]cell
                       |White[ ]blood[ ]cell[ ]\(WBC[ ]\) 
                       |White[ ]blood[ ]cell[ ]\(WBC\)[ ]count 
                       |White[ ]blood[ ]cell[ ]count[ ]\(WBC\) 
                       |White[ ]blood[ ]count[ ]\(WBC\)
                       |White[ ]blood[ ]cells[ ]\(WBCs\)
                       |White[ ]blood[ ]cell[ ]\(WBC\)[ ]count[ ]of 
                       |White[ ]blood[ ]cell[ ]count[ ]must[ ]be
                       |White[ ]blood[ ]cell[ ]\(WBC\)[ ]value[ ]of
                       |White[ ]blood[ ]cell[ ]count[ ]of
                       |White[ ]blood[ ]cell[ ]count[ ]
                       |WBC[ ]count 
                       |WBC
                       |Leukocytes:
                       |Leukocytes)   # first group -  description of test used
                   \s*                             # White space 
                   (\=\>|\>\=|\=\<|\<\=|\<|\>|≥|≤|greater[ ]than[ ]or[ ]equal[ ]to|more[ ]or[ ]equal[ ]to|less[ ]than|of[ ]at[ ]least|greater[ ]than)               # Relational operators
                   \s*                              # More white space
                    (\d+[\.,]*\d*)?    # number
                    #(\d+|\d{1,3}(,\d{3})*)(\.\d+)?
                    \s*([x|×|*]?\s*\d+\^?⁹?E?\d*\s*)?   # scientific notation indicator
                    [ ]?(K/cumm|per[ ]L|THO/uL|K/uL|[K|[ ]}?/mcL|K/mm\^3|K/cells/mm\^3|/uL|cells[ ]/mm3|/cu[ ]mm|/L|/µL|/mm\^3|cells/µl|/mm3|/[ ]mcL|/mcl|/ml|/l|/cubic[ ]millimeters|/cubic[ ]mm|uL)?

"""
                 , re.VERBOSE | re.IGNORECASE | re.UNICODE | re.MULTILINE)

ecog_perf_re = re.compile(r""" (
                                 # (\bECOG\/Zubrod) 
                                #| \(*\becog\)* 
                                #|  (\(*\bzubrod\)* ) 
                                 (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\)[ ]\(Zubrod\))
                                | (most[ ]recent[ ]zubrod)

                                 |  (zubrod) 
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\)[ ]-[ ]American[ ]College[ ]of[ ]Radiology[ ]Imaging[ ]Network[ ]\(ACRIN\))
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\)-American[ ]College[ ]of[ ]Radiology[ ]Imaging[ ]Network[ ]\(ACRIN\))

                                | (ECOG\-ACRIN)
                                | (ECOG\/Zubrod) 
                                | (Eastern[ ]Cooperation[ ]Oncology[ ]Group[ ]\(ECOG\))
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\)[ ]\(World[ ]Health[ ]Organization[ ]\[WHO\]/Gynecologic[ ]Oncology[ ]Group[ ]\[GOG\]/Zubrod[ ]score\))
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group/Gynecologic[ ]Oncology[ ]Group[ ]\(ECOG/GOG\)) 
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]Performance[ ]Status[ ]\(ECOG[ ]PS\) )
                                 | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\)) 
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group) 
                                | (Eastern[ ]Cooperative[ ]Group[ ]\(ECOG\)) 
                                | (Gynecological[ ]Oncology[ ]Group[ ]\(GOG\)) 
                                 | (Gynecologic[ ]Oncology[ ]Group[ ]\(GOG\))

                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\) ) 
                                | (ECOG) 
                                ) 

                                (\s*(performance)*[ ](scale|status[ ]must[ ]be|status|scores|status[ ]score|status[ ]grade|score|)(of)*(\:)*(must[ ]be)* )
                                 ([ ]\(PS\))*
                               #  #([ ]\(\d{1,3}\))| ([ ]\(PS\))*
                               # ([ ]{0,1}\bmust[ ]be)*
                               # # \s*(\bbetween)*\s*(\bof)*(\(PS\))*(\bof)*\:* # first group -  ecog name stuff - ecog with an optional closing paren , performance and then scale or status
                               ( (\s*(\bbetween)*)
                               | (\s*(\bof)*(\(PS\))*))
                               #|(\bof*\:*))* # first group -  ecog name stuff - ecog with an optional closing paren , performance and then scale or status
#
                                \s*
                                (
                                  (\d[ ]\-[ ]\d) 
                                  | (\=\<[ ]\d\-\d) 
                                 |(\d[ ]–[ ]\d) 
                                 |(\d-[ ]\d)
                                | (\=\<\s*\d)  # =< 2 etc
                                |(\d\-\d)  # 0-2 etc
                                 |(\d‐\d)
                                | (\<\s*\d )
                                | (\>\=\s*\d )# >= 2 etc
                                | (\=\<\s*\d-\d)  # =< 0-1 glop
                                | (\=\s*\d)
                                | (≤\s*\d)
                                | (less[ ]than[ ]or[ ]equal[ ]to[ ]\d-\d) 
                                | (less[ ]than[ ]or[ ]equal[ ]to[ ]\d) 
                                |(\d[ ]\bto[ ]\d) # 0 to 1 etc
                                |(\d,[ ]{0,1}\d[ ]{0,1}or[ ]\d) 
                                |(\d,[ ]{0,1}\d,[ ]{0,1}or[ ]{0,1}\d)
                                |(\d,\d,[ ]\bor[ ]\d)
                                |(\d,[ ]\d,[ ]\d)
                                |(\d[ ]or\d)|(\d[ ]or[ ]\d)
                                |(\d,[ ]{0,1}\d,[ ]{0,1}\d[,]{0,1}[ ]{0,1}or[ ]{0,1}\d)
                                | \(\d\-\d\) 
                                ) 

                               # \s*
"""
                          , re.VERBOSE | re.IGNORECASE | re.UNICODE | re.MULTILINE)

karnofsky_lansky_perf_re = re.compile(r"""
                                 (\bkarnofsky|\blansky)
                                 \s*
                                 (     (\bperformance[ ]status[ ]\(kps\)[ ]score[ ]of)
                                     |(\bperformance[ ]status[ ]\(kps\)[ ]of)
                                      |(\bperformance[ ]scale[ ]score)
									 |(\bperformance[ ]scale[ ]of)
									 |(\bperformance[ ]status[ ]score[ ]of)
									  |(\bperformance[ ]status[ ]of)
                                    |(\bperformance[ ]score[ ]of)
                                    |(\bperformance[ ]score[ ]\(kps\))
                                     |(\bperformance[ ]scale[ ]\(kps\))
                                    |(\bperformance[ ]status[ ]score)
                                      |(\bperformance[ ]status[ ]\(kps\))
                                    |(\bperformance[ ]scale)
                                    |(\bperformance[ ]status)
                                    |(\bperformance[ ]score)
                                    |(\bscore)
                                  )*

                                 \s
                                  (\>\=|\=\>|\>\=|\=\<|\<\=|\<|\>|≥|≤|greater[ ]than[ ]or[ ]equal[ ]to|greater[ ]than|at[ ]least)
                                 \s*
                                 (\d\d)
                                 \s*

"""
                                      , re.VERBOSE | re.IGNORECASE | re.UNICODE | re.MULTILINE)

cand_sql = """
select nct_id, criteria_type_id, inclusion_indicator, candidate_criteria_text, display_order from
candidate_criteria where criteria_type_id = ?  and nct_id = ?
"""
i = 1
for t in trials:
    print('Processing ', t[0], ' trial ', str(i), 'of', len(trials))
    for crit_info in [{'criteria_type_id': 6, 're_name': platelets, 'lower_nonsense': 10000, 'upper_nonsense': 250000, 'ncit_code': 'C51951'},
                       {'criteria_type_id': 7, 're_name': wbc, 'lower_nonsense': 500, 'upper_nonsense': 500000, 'ncit_code': 'C51948' }]:
        # for now, need to make this dynamic for later.
        cur.execute(
            "update candidate_criteria set candidate_criteria_norm_form = NULL, candidate_criteria_expression = NULL where criteria_type_id = ? and nct_id = ?",
            [crit_info['criteria_type_id'], t[0]])

        cur.execute(cand_sql, [crit_info['criteria_type_id'], t[0]])
        rs = cur.fetchall()
      #  con.commit()
      #  print("candidate criteria to process: ", len(rs))

        tests = ['Platelets ≥ 100 × 10⁹/L;', 'Platelet count   => 100,000/µL', 'Platelet count   => 100,000,000,000/µL',
                 'Platelets ≥ 10000000000000 × 10⁹/L;',
                 'Platelets ≥ 10000000000000 × 10^9/L;',
                 'Platelets ≥ 10000000000000 x 10⁹/L;',
                 '(C51951)--- Platelets (PLT) >= 100,000/mm^3',
                 '(C51951)--- Platelets >= 100 x 10^9/L',
                 '(C51951)--- Platelets >= 100,000/mm^3 (within 7 days prior to leukapheresis)'
                 ]


        process_numeric_crit(rs, crit_info['re_name'], con, cur, crit_info['criteria_type_id'] , crit_info['ncit_code'], crit_info['lower_nonsense'], crit_info['upper_nonsense'])
    con.commit()
    i = i + 1


hiv_trials_to_process_sql = """
select  cc.nct_id, cc.display_order
from candidate_criteria cc join trial_nlp_dates nlp on cc.nct_id = nlp.nct_id
where (cc.generated_date is  NULL or cc.generated_date < nlp.classification_date) and cc.criteria_type_id in (5)"""
cur.execute(hiv_trials_to_process_sql)
hiv_exc_trials = cur.fetchall()
print("Processing HIV expressions")
get_hiv_codes_sql = """
select  distinct ncit_code from candidate_criteria cc join ncit_nlp_concepts nlp on cc.nct_id = nlp.nct_id and cc.display_order = nlp.display_order
where cc.nct_id = ? and cc.display_order = ? and cc.criteria_type_id = 5
"""
i = 1
for t in hiv_exc_trials:
    print('Processing ', t[0], ' trial ', str(i), 'of', len(hiv_exc_trials))
    cur.execute(get_hiv_codes_sql, [t[0], t[1]])
    codes = cur.fetchall()
    hiv_codes = [c[0] for c in codes]
    #print("codes", hiv_codes)

   # if 'C15175' in hiv_codes or ( ('C14219' in hiv_codes or 'C14220' in hiv_codes)
   #                              and ('C25246' in hiv_codes or 'C128320' in hiv_codes or 'C54625' in hiv_codes
   #                             or 'C80137' in hiv_codes or 'C159692' in hiv_codes or 'C48932' in hiv_codes or 'C45329' in hiv_codes)):
    if 'C15175' in hiv_codes or 'C14219' in hiv_codes or 'C14220' in hiv_codes:
        hiv_exp = "check_if_any('C15175') == 'YES'"
        hiv_norm_form = 'HIV Positive (C15175)'
    else:
        hiv_exp = "NO MATCH"
        hiv_norm_form = 'NO MATCH'

    cur.execute("""update candidate_criteria set candidate_criteria_norm_form = ?, candidate_criteria_expression = ? , 
                   generated_date = ?, marked_done_date = NULL 

                      where nct_id = ? and criteria_type_id = ? and display_order = ?
                   """, [hiv_norm_form, hiv_exp, datetime.datetime.now(), t[0], 5, t[1]])
    i = i + 1
    con.commit()

###############################################################################################
# Brain mets
###############################################################################################
print("Processing brain mets")
brain_mets_trials_to_process_sql = """
select  cc.nct_id, cc.display_order
from candidate_criteria cc join trial_nlp_dates nlp on cc.nct_id = nlp.nct_id
where (cc.generated_date is  NULL or cc.generated_date < nlp.classification_date) and cc.criteria_type_id in (35)"""
cur.execute(brain_mets_trials_to_process_sql)
brain_mets_trials_to_process = cur.fetchall()

get_brain_mets_codes_sql = """
select  distinct ncit_code from candidate_criteria cc join ncit_nlp_concepts nlp on cc.nct_id = nlp.nct_id and cc.display_order = nlp.display_order
where cc.nct_id = ? and cc.display_order = ? and cc.criteria_type_id = 35
"""

i = 1
for t in brain_mets_trials_to_process:
    print('Processing ', t[0], ' trial ', str(i), 'of', len(brain_mets_trials_to_process))
    cur.execute(get_brain_mets_codes_sql, [t[0], t[1]])
    codes = cur.fetchall()
    brain_mets_codes = [c[0] for c in codes]
    if 'C3813' in brain_mets_codes and ( 'C48932' in brain_mets_codes or 'C80137' in brain_mets_codes) :
        brain_mets_exp = "(check_if_any('C4015') == 'YES')"
        brain_mets_norm_form = 'CNS Metastases (C4015)'
    else:
        brain_mets_exp = "NO MATCH"
        brain_mets_norm_form = 'NO MATCH'

    cur.execute("""update candidate_criteria set candidate_criteria_norm_form = ?, candidate_criteria_expression = ? , 
                   generated_date = ?, marked_done_date = NULL 

                      where nct_id = ? and criteria_type_id = ? and display_order = ?
                   """, [brain_mets_norm_form, brain_mets_exp, datetime.datetime.now(), t[0], 35, t[1]])
    i = i + 1
    con.commit()

perf_trials_to_process_sql = """
select  cc.nct_id, cc.display_order
from candidate_criteria cc join trial_nlp_dates nlp on cc.nct_id = nlp.nct_id
where (cc.generated_date is  NULL or cc.generated_date < nlp.classification_date) and cc.criteria_type_id in (8)"""
cur.execute(perf_trials_to_process_sql)
perf_trials_to_process = cur.fetchall()
print("Processing Performance Status expressions")
get_perf_codes_sql = """
select  distinct ncit_code from candidate_criteria cc join ncit_nlp_concepts nlp on cc.nct_id = nlp.nct_id and cc.display_order = nlp.display_order
where cc.nct_id = ? and cc.display_order = ? and cc.criteria_type_id = 8
"""
perf_cand_sql = """
select nct_id, criteria_type_id, inclusion_indicator, candidate_criteria_text, display_order from
candidate_criteria where criteria_type_id = 8  and nct_id = ?
"""
ecog_codes_sql = """
select descendant from ncit_tc where parent in  ('C105721', 'C25400') 
"""
cur.execute(ecog_codes_sql)
ecog_rs = cur.fetchall()
ecog_codes = [c[0] for c in ecog_rs]
ecog_codes_set = set(ecog_codes)
i = 1
karnofsky_to_ecog = {100: 0, 90: 0, 80: 1, 70: 1, 60: 2, 50: 2, 40: 3, 30: 3, 20: 4, 10: 4, 0: 5}
for t in perf_trials_to_process:
    print('Processing ', t[0], ' trial ', str(i), 'of', len(perf_trials_to_process))
    cur.execute(get_perf_codes_sql, [t[0], t[1]])
    codes = cur.fetchall()
    perf_codes = [c[0] for c in codes]
    perf_codes_set = set(perf_codes)

    cur.execute(perf_cand_sql, [t[0]])
    perf_cands = cur.fetchall()

    for pc in perf_cands:
        g = ecog_perf_re.search(pc[3])
        # print(pc[3])
        print(g)
        if g is not None:
            newgroups = [s.strip() if s is not None else None for s in g.groups()]
            ecog_groups  = list(dict.fromkeys([i for i in newgroups if i]))
            print(newgroups)
            print(ecog_groups)
          #  hiv_exp = "check_if_any('C15175') == 'YES'"
           # hiv_norm_form = 'HIV Positive (C15175)'
            tstat = ecog_groups[len(ecog_groups)-1]
            if tstat in ['0-2', '0 - 2', '0 – 2','0- 2', '=< 2', '0, 1, or 2', '0 to 2', '< 3', '0, 1 or 2', '0,1 or 2', '≤ 2', '≤2', 'less than or equal to 2', '0, 1, 2']:
                perf_norm_form = 'Performance Status <= 2'
                perf_exp = parse_performance_string(perf_norm_form)
            elif tstat in ['0-1', '=< 1', '0 to 1', '0 or 1', '0 or1', '< 2', '≤ 1', '0, 1', 'less than or equal to 1', '=< 0-1']:
                perf_norm_form = 'Performance Status <= 1'
                perf_exp = parse_performance_string(perf_norm_form)
            elif tstat in ['0-3', '0‐3', '=< 3', '0, 1, 2, or 3', '0 to 3','0, 1, 2 or 3', '≤ 3', 'less than or equal to 3']:
                perf_norm_form = 'Performance Status <= 3'
                perf_exp = parse_performance_string(perf_norm_form)
            elif tstat in ['2-3', '2 to 3', '2 or 3']:
                perf_norm_form = ' 2 <= Performance Status <= 3'
                perf_exp = 'NO MATCH'
            elif tstat in ['0-4', '=< 4', '0, 1, 2, 3 or 4', '0 to 4', '≤ 4', 'less than or equal to 4']:
                perf_norm_form = 'Performance Status <= 4'
                perf_exp = parse_performance_string(perf_norm_form)
            else:
                perf_norm_form = 'NO MATCH'
                perf_exp = 'NO MATCH'

            print(perf_norm_form, perf_exp)

        else:
            # No ECOG so look for Karnofsky etc.
            g = karnofsky_lansky_perf_re.search(pc[3])
            print(g)
            perf_norm_form = 'NO MATCH'
            perf_exp = 'NO MATCH'
            if g is not None:
                print("Lansky / Karnofsky" , g.groups())
                newgroups = [s.strip() if s is not None else None for s in g.groups()]
                karnofsky_groups = list(dict.fromkeys([i for i in newgroups if i]))
                # Last thing in the list should be number on the scale, we hope
                karnofsky_score =  karnofsky_groups[len(karnofsky_groups)-1]
                if karnofsky_score.isnumeric() and len(karnofsky_groups) >= 2:
                    relational = karnofsky_groups[len(karnofsky_groups)-2]
                    print("Karnofksy/Lansky : ", relational,karnofsky_score )
                    if int(karnofsky_score) in karnofsky_to_ecog:
                        ecog_equivalent = karnofsky_to_ecog[int(karnofsky_score)]
                        # (\>\=|\=\>|\>\=|\=\<|\<\=|\<|\>|≥|≤)
                        if relational in ['>=', '=>', '>','≥' , 'greater than', 'greater than or equal to', 'at least']:
                            perf_norm_form = 'Performance Status <= '+str(ecog_equivalent)
                            perf_exp = parse_performance_string(perf_norm_form)

        cur.execute("""update candidate_criteria set candidate_criteria_norm_form = ?, candidate_criteria_expression = ? , 
                                     generated_date = ?, marked_done_date = NULL 

                                        where nct_id = ? and criteria_type_id = ? and display_order = ?
                                     """, [perf_norm_form, perf_exp, datetime.datetime.now(), t[0], 8, t[1]])

    i = i + 1
    con.commit()

con.close()
