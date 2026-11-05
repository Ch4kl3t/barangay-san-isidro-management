from pathlib import Path
import pytest
from privacy import HEALTH_FIELDS
from report_outputs import selected_columns
from reporting import report_query

def test_health_defaults_and_identity_retained():
    assert not HEALTH_FIELDS & {k for k,l in selected_columns('residents',{})}
    assert {k for k,l in selected_columns('residents',{'columns':'mental_health_status'})}=={'full_name','id','mental_health_status'}
    for kind in ['households','audit']:
        with pytest.raises(ValueError):selected_columns(kind,{'columns':'mental_health_status'})

def test_health_query_requires_live_approved_admin(app):
    from flask import g
    from werkzeug.exceptions import Forbidden
    with app.test_request_context('/'):
        for identity in [None,{'role':'user','status':'approved'},{'role':'admin','status':'pending'}]:
            g.identity=identity
            with pytest.raises(Forbidden):report_query('residents',{},HEALTH_FIELDS)
        g.identity={'role':'admin','status':'approved'}
        sql,*_=report_query('residents',{},['mental_health_status'])
        assert 'h.mental_health_status' in sql and 'h.current_health_status' not in sql

def test_flash_states_are_escaped_dismissible_once(app,identity):
    from flask import g,session,render_template
    with app.test_request_context('/profile'):
        g.identity=identity
        session['_flashes']=[('success','Saved.'),('danger','<script>bad</script>'),('warning','Review.'),('info','Information.')]
        text=render_template('base.html')
        assert text.count('data-toast-close')==4
        assert '&lt;script&gt;bad&lt;/script&gt;' in text
        assert 'app-toast--error' in text and 'role="alert"' in text
        assert '_flashes' not in session
