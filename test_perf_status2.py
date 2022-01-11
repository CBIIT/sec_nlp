import re
import sys
import sqlite3
import time
con = sqlite3.connect('/Users/hickmanhb/sqlite/sec_poc.db')
cur = con.cursor()
ecog_perf_re =  re.compile(r""" (
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
                                | (Eastern[ ]Collaborative[ ]Oncology[ ]Group[ ]\(ECOG\))
                                | (Eastern[ ]Cooperation[ ]Oncology[ ]Group[ ]\(ECOG\))
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\)[ ]\(World[ ]Health[ ]Organization[ ]\[WHO\]/Gynecologic[ ]Oncology[ ]Group[ ]\[GOG\]/Zubrod[ ]score\))
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group/Gynecologic[ ]Oncology[ ]Group[ ]\(ECOG/GOG\)) 
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]Performance[ ]Status[ ]\(ECOG[ ]PS\) )
                                 | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\)) 
                                  | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[\n]\(ECOG\)) 
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group) 
                                | (Eastern[ ]Cooperative[ ]Group[ ]\(ECOG\)) 
                                | (Gynecological[ ]Oncology[ ]Group[ ]\(GOG\)) 
                                 | (Gynecologic[ ]Oncology[ ]Group[ ]\(GOG\))
                                 | (Eastern[ ]Cooperative[ ]Oncology[ ]Group/World[ ]Health[ ]Organization[ ]\(ECOG/WHO\) )
                                 |  (ECOG/WHO[ ]performance[ ]status) 
                                 | (World[ ]Health[ ]Organization[ ]\(WHO\) )
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[ ]\(ECOG\) ) 
                                | (Eastern[ ]Cooperative[ ]Oncology[ ]Group[\s\S]*\(ECOG\))
                                | (ECOG) 
                                | (WHO) 
                                ) 
                                                               
                                (\s*(performance)*[ ](scale|
                                                      status[ ]\(PS\) |
                                                      status[ ]must[ ]be|
                                                      status[ ]within[ ]\d\d[ ]hours[ ]prior[ ]to[ ]induction[ ]chemotherapy|
                                                      status|
                                                      scores|
                                                      status[ ]score
                                                      |status[ ]grade|score|)(of)*(\:)*(must[ ]be)* )
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
                                  |  (\<\=[ ]\d[ ]or[ ]\d) 
                                  | (\<\=\d) 
                                 |(\d[ ]–[ ]\d) 
                                 |(\d-[ ]\d)
                                | (\=\<\s*\d)  # =< 2 etc
                                |(\d\-\d)  # 0-2 etc
                                 |(\d‐\d)
                                | (\<\s*\d )
                                | (\>\=\s*\d )# >= 2 etc
                                | (\=\<\s*\d-\d)  # =< 0-1 glop
                                | (\=[ ]\d,[ ]\d,[ ]or[ ]\d)
                                | (\=\s*\d)
                                | (≤\s*\d)
                                | (less[ ]than[ ]or[ ]equal[ ]to[ ]\d-\d) 
                                | (less[ ]than[ ]or[ ]equal[ ]to[ ]\d) 
                                |(\d[ ]\bto[ ]\d) # 0 to 1 etc
                                |(\d,[ ]{0,1}\d[ ]{0,1}or[ ]\d) 
                                |(\d,[ ]{0,1}\d,[ ]{0,1}or[ ]{0,1}\d)
                                |(\d,\d,[ ]\bor[ ]\d)
                                |(\d,[ ]\d,[ ]\d)
                                | (\d,[ ]\d)
                                |(\d[ ]or\d)|(\d[ ]or[ ]\d)
                                |(\d,[ ]{0,1}\d,[ ]{0,1}\d[,]{0,1}[ ]{0,1}or[ ]{0,1}\d)
                                | \(\d\-\d\) 
                                | \(\d[ ]-[ ]\d\)
                                | (\d/\d)
                                | (\d)
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

elist = ["""  5. Have a life expectancy of at least 3 months and an Eastern Cooperative Oncology Group
             (ECOG) performance status of 0 or 1.
             """,
    "(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status (PS) 0, 1",
    "(['C20641'])--- ECOG performance status of 0 - 1",
    "(['C20641'])--- ECOG/WHO performance status of 0 or 1 with no deterioration over the previous 2 weeks and a minimum life expectancy of 12 weeks.",
    "(['C20641'])--- Participant has an Eastern Cooperative Oncology Group (ECOG) performance status of <= 2 for Part 1 and <= 1 for Part 2.",
    "(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status = 0, 1, or 2",
    " mL/min, ECOG performance status of 2, ",
    "* Zubrod performance status = 2",
    "(['C20641'])--- STEP 2 RANDOMIZATION: CLINICAL/LABORATORY CRITERIA: Patients must have a Zubrod performance status of 0 – 1 within 28 days prior to randomization.",
"(['C20641'])--- ECOG performance status within 48 hours prior to induction chemotherapy ≤ 3",
    ' Patient must have Eastern Cooperative Oncology Group (ECOG) performance status =< 0-1',
"(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status of 0 or 1",
         "(['C20641'])--- Patients must have Eastern Cooperative Oncology Group (ECOG) performance status =< 1 and a life expectancy of at least 3 months",
"(['C20641'])--- Gynecologic Oncology Group (GOG) performance status 0, 1, 2",
"(['C20641'])--- Patient must have a Gynecologic Oncology Group (GOG) performance status of 0, 1, or 2 or equivalent",
"(['C20641'])--- Patients with a Gynecologic Oncology Group (GOG) performance status of 0, 1, or 2",
"(['C20641'])--- Gynecologic Oncology Group (GOG) performance status 0, 1, 2",
"(['C20641'])--- Gynecologic Oncology Group (GOG) performance status of 0 to 1.",
"(['C20641'])--- Patients with an Eastern Cooperative Oncology Group/Gynecologic Oncology Group (ECOG/GOG) performance status of 0, 1, or 2",
"(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) (World Health Organization [WHO]/Gynecologic Oncology Group [GOG]/Zubrod score) performance status 0 - 2",
"(['C20641'])--- Patients must have Gynecologic Oncology Group (GOG) performance status 0, 1, or 2",
"(['C20641'])--- Patients must have a Gynecologic Oncology Group (GOG) performance status of 0, 1, or 2",
"(['C20641'])--- Gynecological Oncology Group (GOG) performance status =< 2",
"(['C20641'])--- Gynecological Oncology Group (GOG) performance status of =< 2",

"(['C20641'])--- Gynecologic Oncology Group (GOG) performance status 0, 1, or 2",
"(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status =< 3",
"(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status =< 3 (for adults) or Lansky performance status >= 40 (for children).",
"(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status =< 3 (There may be certain patients with performance status [PS] 3 in the context of rapidly proliferative/refractory ALL who would benefit from this regimen. We don’t want to exclude such patients who may derive benefit from this salvage regimen)",
"(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status (PS) 0, 1, 2, or 3",
"(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status: 0 or 1",
"(['C20641'])--- Eastern Cooperation Oncology Group (ECOG) performance status of 0 or 1.",
"(['C20641'])--- Patients must have a Zubrod performance status of 0‐3",
         "  (['C20641'])--- Patients must have Eastern Cooperative Oncology Group (ECOG) performance status =< 1 and a life expectancy of at least 3 months",
         " (['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status 0 – 2 (asymptomatic to symptomatic but capable of self-care) within 45 days prior to randomization",
         "(['C20641'])--- Patient must have Eastern Cooperative Oncology Group (ECOG) performance status =< 0-1",
         " (['C20641'])--- Patient must have an Eastern Cooperative Oncology Group (ECOG) performance status of 0- 2",
         " (['C20641'])--- An Eastern Cooperative Group (ECOG) performance status ≤ 1",
         " (['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status grade of 0 or 1",
         " (['C20641'])--- Eastern Collaborative Oncology Group (ECOG) Performance Status of 0-1.",
         " (['C20641'])--- Patients must have Eastern Cooperative Oncology Group (ECOG) performance status =< 1 and a life expectancy of at least 3 months",
         " (['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status = 0, 1, or 2",
         "Eastern Cooperative Oncology Group (ECOG) Performance Status (0 - 1)",
"(['C20641'])--- Eastern Cooperative Oncology Group performance status (ECOG) of 1 or Karnofsky performance status (KPS) of >= 70%",
         "(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status of <=2.",
"(['C20641'])--- Eastern Cooperative Oncology Group/World Health Organization (ECOG/WHO) performance status (PS) 0-1 (Karnofsky performance status [KPS] 70-100)",
"(['C20641'])--- ECOG performance status <= 1 or 2",
         "(['C20641'])--- WHO Performance Status 0, 1 or 2. A maximum of 1/3 of patients in cohorts A & B may be WHO performance status 2",
         "(['C20641'])--- ECOG performance status (0-2)",
         "(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status of 0/1",
         "(['C20641'])--- World Health Organization (WHO) performance status =< 2",
         "(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status of ≤1 (adults 18 years or older)/Lansky Performance Score ≥ 80% (minors ages 12-17 only)",
         "(['C20641'])--- Eastern Cooperative Oncology Group (ECOG) performance status (PS) score of 0 or 1."
         ]


klist = [ "Karnofsky performance status [KPS] < 80"
         "(['C20641'])--- Karnofsky or Lansky performance status of ≥ 50%",
         " -  Karnofsky Performance Status (KPS) score of ≥ 70.",
         "(['C20641'])--- Karnofsky or Lansky performance scale score >= 60%",
         "(['C20641'])--- Patients must have a Lansky or Karnofsky performance status score of >= 50, corresponding to Eastern Cooperative Oncology Group (ECOG) categories 0, 1 or 2. Use Karnofsky for patients > 16 years of age and Lansky for patients =< 16 years of age. ",
         "(['C20641'])--- Patients must have a Lansky or Karnofsky performance status score of >= 50, corresponding to Eastern Cooperative Oncology Group (ECOG) categories 0, 1 or 2. ",

         "(['C20641'])--- Karnofsky performance status >= 70",
         " (['C20641'])--- Karnofsky Performance Status (KPS) at least 70",
            "(['C20641'])--- Karnofsky or Lansky performance status of >= 60",
         "(['C20641'])--- Karnofsky performance status (KPS) of greater than or equal to 70",
         """
         (['C20641'])--- ELIGIBILITY CRITERIA FOR ENROLLMENT ONTO APEC1621SC: Karnofsky >= 50% for patients > 16 years of age and Lansky >= 50 for patients =< 16 years of age); note: neurologic deficits in patients with CNS tumors must have been stable for at least 7 days prior to study enrollment; patients who are unable to walk because of paralysis, but who are up in a wheelchair, will be considered ambulatory for the purpose of assessing the performance score
         """]

# perf_trials_to_process_sql = """
# select  cc.nct_id, cc.display_order
# from candidate_criteria cc join trial_nlp_dates nlp on cc.nct_id = nlp.nct_id
# where cc.criteria_type_id in (8)"""
# cur.execute(perf_trials_to_process_sql)
# perf_trials_to_process = cur.fetchall()
# print("Processing Performance Status expressions")
# get_perf_codes_sql = """
# select  distinct ncit_code from candidate_criteria cc join ncit_nlp_concepts nlp on cc.nct_id = nlp.nct_id and cc.display_order = nlp.display_order
# where cc.nct_id = ? and cc.display_order = ? and cc.criteria_type_id = 8
# """
# perf_cand_sql = """
# select nct_id, criteria_type_id, inclusion_indicator, candidate_criteria_text, display_order from
# candidate_criteria where criteria_type_id = 8  and nct_id = ?
# """
# ecog_codes_sql = """
# select descendant from ncit_tc where parent in  ('C105721', 'C25400')
# """
# cur.execute(ecog_codes_sql)
# ecog_rs = cur.fetchall()
# ecog_codes = [c[0] for c in ecog_rs]
# ecog_codes_set = set(ecog_codes)
# i = 1
# karnofsky_to_ecog = {100: 0, 90: 0, 80: 1, 70: 1, 60: 2, 50: 2, 40: 3, 30: 3, 20: 4, 10: 4, 0: 5}
# for t in perf_trials_to_process:
#     print('Processing ', t[0], ' trial ', str(i), 'of', len(perf_trials_to_process))
#     i = i + 1
#     cur.execute(get_perf_codes_sql, [t[0], t[1]])
#     codes = cur.fetchall()
#     perf_codes = [c[0] for c in codes]
#     perf_codes_set = set(perf_codes)
#
#     cur.execute(perf_cand_sql, [t[0]])
#     perf_cands = cur.fetchall()
#
#     for pc in perf_cands:
#         g = ecog_perf_re.search(pc[3])
#         print(pc[3])
#         print(g)
#         if g is not None:
#             newgroups = [s.strip() if s is not None else None for s in g.groups()]
#             ecog_groups  = list(dict.fromkeys([i for i in newgroups if i]))
#             print(newgroups)
#             print(ecog_groups)
#         else:
#             time.sleep(1.8)
#     print('---------------------------------------------')
#sys.exit()
for e in elist:
    print(e)
    g = ecog_perf_re.search(e)
    # print(pc[3])
    print(g)
    if g is not None:
        newgroups = [s.strip() if s is not None else None for s in g.groups()]
        ecog_groups = list(dict.fromkeys([i for i in newgroups if i]))
        print(newgroups)
        print(ecog_groups)
        #  hiv_exp = "check_if_any('C15175') == 'YES'"
        # hiv_norm_form = 'HIV Positive (C15175)'
        tstat = ecog_groups[len(ecog_groups) - 1]
        if tstat in ['0-2', '0 - 2', '=< 2', '0, 1, or 2', '0 to 2', '< 3', '0, 1 or 2', '0,1 or 2', '≤ 2', '≤2',
                     'less than or equal to 2','= 0, 1, or 2', '0 – 2','0- 2', '0, 1, 2','= 2','2','<=2','<= 1 or 2','(0-2)']:
            perf_norm_form = 'Performance Status <= 2'
        elif tstat in ['0-1', '=< 1', '0 to 1', '0 or 1', '0 or1', '< 2', '≤ 1', '0, 1', 'less than or equal to 1','0 – 1', '=< 0-1', '0 - 1','(0 - 1)','1','0/1','≤1']:
            perf_norm_form = 'Performance Status <= 1'
        elif tstat in ['0-3', '=< 3', '0, 1, 2, or 3', '0 to 3', '0, 1, 2 or 3', '≤ 3', 'less than or equal to 3', '0‐3']:
            perf_norm_form = 'Performance Status <= 3'
        elif tstat in ['2-3', '2 to 3', '2 or 3']:
            perf_norm_form = ' 2 <= Performance Status <= 3'
        elif tstat in ['0-4', '=< 4', '0, 1, 2, 3 or 4', '0 to 4', '≤ 4', 'less than or equal to 4']:
            perf_norm_form = 'Performance Status <= 4'
        else:
            perf_norm_form = 'NO MATCH'
        print(perf_norm_form)
    print('-------------------------------------------------------')
sys.exit()
for s in klist:
    g = karnofsky_lansky_perf_re.search(s)
    print(s, ":")
    if g is not None:
        print(g, g.groups())
        newgroups = [s.strip() if s is not None else None for s in g.groups()]
        karnofsky_groups = list(dict.fromkeys([i for i in newgroups if i]))
        print(karnofsky_groups)
        karnofsky_score = karnofsky_groups[len(karnofsky_groups) - 1]
        relational = karnofsky_groups[len(karnofsky_groups) - 2]
        print(relational, karnofsky_score)

    print('-----')
