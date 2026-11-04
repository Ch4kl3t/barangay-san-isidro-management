"""Account workflows. All database/network access happens inside explicit requests."""
import secrets
from datetime import datetime, timedelta
from flask import current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from database import transaction
from office_time import utc_now
from security import hash_password, verify_password, token_hash, throttle


def audit(cursor, action, target, target_id, details, old=None, new=None, context='N/A'):
    import json
    from privacy import audit_value
    actor = g.get('identity') or {}
    new = dict(new) if isinstance(new,dict) else ({'value':new} if new is not None else {})
    if actor.get('role') in {'admin','user'}:new['_actor_role']=actor['role']
    cursor.execute('''INSERT INTO audit_logs(user_id,username,action_type,target_type,target_id,
        details,old_value,new_value,household_context,ip_address,user_agent,status)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (str(actor.get('id', 'system')), actor.get('username', 'System'), action, target,
         str(target_id), details, json.dumps(audit_value(old), default=str) if old is not None else None,
         json.dumps(audit_value(new), default=str) if new is not None else None,
         str(context), request.remote_addr, request.user_agent.string[:255], 'DENIED' if action=='LOGIN_DENIED' else 'SUCCESS'))
    from notifications import create_for_audit
    create_for_audit(cursor,action,target,target_id,details,old,new,actor.get('id'))


def protect_administrator_change(cursor,user_id,new_role=None,new_status=None,delete=False):
    # Serialize all administrator access changes, then recheck the actor under lock.
    cursor.execute('SELECT pg_advisory_xact_lock(762021)')
    cursor.execute('SELECT id,role,status FROM users WHERE id=%s FOR UPDATE',(g.identity['id'],))
    actor=cursor.fetchone()
    if not actor or actor['role']!='admin' or actor['status']!='approved':
        from flask import abort
        abort(403)
    cursor.execute('SELECT id,role,status FROM users WHERE id=%s FOR UPDATE',(user_id,))
    target=cursor.fetchone()
    if not target:return None
    removing=delete or new_role is not None and new_role!='admin' or new_status is not None and new_status!='approved'
    if removing and target['role']=='admin' and target['status']=='approved':
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='admin' AND status='approved'")
        if cursor.fetchone()['total']<=1:
            from flask import abort
            abort(409,description='At least one approved administrator must remain')
    if ((new_role is not None and new_role!=target['role']) or
        (new_status is not None and new_status!='approved') or delete):
        from resident_linking import revoke
        revoke(cursor,user_id,'Account access changed; a fresh resident verification is required')
    return target


def email_address(value):
    import re
    value = value.strip().lower()
    if len(value) > 255 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise ValueError('Enter a valid email address')
    return value


def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        with transaction() as cursor:
            allowed = throttle(cursor, 'login-ip', request.remote_addr or '', 20)
            allowed = throttle(cursor, 'login-user', username.casefold(), 10) and allowed
            cursor.execute('SELECT * FROM users WHERE username=%s', (username,))
            user = cursor.fetchone() if allowed else None
            valid = user and verify_password(user['password'], password) and user['status'] == 'approved' and user['role']=='admin'
            if not valid:
                audit(cursor, 'LOGIN_DENIED', 'System', 'N/A', 'Authentication denied')
        if valid:
            g.identity = user
            with transaction() as cursor:
                audit(cursor, 'LOGIN', 'User', user['id'], 'Authenticated')
            session.clear()
            session.update(user_id=user['id'], username=user['username'], role=user['role'],
                           session_version=user['session_version'])
            return redirect(url_for('home'))
        flash('Sign-in failed or temporarily limited. Check your credentials and account approval.', 'danger')
    return render_template('login.html')


def logout():
    session.clear()
    if g.get('identity'):
        with transaction() as cursor:audit(cursor,'LOGOUT','User',g.identity['id'],'Signed out')
    return redirect(url_for('login'))


def signup():
    return create_account(False)


def register_user():
    return create_account(True)


def create_account(admin):
    template = 'register_user.html' if admin else 'signup.html'
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            if not 3 <= len(username) <= 100:
                raise ValueError('Username must contain 3 to 100 characters')
            email = email_address(request.form.get('email', ''))
            password = request.form.get('password', '')
            if password != request.form.get('confirm_password'):
                raise ValueError('Passwords do not match')
            role = request.form.get('role', 'user') if admin else 'user'
            if role not in {'admin', 'user'}:
                raise ValueError('Invalid role')
            hashed = hash_password(password)
            with transaction() as cursor:
                if not admin and not throttle(cursor, 'signup', request.remote_addr or '', 5, 60):
                    raise ValueError('Registration is temporarily limited. Try again later.')
                cursor.execute('''INSERT INTO users(username,password,email,role,status)
                    VALUES(%s,%s,%s,%s,%s) RETURNING id''',
                    (username, hashed, email, role, 'approved' if admin else 'pending'))
                new_id = cursor.fetchone()['id']
                audit(cursor, 'ADD' if admin else 'SIGNUP', 'User', new_id, 'Account registered',
                      new={'username': username, 'role': role, 'status': 'approved' if admin else 'pending'})
            flash('Account created.' if admin else 'Request submitted. An administrator must approve access. Check with the barangay office for approval.', 'success')
            return redirect(url_for('user_management' if admin else 'login'))
        except ValueError as exc:
            flash(str(exc), 'danger')
        except Exception as exc:
            from psycopg2 import IntegrityError
            if isinstance(exc, IntegrityError):
                flash('Username or email is already registered.', 'danger')
            else:
                raise
    return render_template(template)


def update_user_status(user_id, action):
    if action not in {'approve', 'reject'}:
        return jsonify(error='Invalid action'), 400
    if user_id == g.identity['id']:
        return jsonify(error='You cannot suspend your own account'), 400
    with transaction() as cursor:
        if not protect_administrator_change(cursor,user_id,new_status='approved' if action=='approve' else 'rejected'):return jsonify(error='User not found'),404
        cursor.execute("UPDATE users SET role=CASE WHEN status='pending' THEN 'user' ELSE role END,status=%s,session_version=session_version+1 WHERE id=%s RETURNING id",
                       ('approved' if action == 'approve' else 'rejected', user_id))
        if not cursor.fetchone():
            return jsonify(error='User not found'), 404
        audit(cursor, 'UPDATE', 'User', user_id, 'Account ' + action)
    return jsonify(success=True, new_status='approved' if action == 'approve' else 'rejected')


def api_update_user_role():
    data = request.get_json(silent=True) or {}
    role = data.get('role')
    try:user_id=int(data.get('user_id'));assert user_id>0
    except (ValueError,TypeError,AssertionError):return jsonify(error='Invalid user ID'),400
    if role not in {'admin', 'user'}:
        return jsonify(error='Invalid role'), 400
    if str(user_id) == str(g.identity['id']) and role != 'admin':
        return jsonify(error='You cannot demote your own active admin account'), 400
    with transaction() as cursor:
        if not protect_administrator_change(cursor,user_id,new_role=role):return jsonify(error='User not found'),404
        cursor.execute('UPDATE users SET role=%s,session_version=session_version+1 WHERE id=%s RETURNING id', (role, user_id))
        if not cursor.fetchone():
            return jsonify(error='User not found'), 404
        audit(cursor, 'UPDATE', 'User', user_id, 'Account role changed', new={'role': role})
    return jsonify(success=True)


def api_delete_user():
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data.get('user_id'))
    except (ValueError, TypeError):
        return jsonify(error='Invalid user ID'), 400
    mode = data.get('delete_mode', data.get('mode', 'soft'))
    if mode not in {'soft', 'hard'}:
        return jsonify(error='Invalid deletion mode'), 400
    if user_id == g.identity['id']:
        return jsonify(error='You cannot delete your own account.'), 400
    with transaction() as cursor:
        if not protect_administrator_change(cursor,user_id,delete=True):
            return jsonify(error='User not found'), 404
        cursor.execute('UPDATE password_resets SET used=TRUE WHERE user_id=%s', (user_id,))
        if mode == 'hard':
            cursor.execute('DELETE FROM users WHERE id=%s', (user_id,))
        else:
            cursor.execute("UPDATE users SET status='inactive',session_version=session_version+1 WHERE id=%s", (user_id,))
        audit(cursor, 'DELETE', 'User', user_id, 'Account ' + mode + ' deletion')
    return jsonify(success=True, delete_mode=mode, new_status='inactive')


def update_profile():
    try:
        import unicodedata
        username = request.form.get('username', g.identity['username']).strip()
        # Match existing account length rules; no reserved-name list exists.
        if not 3 <= len(username) <= 100 or any(unicodedata.category(c).startswith('C') for c in username):
            raise ValueError('Username must contain 3 to 100 printable characters')
        email = email_address(request.form.get('email', ''))
        with transaction() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(762022)')
            cursor.execute('SELECT id,session_version FROM users WHERE id=%s FOR UPDATE', (g.identity['id'],))
            current = cursor.fetchone()
            if not current or current['session_version'] != g.identity['session_version']:
                raise ValueError('Account changed. Sign in again before saving.')
            cursor.execute('SELECT id FROM users WHERE lower(btrim(username))=lower(%s) AND id<>%s', (username, g.identity['id']))
            if cursor.fetchone():
                raise ValueError('Username is already registered.')
            cursor.execute('UPDATE users SET username=%s,email=%s,session_version=session_version+1 WHERE id=%s', (username, email, g.identity['id']))
            cursor.execute('UPDATE password_resets SET used=TRUE WHERE user_id=%s', (g.identity['id'],))
            audit(cursor, 'UPDATE', 'User', g.identity['id'], 'Profile updated; sessions revoked')
        session.clear()
        flash('Profile updated. Sign in again.', 'success')
        return redirect(url_for('login'))
    except ValueError as exc:
        flash(str(exc), 'danger')
    except Exception as exc:
        from psycopg2 import IntegrityError
        if isinstance(exc, IntegrityError):
            flash('Username or email is already registered.', 'danger')
        else:
            raise
    return redirect(url_for('profile'))


def change_password():
    try:
        password = request.form.get('new_password', '')
        if password != request.form.get('confirm_password'):
            raise ValueError('Passwords do not match')
        hashed = hash_password(password)
        with transaction() as cursor:
            cursor.execute('SELECT password,session_version FROM users WHERE id=%s FOR UPDATE', (g.identity['id'],))
            current = cursor.fetchone()
            if not current or current['session_version'] != g.identity['session_version']:
                raise ValueError('Account changed. Sign in again before saving.')
            if not verify_password(current['password'], request.form.get('current_password', '')):
                raise ValueError('Current password is incorrect')
            cursor.execute('UPDATE users SET password=%s,session_version=session_version+1 WHERE id=%s', (hashed, g.identity['id']))
            cursor.execute('UPDATE password_resets SET used=TRUE WHERE user_id=%s', (g.identity['id'],))
            audit(cursor, 'PASSWORD_CHANGE', 'User', g.identity['id'], 'Password changed; sessions revoked')
        session.clear()
        flash('Password changed. Sign in again.', 'success')
        return redirect(url_for('login'))
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('profile'))


def reset_origin():
    import os
    from configuration import trusted_origin
    return trusted_origin(os.getenv('APP_BASE_URL', ''), current_app.config['APP_ENV'])


def forgot_password():
    if request.method == 'POST':
        try:
            email = email_address(request.form.get('email', ''))
        except ValueError:
            email = ''
        token = secrets.token_urlsafe(32)
        recipient = None
        with transaction() as cursor:
            allowed = throttle(cursor, 'reset-ip', request.remote_addr or '', 10)
            allowed = throttle(cursor, 'reset-email', email, 3, 60) and allowed
            if allowed and email:
                cursor.execute("SELECT id,username,email FROM users WHERE LOWER(TRIM(email))=%s AND status='approved' AND role='admin'", (email,))
                recipient = cursor.fetchone()
                if recipient:
                    cursor.execute('UPDATE password_resets SET used=TRUE WHERE user_id=%s', (recipient['id'],))
                    cursor.execute('''INSERT INTO password_resets(user_id,token_hash,expires_at)
                        VALUES(%s,%s,%s)''', (recipient['id'], token_hash(token), utc_now() + timedelta(hours=1)))
                    audit(cursor, 'PASSWORD_RESET_REQUEST', 'User', recipient['id'], 'Recovery requested')
        if recipient and current_app.config['SEND_EMAIL']:
            from auth_utils import send_password_reset_email
            success, _ = send_password_reset_email(recipient['email'], recipient['username'],
                reset_origin() + url_for('reset_password', token=token))
            if not success:
                current_app.logger.warning('Recovery provider did not accept request')
        flash('If the address is registered and eligible, a reset request has been processed. Contact the office if no email arrives.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')


def reset_password(token):
    if request.method == 'POST':
        try:
            password = request.form.get('new_password', '')
            if password != request.form.get('confirm_password'):
                raise ValueError('Passwords do not match')
            hashed = hash_password(password)
            with transaction() as cursor:
                # Conditional UPDATE locks the token; a concurrent second redemption sees used=TRUE.
                cursor.execute('''UPDATE password_resets SET used=TRUE,used_at=CURRENT_TIMESTAMP
                    WHERE token_hash=%s AND used=FALSE AND expires_at>CURRENT_TIMESTAMP RETURNING user_id''', (token_hash(token),))
                record = cursor.fetchone()
                if not record:
                    raise ValueError('Invalid or expired reset link')
                cursor.execute("UPDATE users SET password=%s,session_version=session_version+1 WHERE id=%s AND status='approved' AND role='admin' RETURNING id", (hashed, record['user_id']))
                if not cursor.fetchone():
                    raise ValueError('Invalid or expired reset link')
                cursor.execute('UPDATE password_resets SET used=TRUE WHERE user_id=%s', (record['user_id'],))
                audit(cursor, 'PASSWORD_RESET_SUCCESS', 'User', record['user_id'], 'Password reset; sessions revoked')
            session.clear()
            flash('Password reset. Sign in again.', 'success')
            return redirect(url_for('login'))
        except ValueError as exc:
            flash(str(exc), 'danger')
    return render_template('reset_password.html', token=token)
