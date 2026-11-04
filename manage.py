"""Explicit local database management. Does not import Flask or load .env."""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
from psycopg2.extras import RealDictCursor
from database import connect
from security import hash_password
from datetime import date
from office_time import today as office_today


def resident_preflight(cursor):
    problems=[]
    cursor.execute('SELECT birthdate,firstname,surname,household_id,gender,status,civil_status,mental_health_status,current_health_status FROM household')
    for row in cursor.fetchall():
        try:
            value=str(row['birthdate']).strip() if row['birthdate'] else ''
            born=date.fromisoformat(value) if value else None
            if born and born>office_today():
                raise ValueError()
        except ValueError:
            problems.append('Invalid or future resident birthdates')
        if not row['firstname'] or not row['firstname'].strip() or not row['surname'] or not row['surname'].strip():
            problems.append('Missing resident names')
        if row['household_id'] is None:
            problems.append('Unassigned residents')
        for key,allowed in [('gender',{'Male','Female','Not recorded'}),('status',{'Active','Deceased'}),
                            ('civil_status',{'Single','Married','Widowed','Separated','Not recorded'})]:
            if row[key] is not None and row[key] not in allowed:
                problems.append('Unsupported '+key+' values')
        if any(row.get(key) is not None and len(row[key])>500 for key in ['mental_health_status','current_health_status']):
            problems.append('Oversized health information')
    if problems:
        raise RuntimeError('Migration stopped without corrections: '+'; '.join(sorted(set(problems))))


def preflight(cursor, schema='public'):
    required={
        'users': {'id','username','password','email','role','status','signup_date'},
        'households': {'id','surname','house_number','address','created_at'},
        'household': {'id','firstname','middlename','surname','age','birthdate','gender','civil_status','occupation','household_id','status','created_at'},
        'audit_logs': {'id','user_id','username','action_type','target_type','target_id','old_value','new_value','details','household_context','status','ip_address','user_agent','created_at'},
        'password_resets': {'id','username','token','created_at','expires_at','used','used_at','ip_address','attempt_count'},
    }
    # Report schema names only, never resident data. A competing legacy layout needs
    # an owner-reviewed mapping; do not manufacture surname or event dates for it.
    for table,columns in required.items():
        cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s',(schema,table))
        existing={row['column_name'] for row in cursor.fetchall()}
        missing=columns-existing
        if missing:
            raise RuntimeError('Unsupported legacy shape: '+table+' missing '+', '.join(sorted(missing))+'. Review mapping before migration.')
        if table=='household':
            for column in ['mental_health_status','current_health_status']:
                if column in existing:
                    cursor.execute('SELECT COUNT(*) AS total FROM household WHERE length('+column+')>500')
                    if cursor.fetchone()['total']:
                        raise RuntimeError('Migration stopped before constraints: oversized health information; review privately')
    checks = [
        ("SELECT 1 FROM users GROUP BY LOWER(TRIM(email)) HAVING LOWER(TRIM(email))<>'' AND COUNT(*)>1", 'Duplicate normalized recovery emails'),
        ("SELECT 1 FROM households GROUP BY LOWER(TRIM(surname)),LOWER(TRIM(house_number)) HAVING COUNT(*)>1", 'Duplicate household identities'),
        ('SELECT 1 FROM household h LEFT JOIN households hh ON hh.id=h.household_id WHERE h.household_id IS NOT NULL AND hh.id IS NULL', 'Orphan household memberships'),
    ]
    problems = []
    for query, label in checks:
        cursor.execute(query)
        if cursor.fetchone():
            problems.append(label)
    if problems:
        raise RuntimeError('Migration stopped without corrections: ' + '; '.join(problems))


