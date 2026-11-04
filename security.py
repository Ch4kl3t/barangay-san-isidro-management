"""Authentication, CSRF, session revocation, and privacy boundaries."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from flask import abort, current_app, g, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database import transaction
from office_time import utc_now

PUBLIC = {'static', 'login', 'forgot_password', 'reset_password', 'health'}


def hash_password(password):
    if not isinstance(password, str) or not 8 <= len(password) <= 200:
        raise ValueError('Password must contain 8 to 200 characters')
    return generate_password_hash(password, method='scrypt')


def verify_password(stored, supplied):
    # Plaintext accounts must be explicitly migrated by the offline management command.
    if not isinstance(supplied,str) or len(supplied)>200:
        return False
    try:
        return bool(stored and stored.startswith(('scrypt:', 'pbkdf2:')) and
                    check_password_hash(stored, supplied))
    except (ValueError,TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']


def throttle(cursor, category, identity, limit=5, minutes=15):
    key = token_hash(category + ':' + identity)
    # Serialize requests for this identity across workers, not just in one process.
    cursor.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (key,))
    cursor.execute('SELECT COUNT(*) AS total FROM auth_attempts WHERE key_hash=%s AND created_at > %s',
                   (key, utc_now() - timedelta(minutes=minutes)))
    allowed = cursor.fetchone()['total'] < limit
    if allowed:
        cursor.execute('INSERT INTO auth_attempts(key_hash) VALUES(%s)', (key,))
    return allowed


def protect_request():
    g.identity = None
    if request.endpoint is not None and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
        expected = session.get('_csrf', '')
        # Session-generated CSRF tokens are ASCII. compare_digest(str, str)
        # raises TypeError for a non-ASCII submitted form value.
        if (not isinstance(expected, str) or not isinstance(supplied, str) or
                not expected or not expected.isascii() or not supplied.isascii() or
                not hmac.compare_digest(expected, supplied)):
            abort(400, description='The form expired. Reload the page and try again.')
    if request.endpoint in {'static', 'health'}:
        return
    if 'user_id' in session:
        with transaction() as cursor:
            cursor.execute('SELECT id,username,role,status,session_version FROM users WHERE id=%s',
                           (session['user_id'],))
            user = cursor.fetchone()
        if (not user or user['status'] != 'approved' or user['role'] != 'admin' or user['role'] != session.get('role') or
                user['session_version'] != session.get('session_version')):
            session.clear()
        else:
            g.identity = user
    # Unknown/retired endpoints still recheck and clear obsolete signed sessions.
    if request.endpoint is None:
        return
    if request.endpoint not in PUBLIC and not g.identity:
        if request.path.startswith('/api/'):
            return jsonify(error='Authentication required'), 401
        return redirect(url_for('login'))


def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store'
    return response
