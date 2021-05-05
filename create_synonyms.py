import sqlite3
import progressbar
import argparse


parser = argparse.ArgumentParser(description='Create ncit synonym table')

parser.add_argument('--dbfilename', action='store', type=str, required=True)
args = parser.parse_args()

con = sqlite3.connect(args.dbfilename)




sql = '''select code, synonyms from ncit 
where (concept_status is null or (concept_status not like '%Obsolete%' and concept_status not like '%Retired%') ) 
'''

insert_sql = '''
insert into ncit_syns(code, syn_name, l_syn_name) values($1,$2,$3)
'''
cur = con.cursor()
cur.execute('drop table if exists ncit_syns')
con.commit()
cur.execute(
    """
create table ncit_syns
(
code varchar(100),
syn_name text,
l_syn_name text)""")
con.commit()
cur.execute(sql)
r = cur.fetchall()
bar = progressbar.ProgressBar(maxval=len(r),
                              widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
bar.start()
i=0
for rec in r:

    c = rec[0]
    synonyms = rec[1].split('|')
    newlist = list(zip([c] * len(synonyms), synonyms, [s.lower() for s in synonyms]))
    cur.executemany(insert_sql, newlist)
    con.commit()
    i += 1
    bar.update(i)
    #print(rs)

cur.execute('create index ncit_syns_code_idx on ncit_syns(code)')
cur.execute('create index ncit_syns_syn_name on ncit_syns(syn_name)')
cur.execute('create index ncit_lsyns_syn_name on ncit_syns(l_syn_name)')
con.commit()
con.close()