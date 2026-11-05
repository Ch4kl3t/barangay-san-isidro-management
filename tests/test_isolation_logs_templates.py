import ast
import importlib
import logging
from pathlib import Path
from contextlib import contextmanager
import pytest
from safe_logging import PrivateRequestFilter


@pytest.mark.parametrize('name',['app','check_logs','query_users','verify_email','verify_migration','fix_roles','init_db_render','setup_db','add_email','migrate_signup'])
def test_imports_never_touch_database_or_network(name):
    importlib.import_module(name)


def test_access_logging_redacts_tokens_and_queries():
    record=logging.LogRecord('werkzeug',logging.INFO,'test',1,'GET /reset-password/%s?email=%s HTTP/1.1',('RAW_RESET_TOKEN','PRIVATE_EMAIL'),None)
    PrivateRequestFilter().filter(record)
    text=record.getMessage()
    assert 'RAW_RESET_TOKEN' not in text and 'PRIVATE_EMAIL' not in text


def test_new_layout_templates_compile_and_render(client,monkeypatch):
    import webapp
    class Cursor:
        def execute(self,query,params=()):self.query=query
        def fetchone(self):
            if 'SELECT username,email' in self.query:return dict(username='Synthetic',email='synthetic@example.invalid',signup_date=None)
            return dict(total=0,pending=0,active=0,deceased=0)
        def fetchall(self):return []
    @contextmanager
    def fake():yield Cursor()
    monkeypatch.setattr(webapp.database,'transaction',fake)
    monkeypatch.setattr('record_routes.transaction',fake)
    monkeypatch.setattr('management.transaction',fake)
    for url in ['/','/profile','/print_reports','/add_member','/add_household','/analytics']:
        response=client.get(url)
        assert response.status_code==200,(url,response.status_code)
        assert b'csrf' in response.data


def test_pagination_preserves_filters(client,monkeypatch):
    monkeypatch.setattr('directory_routes.rows_for',lambda *args,**kwargs:([],121,'Registration'))
    class Counts:
        def execute(self,*args):pass
        def fetchone(self):return dict(active=0,deceased=0)
        def fetchall(self):return []
    @contextmanager
    def counts():yield Counts()
    monkeypatch.setattr('directory_routes.transaction',counts)
    response=client.get('/view_members?search=Synthetic&page=2')
    assert response.status_code==200
    assert b'search=Synthetic&amp;page=3' in response.data


def test_connection_rejects_wrong_actual_server(monkeypatch):
    import database
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,query):pass
        def fetchone(self):return ('live_records','127.0.0.1',5432)
    class Conn:
        closed=False
        def cursor(self):return Cursor()
        def close(self):self.closed=True
    conn=Conn()
    monkeypatch.setenv('ALLOW_LOCAL_DATABASE','1')
    monkeypatch.setattr('psycopg2.connect',lambda *args,**kwargs:conn)
    with pytest.raises(RuntimeError):database.connect('test')
    assert conn.closed


def test_local_connection_pins_address_and_port_despite_inherited_options(monkeypatch):
    import database
    captured={}
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,query):self.query=query
        def fetchone(self):
            host='127.0.0.1' if 'host(inet_server_addr())' in self.query else '127.0.0.1/32'
            return ('barangay_test',host,5432)
    class Conn:
        def cursor(self):return Cursor()
        def rollback(self):pass
    conn=Conn()
    def connect(*args,**kwargs):captured.update(kwargs);return conn
    monkeypatch.setenv('ALLOW_LOCAL_DATABASE','1')
    monkeypatch.setenv('DATABASE_URL','postgresql://synthetic@localhost/barangay_test')
    monkeypatch.setenv('PGHOSTADDR','192.0.2.1')
    monkeypatch.setenv('PGPORT','5433')
    monkeypatch.setattr('psycopg2.connect',connect)
    assert database.connect('test') is conn
    assert captured['hostaddr']=='127.0.0.1' and captured['port']==5432
