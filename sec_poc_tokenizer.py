import argparse
import datetime
import os
from bz2 import decompress
from functools import lru_cache
from pathlib import Path
from pickle import loads
import traceback

import psycopg2
import psycopg2.extras
import spacy

# Ensure the sec_etl root (where etl_processor.py lives) is on sys.path whether
# run via the sec_etl-level symlink, directly, or through etl.qmd.
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
for _root in (_THIS_DIR, _os.path.dirname(_THIS_DIR), _os.path.dirname(_os.path.dirname(_THIS_DIR)), _os.getcwd()):
    if _os.path.isfile(_os.path.join(_root, 'etl_processor.py')):
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        break

from etl_processor import EtlProcessor, etl_printer


# Pref-names / synonyms that are too short or generic to be meaningful NCIt
# matches.  Shared verbatim by both span-lookup queries below.
SPAN_STOPWORDS = (
    'i', 'ii', 'iii', 'iv', 'v', 'set', 'all', 'at', 'is', 'and', 'or', 'to',
    'a', 'be', 'for', 'an', 'as', 'in', 'of', 'x', 'are', 'no', 'any', 'on',
    'who', 'have', 't', 'who', 'at',
)


@lru_cache(maxsize=10000)
def get_best_ncit_code_for_span(con, a_span):
    get_best_ncit_code_sql_for_span = """
    select code from ncit where lower(pref_name) = %s and
    lower(pref_name) not in %s
    """
    cur = con.cursor()
    cur.execute(get_best_ncit_code_sql_for_span, [a_span, SPAN_STOPWORDS])
    return cur.fetchall()


@lru_cache(maxsize=10000)
def get_all_ncit_codes_for_span(con, a_span):
    get_ncit_code_sql_for_span = """
    select distinct code from ncit_syns where l_syn_name = %s and
     l_syn_name not in %s
    """
    cur = con.cursor()
    cur.execute(get_ncit_code_sql_for_span, [a_span, SPAN_STOPWORDS])
    return cur.fetchall()


