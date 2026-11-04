"""Opt-in actual PostgreSQL tests on a NEW temporary cluster, never an existing DB.

RUN_ISOLATED_HEAD_TESTS=1; optionally ISOLATED_POSTGRES_BIN points to installed
initdb/pg_ctl binaries. No credentials/configuration from the project are read.
The random loopback port, random role, nonce and fresh directory pin every connect.
"""
from contextlib import contextmanager
import copy
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'migrations/optional/007_household_roles.up.sql'
DOWN=ROOT/'migrations/optional/007_household_roles.down.sql'


def fingerprint(cursor):
    result={}
    for table in ('users','households','household','audit_logs','password_resets'):
        cursor.execute('SELECT count(*) AS total,md5(COALESCE(string_agg(to_jsonb(t)::text,\'\' ORDER BY id),\'\')) AS digest FROM '+table+' t')
        result[table]=dict(cursor.fetchone())
    return result


@pytest.fixture(scope='module')
def isolated_cluster():
    if os.getenv('RUN_ISOLATED_HEAD_TESTS')!='1':pytest.skip('Opt-in temporary PostgreSQL cluster only')
    binaries=Path(os.getenv('ISOLATED_POSTGRES_BIN',r'C:\Program Files\PostgreSQL\18\bin'))
    initdb=binaries/'initdb.exe';pg_ctl=binaries/'pg_ctl.exe'
    if not initdb.is_file() or not pg_ctl.is_file():pytest.skip('Installed PostgreSQL server tools unavailable')
    output=(ROOT/'output').resolve();output.mkdir(exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='isolated-heads-',dir=output)).resolve()
    assert folder.is_relative_to(output) and folder!=output
    data=folder/'data';password_file=folder/'test-auth.txt'
    nonce=secrets.token_hex(16);user='fixture_'+secrets.token_hex(8);password=secrets.token_urlsafe(32)
    password_file.write_text(password,encoding='ascii')
    environment={k:v for k,v in os.environ.items() if not k.startswith('PG') and k not in {'DATABASE_URL','APP_ENV'}}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    assert port!=5432 and port>1024
    started=False
    def run(arguments):
        result=subprocess.run([str(a) for a in arguments],env=environment,capture_output=True,timeout=40)
        if result.returncode:
            # Startup logs contain only this newly generated cluster. Emit fixed
            # categories, never command arguments, authentication values or logs.
            log=(folder/'server.log').read_text(errors='replace') if (folder/'server.log').exists() else ''
            detail=(result.stdout+result.stderr).decode(errors='replace')+' '+log
            if 'could not create restricted token' in detail.lower():
                pytest.skip('Windows restricted token prevents launching the isolated PostgreSQL test server; no existing database selected')
            category=next((label for needle,label in [
                ('Permission denied','PERMISSION_DENIED'),('Access is denied','ACCESS_DENIED'),
                ('No such file or directory','PATH_NOT_FOUND'),('invalid argument','INVALID_ARGUMENT'),
                ('unrecognized configuration parameter','CONFIGURATION_PARAMETER'),
                ('Address already in use','PORT_IN_USE'),('not permitted','OPERATION_NOT_PERMITTED'),
                ('could not execute','PROCESS_EXECUTION_FAILED'),('not recognized','EXECUTABLE_NOT_FOUND')]
                if needle.lower() in detail.lower()),'UNCLASSIFIED_STARTUP_FAILURE')
            raise RuntimeError('Isolated PostgreSQL failed: '+category+'; no existing database was selected')
    def connect():
        conn=psycopg2.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=port,
            dbname='postgres',user=user,password=password,sslmode='prefer',connect_timeout=5,
            options='-c search_path=public -c statement_timeout=10000 -c timezone=UTC')
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT current_database(),current_user,inet_server_port(),current_setting('bis.test_id')")
                assert cursor.fetchone()==('postgres',user,port,nonce)
            conn.rollback();return conn
        except BaseException:conn.close();raise
    try:
        run([initdb,'-D',data,'-U',user,'--pwfile',password_file,'-A','scram-sha-256','--encoding=UTF8','--no-locale'])
        password_file.unlink()
        run([pg_ctl,'-D',data,'-l',folder/'server.log','-w','-t','20','-o',
             f'-h 127.0.0.1 -p {port} -c bis.test_id={nonce}','start'])
        started=True
        from manage import apply_migrations
        from security import hash_password
        conn=connect()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    assert len(apply_migrations(cursor))==6
                    cursor.execute("INSERT INTO users(username,password,email,role,status) VALUES(%s,%s,%s,'admin','approved'),(%s,%s,%s,'user','approved')",
                        ('Fixture-admin',hash_password('Fictional integration password'), 'admin@example.invalid',
                         'Fixture-unrelated',hash_password('Different fictional password'),'other@example.invalid'))
                    for home in range(1,31):
                        cursor.execute('INSERT INTO households(surname,house_number,address) VALUES(%s,%s,%s) RETURNING id',
                                       ('Fictional family '+str(home),str(home),'Fictional test address'))
                        identifier=cursor.fetchone()['id']
                        for member in range(4):
                            deceased=4*(home-1)+member>=110
                            cursor.execute("""INSERT INTO household(firstname,surname,household_id,birthdate,gender,civil_status,status,death_date)
                              VALUES(%s,%s,%s,%s,'Female','Single',%s,%s)""",
                              ('Fictional '+str(member),'Independent surname',identifier,'1945-05-07' if deceased else '2000-01-01',
                               'Deceased' if deceased else 'Active','2021-02-21' if deceased else None))
                    before=fingerprint(cursor)
                    cursor.execute(UP.read_text(encoding='utf-8'))
                    after=fingerprint(cursor)
                    assert before==after
            yield dict(connect=connect,before=before,after=after,nonce=nonce)
        finally:conn.close()
    finally:
        if started or (data/'postmaster.pid').exists():
            run([pg_ctl,'-D',data,'-m','fast','-w','-t','20','stop'])
        # This unique directory was created by this fixture. Never remove or move
        # any user database directory, public schema or preserved snapshot.
        assert folder.resolve().is_relative_to(output) and folder.resolve()!=output
        shutil.rmtree(folder)


