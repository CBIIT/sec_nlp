drop table if exists ncit_nlp_concepts;

create table ncit_nlp_concepts
(nct_id varchar(100),
 display_order int,
 ncit_code text,
 span_text text,
 start_index int,
 end_index int
);

create index nlp_nct_id_idx on ncit_nlp_concepts(nct_id);
create index nlp_nct_id_ncit_code_idx on ncit_nlp_concepts(nct_id, ncit_code);
create index nlp_ncit_code_idx on ncit_nlp_concepts(ncit_code);

drop view if exists nlp_data_view;
create view nlp_data_view as
select nlp.nct_id,nlp.ncit_code, nlp.display_order, n.pref_name ,nlp.span_text,
nlp.start_index, nlp.end_index, tuc.inclusion_indicator, tuc.description
from ncit_nlp_concepts nlp join ncit n on nlp.ncit_code = n.code
join trial_unstructured_criteria tuc on nlp.nct_id = tuc.nct_id and nlp.display_order = tuc.display_order

drop table if exists ncit_syns;
create table ncit_syns
(
code varchar(100),
syn_name text,
l_syn_name text);

create index ncit_syns_code_idx on ncit_syns(code);
create index ncit_syns_syn_name on ncit_syns(syn_name);
create index ncit_lsyns_syn_name on ncit_syns(l_syn_name);

create index ncit_lower on ncit(lower(pref_name));

drop table if exists candidate_criteria ;
create table candidate_criteria (
nct_id varchar(100),
criteria_type_id int,
display_order int,
inclusion_indicator int,
candidate_criteria_text text
);

drop view if exists candidate_criteria_view;
create view candidate_criteria_view as
SELECT cc.nct_id, cc.criteria_type_id, ct.criteria_type_title,
tc.trial_criteria_orig_text,  tc.trial_criteria_refined_text,
tc.trial_criteria_expression, cc.display_order, cc.inclusion_indicator, cc.candidate_criteria_text
from candidate_criteria cc
join criteria_types ct on cc.criteria_type_id = ct.criteria_type_id
left outer join trial_criteria tc on cc.nct_id = tc.nct_id and cc.criteria_type_id = tc.criteria_type_id
order by cc.nct_id, cc.criteria_type_id
;


---

with performance_statuses as
( select descendant from ncit_tc where parent = 'C20641')

select n.nct_id, n.ncit_code, n.pref_name, n.span_text,n.inclusion_indicator, n.description
from nlp_data_view n join performance_statuses ps on n.ncit_code = ps.descendant

/* create table nlp_take_2 as select * from nlp_data_view */


/* antineoplastic agents */

with codes_of_interest as
( select descendant from ncit_tc where parent = 'C274')

select n.nct_id, n.ncit_code, n.pref_name, n.span_text, n.inclusion_indicator, n.description
from nlp_data_view n join codes_of_interest ps on n.ncit_code = ps.descendant

/* gene or biomarker */
with codes_of_interest as
 ( select descendant from ncit_tc where parent in( 'C16612', 'C16342', 'C18093', 'C45576'))
/* ( select descendant from ncit_tc where parent in( 'C45576')) */
select n.nct_id, n.ncit_code, n.pref_name, n.span_text,n.inclusion_indicator, n.description
from nlp_data_view n join codes_of_interest ps on n.ncit_code = ps.descendant

/* performance status */
with codes_of_interest as
 ( select descendant from ncit_tc where parent in( 'C20641'))
/* ( select descendant from ncit_tc where parent in( 'C45576')) */
select n.nct_id, n.ncit_code, n.pref_name, n.span_text,n.inclusion_indicator, n.description
from nlp_data_view n join codes_of_interest ps on n.ncit_code = ps.descendant