def apply_migrations(cursor, schema='public'):
    """Caller owns the transaction; the normal management command uses public.

    An explicit schema lets real integration tests exercise this same runner in
    their own disposable namespace, never the database's existing public tables.
    """
    cursor.execute('SELECT current_schema() AS name')
    if cursor.fetchone()['name'] != schema:
        raise RuntimeError('Migration schema does not match the explicitly selected search path')
    cursor.execute('SELECT pg_advisory_xact_lock(762019)')
    cursor.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    applied=[]
    for path in sorted(Path(__file__).parent.joinpath('migrations').glob('*.sql')):
        content=path.read_text(encoding='utf-8')
        checksum=hashlib.sha256(content.encode()).hexdigest()
        cursor.execute('SELECT checksum FROM schema_migrations WHERE version=%s',(path.name,))
        row=cursor.fetchone()
        if row:
            if row['checksum']!=checksum:
                raise RuntimeError('Applied migration checksum mismatch')
            continue
        if path.name.startswith('002'):preflight(cursor,schema)
        if path.name.startswith('004'):resident_preflight(cursor)
        cursor.execute(content)
        cursor.execute('INSERT INTO schema_migrations(version,checksum) VALUES(%s,%s)',(path.name,checksum))
        applied.append(path.name)
    return applied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'migrate', 'hash-passwords', 'create-admin', 'reset-password', 'purge-expired'])
    parser.add_argument('--database', required=True, choices=['barangay_dev', 'barangay_test'])
    parser.add_argument('--username')
    parser.add_argument('--email')
    parser.add_argument('--private-config',action='store_true',help='Use the existing ignored configuration for the selected local target')
    args = parser.parse_args()
    mode = 'test' if args.database == 'barangay_test' else 'development'
    if args.private_config:
        import json
        try:private=json.loads((Path(__file__).resolve().parent/'.local'/(mode+'.json')).read_text(encoding='utf-8'))
        except (OSError,ValueError):raise RuntimeError('Private local configuration is missing or unreadable; values omitted') from None
        if not private.get('DATABASE_URL'):raise RuntimeError('Private local database URL is missing; values omitted')
        os.environ.update(APP_ENV=mode,DATABASE_URL=private['DATABASE_URL'],ALLOW_LOCAL_DATABASE='1',ENABLE_EMAIL='0',FLASK_SKIP_DOTENV='1')
    if os.getenv('APP_ENV', 'development') != mode:
        parser.error('APP_ENV must match the explicitly selected local database')
    conn = connect(mode)
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('SELECT current_database() AS name, inet_server_addr() AS address')
                actual = cursor.fetchone()
                if actual['name'] != args.database or str(actual['address']) not in {'127.0.0.1', '::1'}:
                    raise RuntimeError('Server identity does not match the disposable loopback target')
                print('Verified disposable database:', args.database)
                if args.command == 'check':
                    return
                if args.command == 'migrate':
                    for version in apply_migrations(cursor):
                        print('Applied:',version)
                elif args.command == 'hash-passwords':
                    cursor.execute('SELECT id,password FROM users FOR UPDATE')
                    count = 0
                    for user in cursor.fetchall():
                        password = user['password']
                        if not password.startswith(('scrypt:', 'pbkdf2:')):
                            # Preserve legacy whitespace behavior; never print the credential.
                            cursor.execute('UPDATE users SET password=%s,session_version=session_version+1 WHERE id=%s',
                                           (hash_password(password), user['id']))
                            count += 1
                    cursor.execute('UPDATE password_resets SET used=TRUE')
                    print('Migrated account count:', count)
                elif args.command == 'purge-expired':
                    cursor.execute('DELETE FROM resident_drafts WHERE expires_at<=CURRENT_TIMESTAMP')
                    cursor.execute("DELETE FROM auth_attempts WHERE created_at<CURRENT_TIMESTAMP-INTERVAL '1 day'")
                    cursor.execute('DELETE FROM password_resets WHERE expires_at<=CURRENT_TIMESTAMP')
                    print('Expired drafts, reset links and throttle history purged')
                elif args.command == 'create-admin':
                    from account_routes import email_address
                    if not args.username or not 3 <= len(args.username) <= 100 or not args.email:
                        parser.error('Provide --username and --email')
                    password = getpass.getpass('New administrator password: ')
                    if password != getpass.getpass('Confirm password: '):
                        raise RuntimeError('Passwords do not match')
                    cursor.execute("INSERT INTO users(username,email,password,role,status) VALUES(%s,%s,%s,'admin','approved')",
                                   (args.username, email_address(args.email), hash_password(password)))
                    print('Administrator created; no existing account overwritten')
                elif args.command == 'reset-password':
                    if not args.username:parser.error('Provide --username')
                    password=getpass.getpass('New password for the selected local account: ')
                    if password!=getpass.getpass('Confirm password: '):raise RuntimeError('Passwords do not match')
                    cursor.execute('UPDATE users SET password=%s,session_version=session_version+1 WHERE username=%s RETURNING id',
                                   (hash_password(password),args.username))
                    row=cursor.fetchone()
                    if not row:raise RuntimeError('Local account not found')
                    cursor.execute('UPDATE password_resets SET used=TRUE WHERE user_id=%s',(row['id'],))
                    cursor.execute("INSERT INTO audit_logs(username,action_type,target_type,target_id,details) VALUES('Local maintenance','PASSWORD_CHANGE','User',%s,'Controlled local credential reset; sessions revoked')",(str(row['id']),))
                    print('Selected local credential reset; role and account status unchanged')
    finally:
        conn.close()


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:
        # Constraint/provider errors may contain full rows or connection strings.
        raise SystemExit('Operation rolled back: '+type(exc).__name__+'. Review schema/data using a private database administration session.') from None
