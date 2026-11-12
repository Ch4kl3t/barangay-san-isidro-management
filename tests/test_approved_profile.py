"""Synthetic account activity and preserved account actions; no external services."""
from contextlib import contextmanager
from datetime import datetime


def profile_store(monkeypatch, events):
    calls=[]
    class Cursor:
        def execute(self, query, params=()):
            self.query=query
            calls.append((query, params))
        def fetchone(self):
            if 'SELECT username,email' in self.query:
                return dict(username='Synthetic Account',email='office@example.test',signup_date=datetime(2026,1,1))
            return dict(last_login=datetime(2026,11,1))
        def fetchall(self):return events
    @contextmanager
    def transaction():yield Cursor()
    monkeypatch.setattr('webapp.database.transaction',transaction)
    return calls


def test_profile_uses_account_values_scopes_activity_and_preserves_actions(client, csrf, identity, monkeypatch):
    calls=profile_store(monkeypatch,[dict(created_at=datetime(2026,11,1),action_type='LOGIN',details='<script>private</script>',status='SUCCESS')])
    response=client.get('/profile')
    assert response.status_code==200
    html=response.get_data(as_text=True)
    assert 'Synthetic Account' in html and 'office@example.test' in html
    assert '&lt;script&gt;private&lt;/script&gt;' in html and '<script>private</script>' not in html
    assert 'PHT' in html
    queries=[(q,p) for q,p in calls if 'LIMIT 5' in q]
    assert len(queries)==1
    query,params=queries[0]
    assert 'WHERE user_id=%s' in query and "target_type='User' AND target_id=%s" in query
    assert params==(str(identity['id']),str(identity['id']))
    assert "ORDER BY created_at DESC,id DESC" in query
    assert 'action="/update_profile"' in html and 'action="/change_password"' in html
    assert html.count('name="csrf_token"')==2
    for path in ['/view_members','/view_households','/analytics','/print_reports','/audit-log']:
        assert 'href="'+path+'"' in html
    assert 'Last changed:' not in html
    assert 'Recent Account Activity' in html


def test_profile_empty_activity_and_administrator_authorization(client, identity, monkeypatch):
    calls=profile_store(monkeypatch,[])
    assert b'No account activity recorded yet.' in client.get('/profile').data
    count=len(calls)
    identity['role']='user'
    assert client.get('/profile').status_code==302
    assert len(calls)==count