class TokenizerProcessor(EtlProcessor):
    INS_CODE_SQL = """
        insert into ncit_nlp_concepts(nct_id, display_order, ncit_code, span_text, start_index, end_index) values (%s,%s,%s,%s,%s,%s)
    """

    GET_CRIT_SQL = """
        select nct_id, display_order, description  from trial_unstructured_criteria where nct_id = %s
    order by nct_id, display_order
    /* limit 10000 */
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
        parser = argparse.ArgumentParser(description='Parse NCI codes from the text')
        parser.add_argument('--force', '-f', action='store_true', required=False, default=False)
        parser.add_argument('--dbname', action='store', type=str, required=False, default=os.environ.get('DB_NAME', 'sec'))
        parser.add_argument('--host', action='store', type=str, required=False, default=os.environ.get('DB_HOST', 'localhost'))
        parser.add_argument('--user', action='store', type=str, required=False, default=os.environ.get('DB_USER', 'sec'))
        parser.add_argument('--password', action='store', type=str, required=False, default=os.environ.get('DB_PASS', 'sec'))
        parser.add_argument('--port', action='store', type=str, required=False, default=os.environ.get('DB_PORT', '5433'))
        return parser

    @etl_printer
    def init_nlp(self, cur):
        start_nlp_init = datetime.datetime.now()
        print('Initializing NLP at ', start_nlp_init)

        nlp = spacy.blank('en')
        nlp_pickle_sql = """select ncit_tokenizer from ncit_version where active_version='Y' limit 1"""
        cur.execute(nlp_pickle_sql)
        pickled = cur.fetchone()[0]
        matcher = loads(decompress(pickled))

        end_nlp_init = datetime.datetime.now()
        print('NLP Init complete at', end_nlp_init, ' elapsed time = ', end_nlp_init - start_nlp_init)
        return nlp, matcher

    @etl_printer
    def delete_orphaned_data(self, con, cur):
        print('deleting data for trials no longer in active / treatment set')

        delete_old_concepts_sql = """
        with del_trials as
        (
        select distinct c.nct_id from ncit_nlp_concepts c where not exists (select t.nct_id from trials t where t.nct_id = c.nct_id)
        )
        delete from ncit_nlp_concepts  where nct_id in (select d.nct_id from del_trials d)
        """
        cur.execute(delete_old_concepts_sql)
        con.commit()

        delete_old_trial_dates_sql = """
        with del_trials as
        (
        select distinct c.nct_id from trial_nlp_dates c where not exists (select t.nct_id from trials t where t.nct_id = c.nct_id)
        )
        delete from trial_nlp_dates  where nct_id in (select d.nct_id from del_trials d)
        """
        cur.execute(delete_old_trial_dates_sql)
        con.commit()

        delete_old_cand_crit_sql = """
        with del_trials as
        (
        select distinct c.nct_id from candidate_criteria c where not exists (select t.nct_id from trials t where t.nct_id = c.nct_id)
        )
        delete from candidate_criteria  where nct_id in (select d.nct_id from del_trials d)
        """
        # NOTE: the original procedural script re-ran delete_old_trial_dates_sql
        # here (copy-paste slip), so candidate_criteria orphans were never
        # purged. Corrected to run the candidate_criteria delete.
        cur.execute(delete_old_cand_crit_sql)
        con.commit()

    @etl_printer
    def get_trials_to_process(self, cur):
        if self.args.force:
            get_trials_sql = """
                             select t.nct_id, t.record_verification_date, t.amendment_date, td.tokenized_date
                             from trials t \
                                      left outer join trial_nlp_dates td on t.nct_id = td.nct_id
                             """
        else:
            get_trials_sql = """
            select  t.nct_id, t.record_verification_date, t.amendment_date, td.tokenized_date
            from trials t left outer join trial_nlp_dates td on t.nct_id = td.nct_id
            where (td.tokenized_date is null)
                  or td.tokenized_date <= greatest(coalesce( t.record_verification_date,'1980-01-01'),
                                                                        coalesce( t.amendment_date,'1980-01-01'))
            """

        cur.execute(get_trials_sql)
        trials = cur.fetchall()
        print('there are ', len(trials), ' trials to tokenize ')
        return trials

    # Deliberately NOT @etl_printer-decorated: runs once per trial, so decorating
    # it floods etl_output/*.txt (and the ETL report email). Stage-level methods
    # keep the decorator.
    def tokenize_trial(self, con, cur, nlp, matcher, trial):
        nct_id = trial[0]
        cur.execute(self.GET_CRIT_SQL, [nct_id])
        con.commit()
        crits = cur.fetchall()

        cur.execute('delete from ncit_nlp_concepts where nct_id = %s ', [nct_id])
        for crit in crits:
            doc = nlp(crit[2])
            matches = matcher(doc)
            spans = [doc[start:end] for _match_id, start, end in matches]

            filtered_spans = spacy.util.filter_spans(spans)
            for f in filtered_spans:
                lower_f = f.text.lower()
                try:
                    float(lower_f)
                    is_a_float = True
                except ValueError:
                    is_a_float = False

                if not is_a_float:
                    bcodes = get_best_ncit_code_for_span(con, lower_f)
                    if len(bcodes) > 0:
                        for one_code in bcodes:
                            cur.execute(self.INS_CODE_SQL, [crit[0], crit[1], one_code[0], lower_f, f.start_char, f.end_char])
                    else:
                        rcodes = get_all_ncit_codes_for_span(con, lower_f)
                        for one_code in rcodes:
                            cur.execute(self.INS_CODE_SQL, [crit[0], crit[1], one_code[0], lower_f, f.start_char, f.end_char])

        cur.execute('select count(*) from trial_nlp_dates where nct_id = %s', [nct_id])
        hm = cur.fetchone()[0]
        if hm == 1:
            cur.execute('update trial_nlp_dates set tokenized_date = %s  where nct_id = %s', [datetime.datetime.now(), nct_id])
        else:
            cur.execute('insert into trial_nlp_dates(nct_id, tokenized_date) values(%s,%s)', [nct_id, datetime.datetime.now()])
        con.commit()

    @etl_printer
    def process_trials(self, con, cur, nlp, matcher, trials):
        print(f"{'Count' : <8}{'  NCT ID': <15}{'RVD' : ^30}{'Amendment Date' : ^30}{'Prior Tokenized Date' : ^30}")
        for i, trial in enumerate(trials):
            print(
                f"{i + 1: <8}{trial[0]: <15}"
                f"{str(trial[1]) if trial[1] is not None else '': <30}"
                f"{str(trial[2]) if trial[2] is not None else '': <30}"
                f"{str(trial[3]) if trial[3] is not None else '' : <30}"
            )
            self.tokenize_trial(con, cur, nlp, matcher, trial)

    @etl_printer
    def refresh_nlp_data_tab(self, con, cur):
        # Refresh the nlp_data_tab and reindex
        cur.execute('drop table if exists nlp_data_tab')
        con.commit()
        cur.execute(
            """create table nlp_data_tab as select nct_id, ncit_code, display_order, pref_name, span_text, start_index, end_index, inclusion_indicator, description
from nlp_data_view"""
        )
        con.commit()
        cur.execute('create index nlp_dt_ncit_code on nlp_data_tab(ncit_code)')
        con.commit()
        cur.execute('create index nlp_dt_nct_id on nlp_data_tab(nct_id)')
        con.commit()
        # nlp_data_tab is dropped and recreated above, which discards its grants.
        # refresh_ncit_pg granted SELECT on it earlier in the ETL run, but that
        # grant is destroyed here -- so it must be re-applied, or sec_read loses
        # access to nlp_data_tab after every run.
        self.ensure_role(con)
        self.grant_select(con, 'nlp_data_tab')

    @etl_printer
    def process(self):
        start_time = datetime.datetime.now()
        con = None
        try:
            con = psycopg2.connect(
                database=self.args.dbname,
                user=self.args.user,
                host=self.args.host,
                port=self.args.port,
                password=self.args.password,
            )
            cur = con.cursor()
            nlp, matcher = self.init_nlp(cur)
            self.delete_orphaned_data(con, cur)
            trials = self.get_trials_to_process(cur)
            con.commit()
            self.process_trials(con, cur, nlp, matcher, trials)
            self.refresh_nlp_data_tab(con, cur)
        except Exception as exc:
            self.fail('TOKENIZER ETL FAILED: ', exc, traceback.format_exc())
        finally:
            if con is not None:
                con.close()
            super().post_process()

        run_done = datetime.datetime.now()
        print('run complete - at ', run_done, 'elapsed time ', run_done - start_time)
        return self.succeeded


if __name__ == '__main__':
    bootstrap_processor = TokenizerProcessor(args=None, python_file=__file__)
    parser = bootstrap_processor.build_parser()
    parsed_args = parser.parse_args()
    # Module-level `success` is what etl.qmd reads back out of the module
    # namespace (runpy.run_path) to decide whether this step passed.
    success = TokenizerProcessor(args=parsed_args, python_file=__file__).process()