@pytest.fixture
def head_database(isolated_cluster,monkeypatch):
    monkeypatch.setenv('APP_ENV','test');monkeypatch.setenv('SECRET_KEY',secrets.token_urlsafe(48))
    monkeypatch.setenv('DATABASE_URL','postgresql://blocked@127.0.0.1/barangay_test')
    monkeypatch.setenv('ALLOW_LOCAL_DATABASE','0');monkeypatch.setenv('ENABLE_EMAIL','0')
    monkeypatch.setenv('APP_BASE_URL','http://127.0.0.1:8787')
    from webapp import create_app
    import account_routes,database,directory_routes,record_routes,reporting,report_outputs,security,notifications
    conn=isolated_cluster['connect']()
    @contextmanager
    def transaction():
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute('SAVEPOINT isolated_request')
            try:yield cursor
            except BaseException:
                cursor.execute('ROLLBACK TO SAVEPOINT isolated_request');raise
            finally:cursor.execute('RELEASE SAVEPOINT isolated_request')
    for module in (account_routes,database,directory_routes,record_routes,reporting,report_outputs,security,notifications):
        monkeypatch.setattr(module,'transaction',transaction)
    app=create_app({'TESTING':True});client=app.test_client()
    with client.session_transaction() as session:
        session.update(user_id=1,username='Fixture-admin',role='admin',session_version=1,_csrf='fixture-csrf')
    def query(statement,params=()):
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(statement,params);return cursor.fetchall() if cursor.description else []
    def post(path,**data):return client.post(path,data={**data,'csrf_token':'fixture-csrf'})
    try:yield dict(conn=conn,client=client,query=query,post=post,transaction=transaction)
    finally:conn.rollback();conn.close()


def test_optional_migration_preserves_all_original_rows(isolated_cluster):
    assert isolated_cluster['before']==isolated_cluster['after']
    assert {k:v['total'] for k,v in isolated_cluster['after'].items()}==dict(users=2,households=30,household=120,audit_logs=0,password_resets=0)


def test_actual_unique_and_membership_constraints_reject_invalid_heads(head_database):
    db=head_database;q=db['query']
    db['post']('/households/1/head',head_resident_id='1',head_assignment='none',head_reason='Explicit fictional decision')
    with pytest.raises(psycopg2.IntegrityError):
        with db['transaction']() as cursor:
            cursor.execute("INSERT INTO household_head_assignments(household_id,household_id_record,resident_id,resident_id_record,assigned_by_record,reason) VALUES(1,1,2,2,1,'Conflicting fictional head')")
    with pytest.raises(psycopg2.IntegrityError):
        with db['transaction']() as cursor:
            cursor.execute("INSERT INTO household_head_assignments(household_id,household_id_record,resident_id,resident_id_record,assigned_by_record,reason) VALUES(2,2,1,1,1,'Foreign household member')")
    assert q('SELECT count(*) AS n FROM household_head_assignments WHERE ended_at IS NULL')[0]['n']==1


