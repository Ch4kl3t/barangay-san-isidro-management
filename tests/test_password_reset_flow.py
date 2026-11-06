"""Password recovery route and Brevo adapter tests; all database and provider calls are mocked."""
from contextlib import contextmanager
from datetime import datetime, timedelta
import re

import pytest

import account_routes
import auth_utils
import email_config
from security import token_hash, verify_password


class ResetStore:
    def __init__(self):
        self.user = dict(id=7, username='office-admin', email='office@example.test',
                         status='approved', role='admin', session_version=4)
        self.tokens = []
        self.rows = []
        self.audits = []

    def execute(self, query, params=()):
        query = ' '.join(query.split())
        self.rows = []
        if query.startswith('SELECT id,username,email FROM users'):
            if params[0] == self.user['email'].lower():
                self.rows = [{k: self.user[k] for k in ('id','username','email')}]
        elif query.startswith('UPDATE password_resets SET used=TRUE WHERE user_id='):
            for row in self.tokens:
                if row['user_id'] == params[0]:
                    row['used'] = True
        elif query.startswith('INSERT INTO password_resets'):
            self.tokens.append(dict(user_id=params[0], token_hash=params[1],
                                    expires_at=params[2], used=False))
        elif query.startswith('UPDATE password_resets SET used=TRUE,used_at='):
            row = next((item for item in self.tokens
                        if item['token_hash'] == params[0] and not item['used']), None)
            if row:
                expiry = row['expires_at']
                now = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()
                if expiry > now:
                    row['used'] = True
                    self.rows = [{'user_id': row['user_id']}]
        elif query.startswith('UPDATE users SET password='):
            hashed, user_id = params
            if (user_id == self.user['id'] and self.user['status'] == 'approved'
                    and self.user['role'] == 'admin'):
                self.user['password'] = hashed
                self.user['session_version'] += 1
                self.rows = [{'id': user_id}]
        elif query.startswith('UPDATE password_resets SET used=TRUE WHERE user_id='):
            for row in self.tokens:
                if row['user_id'] == params[0]:
                    row['used'] = True

    def fetchone(self):
        return self.rows[0] if self.rows else None


@pytest.fixture
def reset_env(app, client, monkeypatch):
    store = ResetStore()
    @contextmanager
    def transaction():
        yield store
    monkeypatch.setattr(account_routes, 'transaction', transaction)
    monkeypatch.setattr(account_routes, 'throttle', lambda *args, **kwargs: True)
    monkeypatch.setattr(account_routes, 'audit',
                        lambda cursor, action, *args, **kwargs: store.audits.append(action))
    app.config['SEND_EMAIL'] = True
    monkeypatch.setenv('APP_BASE_URL', 'https://barangay.example')
    monkeypatch.setattr(email_config, 'SENDER_EMAIL', 'office@example.test')
    return store, client


def test_reset_request_uses_public_url_and_mocked_brevo(reset_env, monkeypatch, csrf):
    store, client = reset_env
    sent = []
    monkeypatch.setattr(auth_utils, 'send_gmail_message',
                        lambda message: (sent.append(message) or (True, 'accepted')))
    response = client.post('/forgot-password', data={'email': store.user['email']},
                           headers=csrf, follow_redirects=False)
    assert response.status_code == 302 and sent
    body = '\n'.join(part.get_payload(decode=True).decode('utf-8')
                      for part in sent[0].walk() if part.get_content_maintype() == 'text')
    match = re.search(r'https://barangay\.example/reset-password/([A-Za-z0-9_-]+)', body)
    assert match and store.tokens[0]['token_hash'] == token_hash(match.group(1))
    assert store.audits == ['PASSWORD_RESET_REQUEST']
    assert 'api-key' not in str(sent[0]).lower()


def test_unknown_account_and_provider_failure_use_generic_response(reset_env, monkeypatch, csrf, caplog):
    store, client = reset_env
    sent = []
    monkeypatch.setattr(auth_utils, 'send_gmail_message',
                        lambda message: (sent.append(message) or (False, 'mock provider failure')))
    known = client.post('/forgot-password', data={'email': store.user['email']},
                        headers=csrf, follow_redirects=True)
    with client.session_transaction() as session:
        session['_csrf'] = 'test-csrf'
    unknown = client.post('/forgot-password', data={'email': 'unknown@example.test'},
                          headers=csrf, follow_redirects=True)
    generic = b'If the address is registered and eligible'
    assert known.status_code == unknown.status_code == 200
    assert generic in known.data and generic in unknown.data
    assert 'mock provider failure' not in caplog.text
    assert len(sent) == 1 and len(store.tokens) == 1
    assert store.audits == ['PASSWORD_RESET_REQUEST']


def test_valid_reset_hashes_password_revokes_sessions_and_rejects_replay(reset_env, csrf):
    store, client = reset_env
    token = 'fictional-reset-token'
    store.tokens.append(dict(user_id=7, token_hash=token_hash(token),
                             expires_at=datetime.now() + timedelta(hours=1), used=False))
    response = client.post('/reset-password/' + token,
                           data={'new_password':'synthetic-new-password',
                                 'confirm_password':'synthetic-new-password'},
                           headers=csrf, follow_redirects=False)
    assert response.status_code == 302
    assert store.user['session_version'] == 5
    assert store.user['password'] != 'synthetic-new-password'
    assert verify_password(store.user['password'], 'synthetic-new-password')
    assert store.tokens[0]['used'] is True
    assert store.audits == ['PASSWORD_RESET_SUCCESS']
    with client.session_transaction() as session:
        assert 'user_id' not in session and '_csrf' not in session
        session['_csrf'] = 'test-csrf'
    reused = client.post('/reset-password/' + token,
                         data={'new_password':'another-synthetic-password',
                               'confirm_password':'another-synthetic-password'},
                         headers=csrf)
    assert reused.status_code == 200 and b'Invalid or expired reset link' in reused.data


@pytest.mark.parametrize('token,expired', [('bad-token', False), ('expired-token', True)])
def test_invalid_and_expired_tokens_fail_safely(reset_env, csrf, token, expired):
    store, client = reset_env
    if expired:
        store.tokens.append(dict(user_id=7, token_hash=token_hash(token),
                                 expires_at=datetime.min, used=False))
    response = client.post('/reset-password/' + token,
                           data={'new_password':'synthetic-new-password',
                                 'confirm_password':'synthetic-new-password'},
                           headers=csrf)
    assert response.status_code == 200 and b'Invalid or expired reset link' in response.data
    assert 'password' not in store.user
    assert not store.audits
