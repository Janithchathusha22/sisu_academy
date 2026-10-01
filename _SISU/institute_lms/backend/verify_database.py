"""Read-only schema audit, not a substitute for live role/RLS integration tests.

Reads SUPABASE_DATABASE_URL from backend/.env regardless of the working directory.
Never prints the DSN, credentials, or row contents. Exit 1 on drift, 2 on no connection.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
BUSINESS = {'institutions','students','teachers','courses','modules','lessons','classes',
            'class_sessions','enrollments','attendance','assignments','materials',
            'assignment_submissions','exams','exam_results','payments','notifications'}

def split_columns(body):
    """Split our migration definitions at unquoted, top-level commas."""
    parts=[];start=0;depth=0;quoted=False
    for i,char in enumerate(body):
        if char=="'": quoted=not quoted
        if not quoted:
            if char=='(': depth+=1
            elif char==')': depth-=1
            elif char==',' and depth==0:
                parts.append(body[start:i].strip());start=i+1
    return parts+[body[start:].strip()]

def expected_schema():
    sql='\n'.join(p.read_text(encoding='utf-8') for p in sorted((ROOT/'supabase/migrations').glob('*.sql')))
    tables={};fks=[];unique=[];checks={}
    for table,body in re.findall(r'create table if not exists public\.(\w+)\s*\((.*?)\n\);',sql,re.S|re.I):
        columns={};checks[table]=0
        for definition in split_columns(body):
            if definition.lower().startswith('check '): checks[table]+=1;continue
            match=re.match(r'unique\s*\(([^)]+)\)',definition,re.I)
            if match: unique.append((table,tuple(c.strip() for c in match[1].split(','))));continue
            match=re.match(r'(\w+)\s+(uuid|text|timestamptz|jsonb|boolean|integer|numeric\(\d+,\d+\))(?=\s|$)',definition,re.I)
            # Numeric closing parentheses are non-word characters; no boundary assumption.
            if not match: raise ValueError('Unsupported migration column: '+table+'.'+definition[:60])
            name,kind=match.groups();kind={'timestamptz':'timestamp with time zone','integer':'integer'}.get(kind,kind)
            columns[name]={'type':kind,'not_null':bool(re.search(r'not null|primary key',definition,re.I))}
            if 'primary key' in definition or re.search(r'\bunique\b',definition): unique.append((table,(name,)))
            ref=re.search(r'references\s+(\w+)\.(\w+)\((\w+)\)',definition,re.I)
            if ref: fks.append((table,name,*ref.groups()))
            if re.search(r'\bcheck\s*\(',definition,re.I): checks[table]+=1
        tables[table]=columns
    tables['profiles']['role']['not_null']=False
    tables['profiles']['account_status']={'type':'text','not_null':True}
    checks['profiles']+=1
    policies=set(re.findall(r'create policy (\w+) on public\.(\w+)',sql,re.I))
    policies.update(('active_account',table) for table in BUSINESS)
    indexes={name:(table,tuple(c.strip() for c in columns.split(','))) for name,table,columns in
             re.findall(r'create index if not exists (\w+) on public\.(\w+)\(([^)]+)\)',sql,re.I)}
    functions=set(re.findall(r'create or replace function public\.(\w+)',sql,re.I))
    return tables,fks,unique,checks,policies,indexes,functions

def verify(connection_string):
    expected,fks,unique,checks,policies,indexes,functions=expected_schema()
    report={'passed':[],'missing':[],'mismatches':[],
            'limitations':['Policy/function definitions are inventoried, not formally proven equivalent.',
                           'No live user sign-in or cross-institution RLS behavior tested by this read-only audit.']}
    def check(ok,description): report['passed' if ok else 'mismatches'].append(description)
    with psycopg.connect(connection_string,connect_timeout=10) as conn:
        conn.execute('set transaction read only')
        conn.execute("set local statement_timeout='15s'")
        actual={}
        for table,column,kind,notnull in conn.execute("""select c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull
            from pg_class c join pg_namespace n on n.oid=c.relnamespace
            join pg_attribute a on a.attrelid=c.oid where n.nspname='public'
            and a.attnum>0 and not a.attisdropped and c.relkind='r'"""):
            actual.setdefault(table,{})[column]={'type':kind,'not_null':notnull}
        for table,columns in expected.items():
            if table not in actual: report['missing'].append('table '+table);continue
            for name,spec in columns.items():
                if name not in actual[table]: report['missing'].append('column '+table+'.'+name)
                else: check(actual[table][name]==spec,'column '+table+'.'+name+' type/nullability')
        rls=dict(conn.execute("select c.relname,c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'"))
        for table in expected: check(rls.get(table) is True,'RLS enabled: '+table)
        policy_rows=conn.execute("select policyname,tablename,permissive,roles,cmd,qual,with_check from pg_policies where schemaname='public'").fetchall()
        actual_policies={(r[0],r[1]):r for r in policy_rows}
        for name,table in sorted(policies):
            if (name,table) not in actual_policies: report['missing'].append('policy '+table+'.'+name)
        for table in BUSINESS:
            row=actual_policies.get(('active_account',table))
            check(bool(row and row[2]=='RESTRICTIVE' and 'my_role() IS NOT NULL' in row[5]),'active account restriction: '+table)
        report['policy_inventory']=policy_rows
        actual_indexes={r[0]:r[1:] for r in conn.execute("""select ci.relname,ct.relname,
            array(select a.attname from unnest(i.indkey::smallint[]) with ordinality k(attnum,ord)
                  join pg_attribute a on a.attrelid=i.indrelid and a.attnum=k.attnum order by k.ord),i.indisvalid
            from pg_index i join pg_class ci on ci.oid=i.indexrelid join pg_class ct on ct.oid=i.indrelid
            join pg_namespace n on n.oid=ct.relnamespace where n.nspname='public'""")}
        for name,(table,cols) in indexes.items():
            row=actual_indexes.get(name)
            check(bool(row and row[0]==table and tuple(row[1])==cols and row[2]),'index '+name)
        constraint_rows=conn.execute("""select c.relname,k.contype,
            array(select a.attname from unnest(k.conkey) with ordinality x(num,ord)
                  join pg_attribute a on a.attrelid=k.conrelid and a.attnum=x.num order by x.ord),
            nr.nspname,cr.relname,
            array(select a.attname from unnest(k.confkey) with ordinality x(num,ord)
                  join pg_attribute a on a.attrelid=k.confrelid and a.attnum=x.num order by x.ord),
            pg_get_constraintdef(k.oid),k.convalidated
            from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace
            left join pg_class cr on cr.oid=k.confrelid left join pg_namespace nr on nr.oid=cr.relnamespace
            where n.nspname='public'""").fetchall()
        actual_fks={(r[0],r[2][0],r[3],r[4],r[5][0]) for r in constraint_rows if r[1]=='f' and len(r[2])==1 and r[7]}
        for fk in fks: check(fk in actual_fks,'foreign key '+'.'.join(fk))
        actual_unique={(r[0],tuple(r[2])) for r in constraint_rows if r[1] in {'p','u'} and r[7]}
        for item in unique: check(item in actual_unique,'unique key '+item[0]+'.'+','.join(item[1]))
        for table,count in checks.items():
            check(sum(r[0]==table and r[1]=='c' and r[7] for r in constraint_rows)>=count,'check constraint count: '+table)
        report['constraint_inventory']=[(r[0],r[1],r[6],r[7]) for r in constraint_rows]
        function_rows=conn.execute("select p.proname,pg_get_functiondef(p.oid) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname=any(%s)",(list(functions),)).fetchall()
        for name in functions: check(name in {r[0] for r in function_rows},'function '+name)
        report['function_inventory']=function_rows
        for table,role,privilege,wanted in [
            ('app_sessions','anon','SELECT',False),('app_sessions','authenticated','SELECT',False),
            ('app_sessions','authenticated','INSERT',False),('app_sessions','service_role','UPDATE',True),
            ('profiles','authenticated','UPDATE',False),('account_applications','authenticated','INSERT',False),
            ('courses','authenticated','INSERT',True),('attendance','authenticated','INSERT',True)]:
            if table in actual:
                granted=conn.execute('select has_table_privilege(%s,%s,%s)',(role,'public.'+table,privilege)).fetchone()[0]
                check(granted==wanted,'table grant '+role+' '+table+' '+privilege+' = '+str(wanted))
        for table,column,privilege,wanted in [('profiles','role','UPDATE',False),('profiles','institution_id','UPDATE',False),
                ('profiles','account_status','UPDATE',False),('profiles','full_name','UPDATE',True),
                ('attendance','status','UPDATE',True),('attendance','student_id','UPDATE',False),
                ('exams','questions','SELECT',False),('exams','title','SELECT',True)]:
            if column in actual.get(table,{}):
                granted=conn.execute('select has_column_privilege(%s,%s,%s,%s)',('authenticated','public.'+table,column,privilege)).fetchone()[0]
                check(granted==wanted,'column grant '+table+'.'+column+' '+privilege+' = '+str(wanted))
        trigger=conn.execute("select exists(select 1 from pg_trigger where tgrelid='auth.users'::regclass and tgname='on_auth_user_created' and tgenabled='O')").fetchone()[0]
        check(trigger,'Auth provisioning trigger enabled')
        conn.rollback()
    report['ok']=not report['missing'] and not report['mismatches']
    return report

if __name__=='__main__':
    load_dotenv(Path(__file__).resolve().parent/'.env')
    url=os.getenv('SUPABASE_DATABASE_URL','')
    if not url:
        print('SUPABASE_DATABASE_URL is required; no connection attempted.')
        raise SystemExit(2)
    try: result=verify(url)
    except psycopg.Error:
        print('Database audit unavailable. Check the private connection settings. Credentials were not printed.')
        raise SystemExit(2) from None
    target=ROOT/'docs/SUPABASE_DATABASE_VERIFICATION.json'
    target.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print('Audit '+('passed' if result['ok'] else 'found drift')+'; report: '+str(target))
    raise SystemExit(0 if result['ok'] else 1)