def test_real_reassignment_preserves_rows_and_relationship_history(head_database):
    db=head_database;q=db['query'];post=db['post']
    with db['conn'].cursor(cursor_factory=RealDictCursor) as cursor:before=fingerprint(cursor)
    assert post('/households/1/head',head_resident_id='1',head_assignment='none',head_reason='First fictional designation').status_code==302
    assignment=q('SELECT id FROM household_head_assignments WHERE ended_at IS NULL')[0]['id']
    response=post('/edit_member/2',firstname='Fictional 1',surname='Independent surname',household_id='1',birthdate='2000-01-01',
        gender='Female',civil_status='Single',status='Active',household_roles_present='yes',head_assignment=str(assignment),relationship_to_head='Non-relative')
    assert response.status_code==302
    assert post('/households/1/head',head_resident_id='2',head_assignment=str(assignment),head_reason='Explicit fictional reassignment').status_code==302
    rows=q('SELECT resident_id_record,ended_at FROM household_head_assignments ORDER BY id')
    assert rows[0]['ended_at'] is not None and rows[1]['ended_at'] is None
    assert q('SELECT relationship FROM household_member_relationships')[0]['relationship']=='Non-relative'
    # The explicit resident edit may update its derived age/timestamp only; other
    # residents and every account/household remain unchanged.
    with db['conn'].cursor(cursor_factory=RealDictCursor) as cursor:after=fingerprint(cursor)
    assert before['users']==after['users'] and before['households']==after['households']
    html=db['client'].get('/view_household/1').text
    assert 'Non-relative' in html and 'Designation history' in html


def test_former_head_transfer_detaches_live_fk_but_retains_historical_ids(head_database):
    db=head_database;q=db['query'];post=db['post']
    post('/households/1/head',head_resident_id='1',head_assignment='none',head_reason='First fictional designation')
    first=q('SELECT id FROM household_head_assignments')[0]['id']
    post('/households/1/head',head_resident_id='2',head_assignment=str(first),head_reason='Explicit fictional reassignment')
    response=post('/edit_member/1',firstname='Fictional 0',surname='Independent surname',household_id='2',birthdate='2000-01-01',gender='Female',civil_status='Single',status='Active')
    assert response.status_code==302
    old=q('SELECT resident_id,resident_id_record,household_id_record FROM household_head_assignments WHERE id=%s',(first,))[0]
    assert old==dict(resident_id=None,resident_id_record=1,household_id_record=1)
    assert q('SELECT household_id FROM household WHERE id=1')[0]['household_id']==2


def test_current_head_deletion_is_blocked_and_deceased_head_can_be_reassigned(head_database):
    db=head_database;q=db['query'];post=db['post']
    post('/households/1/head',head_resident_id='1',head_assignment='none',head_reason='First fictional designation')
    assert post('/delete_member/1').status_code==409
    assignment=q('SELECT id FROM household_head_assignments')[0]['id']
    response=post('/edit_member/1',firstname='Fictional 0',surname='Independent surname',household_id='1',birthdate='2000-01-01',gender='Female',civil_status='Single',status='Deceased',death_date='2020-01-01')
    assert response.status_code==302 and 'reassignment needed' in db['client'].get('/view_household/1').text
    assert post('/households/1/head',head_resident_id='2',head_assignment=str(assignment),head_reason='Fictional deceased head reassignment').status_code==302
    assert q('SELECT status FROM household WHERE id=1')[0]['status']=='Deceased'


def test_real_age_filter_and_preview_use_age_at_death(head_database):
    data=head_database['client'].get('/api/preview/residents?status=Deceased&age_min=75&age_max=75&columns=id,full_name,age').json
    assert data['total']==10 and all(row['age']==75 for row in data['items'])


def test_real_empty_household_creation_and_duplicate_refusal(head_database):
    db=head_database;q=db['query'];post=db['post']
    response=post('/add_household',surname='New fictional home',house_number='Unique 31',address='Fictional address')
    assert response.status_code==302
    assert q('SELECT count(*) AS n FROM household')[0]['n']==120
    assert q('SELECT count(*) AS n FROM households')[0]['n']==31
    response=post('/add_household',surname='New fictional home',house_number='Unique 31',address='Fictional address')
    assert response.status_code==200 and q('SELECT count(*) AS n FROM households')[0]['n']==31
    assert q("SELECT count(*) AS n FROM audit_logs WHERE status='FAILED'")[0]['n']==1


def test_real_rollback_refuses_recorded_decisions_and_empty_rollback_preserves_originals(head_database):
    db=head_database;post=db['post'];q=db['query']
    with db['transaction']() as cursor:
        cursor.execute(DOWN.read_text())
        cursor.execute("SELECT to_regclass('household_head_assignments') AS name")
        assert cursor.fetchone()['name'] is None
        cursor.execute(UP.read_text())
    post('/households/1/head',head_resident_id='1',head_assignment='none',head_reason='Fictional designation before rollback test')
    with pytest.raises(psycopg2.Error):
        with db['transaction']() as cursor:cursor.execute(DOWN.read_text())
    assert q('SELECT count(*) AS n FROM household')[0]['n']==120
    assert q('SELECT count(*) AS n FROM household_head_assignments')[0]['n']==1
