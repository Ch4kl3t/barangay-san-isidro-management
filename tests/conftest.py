"""Isolation is established before test collection imports the application."""
import os
import secrets
import socket
import urllib.request
from contextlib import contextmanager
import psycopg2
import pytest

os.environ['APP_ENV']='test'
os.environ['SECRET_KEY']=secrets.token_urlsafe(48)
os.environ['DATABASE_URL']='postgresql://blocked@127.0.0.1/barangay_test'
os.environ['ALLOW_LOCAL_DATABASE']='0'
os.environ['ENABLE_EMAIL']='0'
os.environ['APP_BASE_URL']='http://127.0.0.1:5000'


def forbidden(*args,**kwargs):
    raise AssertionError('Real database or outbound network access is blocked in isolated tests')

# Collection-time protection, including module-level imports in any test file.
psycopg2.connect=forbidden
socket.socket.connect=forbidden
socket.create_connection=forbidden
urllib.request.urlopen=forbidden


@pytest.fixture(autouse=True)
def synthetic_production_identity_pins(monkeypatch):
    # Existing production configuration cases use this nonworking synthetic
    # tuple. Tests of missing/mismatched pins explicitly override/remove it.
    monkeypatch.setenv('EXPECTED_DATABASE_HOST','example.invalid')
    monkeypatch.setenv('EXPECTED_DATABASE_NAME','records')


@pytest.fixture
def app():
    from webapp import create_app
    return create_app({'TESTING':True})


@pytest.fixture
def identity():
    return dict(id=1,username='test-admin',role='admin',status='approved',session_version=1)


@pytest.fixture
def client(app,monkeypatch,identity):
    import security
    class IdentityCursor:
        def execute(self,*args): pass
        def fetchone(self): return dict(identity) if identity else None
    @contextmanager
    def fake_identity(): yield IdentityCursor()
    monkeypatch.setattr(security,'transaction',fake_identity)
    client=app.test_client()
    with client.session_transaction() as state:
        state.update(identity)
        state['user_id']=identity['id']
        state['_csrf']='test-csrf'
    return client


@pytest.fixture
def csrf(): return {'X-CSRF-Token':'test-csrf'}
