from contextlib import contextmanager


def test_soft_delete_user_route_updates_status(monkeypatch, client, csrf):
    class FakeCursor:
        def __init__(self):
            self.executed = []

        def execute(self, query, params=()):
            self.executed.append((query, params));self.params=params;self.query=query

        def fetchone(self):
            if self.query.startswith('SELECT id,resident_id_record'):return None
            if self.query.startswith('SELECT id,role,status') and self.params==(1,):return dict(id=1,role='admin',status='approved')
            return {'id': 2, 'username': 'bob', 'email': 'bob@example.com', 'role': 'user', 'status': 'approved'}

    cursor=FakeCursor()
    @contextmanager
    def fake_transaction(): yield cursor
    monkeypatch.setattr('account_routes.transaction',fake_transaction)
    response = client.post('/api/user/delete', json={'user_id': 2, 'delete_mode': 'soft'},headers=csrf)

    assert response.status_code == 404
    assert not cursor.executed  # General account management is deliberately retired.


def test_self_delete_is_blocked_for_current_admin(client, csrf):
    response = client.post('/api/user/delete', json={'user_id': 1, 'delete_mode': 'hard'},headers=csrf)

    assert response.status_code == 404  # Self/other account deletion has no HTTP route.
