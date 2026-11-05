"""Release smoke checks with synthetic configuration and mocked baseline tables."""
import importlib
import os
import secrets

import pytest

from tests.test_defense_refinement import role_store


def test_production_wsgi_start_health_and_login_need_no_optional_schema(monkeypatch):
    for key in os.environ:
        if key.startswith('PG'):
            monkeypatch.delenv(key,raising=False)
    configuration={
        'APP_ENV':'production',
        'SECRET_KEY':secrets.token_urlsafe(48),
        'DATABASE_URL':'postgresql://fixture@release.example.invalid/barangay_san_isidro_fresh_20261104?sslmode=verify-full',
        'EXPECTED_DATABASE_HOST':'release.example.invalid',
        'EXPECTED_DATABASE_NAME':'barangay_san_isidro_fresh_20261104',
        'APP_BASE_URL':'https://release.example.invalid',
        'ENABLE_EMAIL':'0',
        'FLASK_SKIP_DOTENV':'1',
    }
    for key,value in configuration.items():monkeypatch.setenv(key,value)
    # conftest blocks every real database/socket connection before importing app.
    import app as entry
    entry=importlib.reload(entry)
    client=entry.app.test_client()
    assert entry.app.config['SESSION_COOKIE_SECURE']
    assert client.get('/health').json=={'status':'ok'}
    login=client.get('/login')
    assert login.status_code==200 and b'csrf_token' in login.data
    assert client.get('/').status_code==302


@pytest.mark.parametrize('path',[
    '/view_household/1','/resident/1','/add_member','/edit_member/1',
    '/add_household','/edit_household/1',
])
def test_baseline_pages_hide_optional_head_controls(client,role_store,path):
    role_store.enabled=False
    response=client.get(path)
    assert response.status_code==200
    assert 'id="headAssignment"' not in response.text
    assert 'name="designate_head"' not in response.text
    assert 'id="householdHeadOptions"' not in response.text
    assert all('/* roles_available */' in query for query,_ in role_store.executed if '/* roles_' in query)


def test_baseline_household_and_resident_saves_work_without_optional_tables(client,csrf,role_store):
    role_store.enabled=False
    response=client.post('/add_household',data={
        'surname':'Fictional release household','house_number':'Release-1',
        'address':'Fictional release address',
    },headers=csrf)
    assert response.status_code==302 and len(role_store.homes)==3
    response=client.post('/add_member',data={
        'firstname':'Fictional release','surname':'Independent surname',
        'household_id':'3','gender':'Female','civil_status':'Single','status':'Active',
    },headers=csrf)
    assert response.status_code==302 and role_store.members[5]['household_id']==3
    response=client.post('/edit_member/5',data={
        'firstname':'Fictional release edited','surname':'Independent surname',
        'household_id':'3','gender':'Female','civil_status':'Single','status':'Active',
    },headers=csrf)
    assert response.status_code==302 and role_store.members[5]['firstname']=='Fictional release edited'
    assert not role_store.heads and not role_store.relations
    assert all('/* roles_available */' in query for query,_ in role_store.executed if '/* roles_' in query)


def test_forged_head_submission_cannot_enable_missing_schema(client,csrf,role_store):
    role_store.enabled=False
    response=client.post('/households/1/head',data={
        'head_resident_id':'1','head_assignment':'none','head_reason':'Fictional test',
    },headers=csrf)
    assert response.status_code==409
    assert not role_store.heads and not role_store.audits
