import pytest

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_soft_delete_user_route_updates_status(monkeypatch, client):
    class FakeCursor:
        def __init__(self):
            self.executed = []

        def execute(self, query, params=()):
            self.executed.append((query, params))

        def fetchone(self):
            return {'id': 2, 'username': 'bob', 'email': 'bob@example.com', 'role': 'user', 'status': 'approved'}

    class FakeConn:
        def __init__(self):
            self.cursor = FakeCursor()

        def commit(self):
            pass

        def close(self):
            pass

    conn = FakeConn()

    monkeypatch.setattr('app.ensure_auth_schema', lambda: None)
    monkeypatch.setattr('app.get_db', lambda: (conn, conn.cursor))
    monkeypatch.setattr('app.log_audit', lambda *args, **kwargs: None)

    with client.session_transaction() as session:
        session['role'] = 'admin'
        session['username'] = 'admin'
        session['user_id'] = 1

    response = client.post('/api/user/delete', json={'user_id': 2, 'delete_mode': 'soft'})

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    assert response.get_json()['delete_mode'] == 'soft'
    assert any('UPDATE users SET status' in query for query, _ in conn.cursor.executed)


def test_self_delete_is_blocked_for_current_admin(monkeypatch, client):
    monkeypatch.setattr('app.ensure_auth_schema', lambda: None)
    monkeypatch.setattr('app.get_db', lambda: (None, None))

    with client.session_transaction() as session:
        session['role'] = 'admin'
        session['username'] = 'admin'
        session['user_id'] = 7

    response = client.post('/api/user/delete', json={'user_id': 7, 'delete_mode': 'hard'})

    assert response.status_code == 400
    assert 'cannot delete your own' in response.get_json()['error'].lower()
