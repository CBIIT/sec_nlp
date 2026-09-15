import argparse
import datetime
import os
from pathlib import Path
import traceback

import psycopg2
import psycopg2.extras

# Ensure the sec_etl root (where etl_processor.py lives) is on sys.path whether
# run via the sec_etl-level symlink, directly, or through etl-new.qmd.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
for _root in (_THIS_DIR, _os.path.dirname(_THIS_DIR), _os.path.dirname(_os.path.dirname(_THIS_DIR)), _os.getcwd()):
    if _os.path.isfile(_os.path.join(_root, 'etl_processor.py')):
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        break

from common_funcs import get_criteria_type_map
from etl_processor import EtlProcessor, etl_printer


class ClassifierProcessor(EtlProcessor):
    GET_TRIALS_SQL = """
    select t.nct_id , t.record_verification_date, t.amendment_date,td.tokenized_date, td.classification_date from trials t
    left outer join trial_nlp_dates td on t.nct_id = td.nct_id
    where td.classification_date is null or td.classification_date <= td.tokenized_date
    """

    def __init__(self, args=None, name=None, python_file=None):
        python_file = python_file or __file__
        super().__init__(
            name=name or Path(python_file).stem,
            args=args,
            python_file=python_file,
        )

    @etl_printer
    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description='Create candidate criteria texts')
        parser.add_argument('--force', '-f', action='store_true', required=False, default=False)
        parser.add_argument('--dbname', '-d', action='store', type=str, required=False, default=os.environ.get('DB_NAME', 'sec'))
        parser.add_argument('--host', '-ho', action='store', type=str, required=False, default=os.environ.get('DB_HOST', 'localhost'))
        parser.add_argument('--user', '-u', action='store', type=str, required=False, default=os.environ.get('DB_USER', 'sec'))
        parser.add_argument('--password', '-pw', action='store', type=str, required=False, default=os.environ.get('DB_PASS', 'sec'))
        parser.add_argument('--port', '-p', action='store', type=str, required=False, default=os.environ.get('DB_PORT', '5433'))
        return parser

    def check_for_concepts(self, con, nct_id, criteria_type_id, ncit_codes, inclusion_indicator, ncit_codes_to_remove='', include_descendants=True):

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
        from ncit_nlp_concepts nlp join descendants d on nlp.ncit_code = d.descendant and nlp.nct_id = %s
        join trial_unstructured_criteria u on nlp.nct_id = u.nct_id  and nlp.display_order = u.display_order and u.inclusion_indicator = %s
            and nlp.ncit_code not in (select descendant as ncit_code from descendants_to_remove)
            """.format(desc_1="''" if len(ncit_codes) == 0 else ', '.join(['%s'] * len(ncit_codes)),
                       desc_to_remove="''" if len(ncit_codes_to_remove) == 0 else ', '.join(['%s'] * len(ncit_codes_to_remove)))
        else:
            desc_sql = """
            select
                   nlp.nct_id, nlp.display_order, nlp.ncit_code, nlp.start_index, nlp.end_index ,u.inclusion_indicator,  u.description
               from ncit_nlp_concepts nlp
               join trial_unstructured_criteria u on nlp.nct_id = u.nct_id  and nlp.display_order = u.display_order and u.inclusion_indicator = %s
                   and nlp.ncit_code in ( {good_codes} ) and nlp.ncit_code not in ({codes_to_remove})
                    and nlp.nct_id = %s
                    """.format(good_codes=', '.join(['%s'] * len(ncit_codes)),
                              codes_to_remove="''" if len(ncit_codes_to_remove) == 0 else ', '.join(['%s'] * len(ncit_codes_to_remove)))
        #print(desc_sql)
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
        select count(*) as num_crits from trial_unstructured_criteria where nct_id = %s and inclusion_indicator = %s
        """
        cur = con.cursor()
        cur.execute(num_crits_for_trial_sql, [nct_id,inclusion_indicator])
        num_crits = cur.fetchone()[0]
        # If the trial doesn't have any unstructured criteria matching the provided inclusion indicator,
        # then it won't have any predicted NLP concepts.
        if num_crits >= 1:
            # Iterate through and get the distinct criteria.
            # Some criterions' descriptions are repeated for each inclusion scenario.
            t = set()
            for crit in d:
                # description (str), display_order (int), inclusion_indicator (bool)
                t.add( (crit[6], crit[1], crit[5] ))

            for c in t:
                ins_sql = """
                insert into candidate_criteria(nct_id, criteria_type_id,  candidate_criteria_text, display_order,inclusion_indicator) values (%s,%s,%s,%s,%s)
                """
                cur.execute(ins_sql, [nct_id, criteria_type_id, '('+ str(ncit_codes) + ')--- '+c[0],c[1] , c[2]])
            con.commit()

        return []

    def get_descendants(self, con, ncit_code):
        sql = """
        select descendant from ncit_tc where parent = $1
        """
        cur = con.cursor()
        cur.execute(sql, [ncit_code])
        rs = cur.fetchall()
        con.commit()
        return rs

    @etl_printer
    def delete_orphaned_candidates(self, con, cur):
        cur.execute("""
        select count(distinct nct_id) as num_trials_to_delete  from candidate_criteria cc where cc.nct_id not in (select nct_id from trials)
        """)
        num_to_delete = cur.fetchone()[0]
        print('there are ', num_to_delete, 'trials that are no longer that have NLP derived criteria. Deleting those.')
        cur.execute("""
        delete from candidate_criteria where nct_id not in (select nct_id from trials)
        """)
        con.commit()

    @etl_printer
    def get_trials_to_classify(self, con, cur):
        cur.execute(self.GET_TRIALS_SQL)
        return cur.fetchall()

    # Deliberately NOT @etl_printer-decorated: runs once per trial, so decorating
    # it floods etl_output/*.txt (and the ETL report email). Stage-level methods
    # keep the decorator.
    def classify_trial(self, con, cur, crit_map, nct_id):
        cur.execute('delete from candidate_criteria where nct_id = %s ', [nct_id])

        # See https://bioappdev.atlassian.net/browse/POC-80
        # C116664 should be removed from performance status
        # C161964 permitted as a prior therapy but not a performance status
        self.check_for_concepts(con, nct_id, crit_map['perf'], ['C20641'],True, ncit_codes_to_remove=['C116664', 'C161964'])   # Performance status
        self.check_for_concepts(con, nct_id, crit_map['wbc'], ['C51948'],True, include_descendants=False) # WBC
        self.check_for_concepts(con, nct_id, crit_map['plt'], ['C51951'],True)    # PLT
        self.check_for_concepts(con, nct_id, crit_map['hiv_exc'], ['C14219'],False)    # HIV
        self.check_for_concepts(con, nct_id, crit_map['bmets'], ['C4015'],False)    # BMETS
        #self.check_for_concepts(con, nct_id, 1, ['C3910','C16612'],0, ncit_codes_to_remove= ['C90505'] )    # BIOMARKER EXC
        self.check_for_concepts(con, nct_id, crit_map['biomarker_exc'], ['C3910','C16612', 'C26548'],False, ncit_codes_to_remove= [ 'C74944','C17021', 'C21176','C25294'])    # BIOMARKER EXC
        self.check_for_concepts(con, nct_id, crit_map['biomarker_inc'], ['C3910','C16612', 'C26548'],True, ncit_codes_to_remove= ['C74944','C17021', 'C21176','C25294'] )    # BIOMARKER INC

        # PT -- need to split these out for inc/exclusion
       # self.check_for_concepts(con, nct_id , 36, ['C62634','C15313', 'C15329'],1)  # PT INC
       # self.check_for_concepts(con, nct_id , 37, ['C62634','C15313', 'C15329'],0)  # PT EXC
        self.check_for_concepts(con, nct_id, crit_map['pt_inc'], ['C25218', 'C1908', 'C62634', 'C163758'], True,ncit_codes_to_remove= ['C25294', 'C102116'])  # PT INC, remove lab procedures
        self.check_for_concepts(con, nct_id, crit_map['pt_exc'], ['C25218', 'C1908', 'C62634', 'C163758'],False, ncit_codes_to_remove= ['C25294', 'C102116'])  # PT EXC, remove lab procedures

        self.check_for_concepts(con, nct_id, crit_map['disease_inc'], ['C3262'],True)  #  Disease inclusions

        cur.execute('select count(*) from trial_nlp_dates where nct_id = %s', [nct_id] )
        hm = cur.fetchone()[0]
        if hm == 1:
            cur.execute("update trial_nlp_dates set classification_date = %s  where nct_id = %s" ,[datetime.datetime.now() , nct_id])
        else:
            cur.execute("insert into trial_nlp_dates(nct_id, classification_date) values(%s,%s)", [nct_id, datetime.datetime.now()])
        con.commit()

    @etl_printer
    def process(self):
        start_time = datetime.datetime.now()
        con = None
        try:
            crit_map = get_criteria_type_map()
            print(crit_map)
            con = psycopg2.connect(
                database=self.args.dbname,
                user=self.args.user,
                host=self.args.host,
                port=self.args.port,
                password=self.args.password,
            )
            cur = con.cursor()

            if self.args.force:
                cur.execute('update trial_nlp_dates set classification_date=null')
                con.commit()

            self.delete_orphaned_candidates(con, cur)

            trials_to_classify = self.get_trials_to_classify(con, cur)
            print('there are ', len(trials_to_classify), ' trials to classify ')
            print(f"{'Count' : <8}{'  NCT ID': <15}{'RVD' : ^30}{'Amendment Date' : ^30}{'Tokenized Date' : ^30}{'Prior Classification Date' : ^30}")
            con.commit()
            for i, trial in enumerate(trials_to_classify, start=1):
                print(f"{i: <8}{trial[0]: <15}{str(trial[1]) if trial[1] is not None else '': ^30}{str(trial[2]) if trial[2] is not None else '': ^30}{str(trial[3]) if trial[3] is not None else '': ^30}{str(trial[4]) if trial[4] is not None else '': ^30}")
                self.classify_trial(con, cur, crit_map, trial[0])
        except Exception as exc:
            self.fail('CLASSIFIER ETL FAILED: ', exc, traceback.format_exc())
        finally:
            if con is not None:
                con.close()
            super().post_process()

        print('Classifier ETL completed in ', datetime.datetime.now() - start_time)
        return self.succeeded


if __name__ == '__main__':
    bootstrap_processor = ClassifierProcessor(args=None, python_file=__file__)
    parser = bootstrap_processor.build_parser()
    parsed_args = parser.parse_args()
    # Module-level `success` is what etl-new.qmd reads back out of the module
    # namespace (runpy.run_path) to decide whether this step passed.
    success = ClassifierProcessor(args=parsed_args, python_file=__file__).process()
