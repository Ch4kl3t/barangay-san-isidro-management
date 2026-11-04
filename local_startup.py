"""Read-only readiness checks and explicit synthetic seeding for disposable local DBs."""
import hashlib
import json
import secrets
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MARKER='Explicit local synthetic demo seed v1'


def require_migrations(cursor):
    cursor.execute("SELECT to_regclass('public.schema_migrations') AS name")
    if not cursor.fetchone()['name']:
        raise RuntimeError('Migrations missing. Run manage.py migrate explicitly for this disposable database.')
    cursor.execute('SELECT version,checksum FROM public.schema_migrations')
    applied={row['version']:row['checksum'] for row in cursor.fetchall()}
    expected={path.name:hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
              for path in ROOT.joinpath('migrations').glob('*.sql')}
    if applied!=expected:
        raise RuntimeError('Migration ledger missing, changed or newer than this source. Review and migrate explicitly; startup will not repair it.')


def seed_demo(cursor, credentials):
    """Caller owns transaction. Never update existing domain records or passwords."""
    from security import hash_password
    cursor.execute('SELECT pg_advisory_xact_lock(762020)')
    cursor.execute('SELECT id FROM audit_logs WHERE details=%s',(MARKER,))
    if cursor.fetchone():
        return False
    usernames=('local_demo_admin','local_demo_user')
    cursor.execute('SELECT id FROM users WHERE username=ANY(%s) OR LOWER(email)=ANY(%s)',
                   (list(usernames),[name+'@example.invalid' for name in usernames]))
    if cursor.fetchone():raise RuntimeError('Demo namespace already exists without its seed marker. No account overwritten; review privately.')
    cursor.execute("SELECT id FROM households WHERE house_number IN ('DEMO-01','DEMO-02','DEMO-EMPTY')")
    if cursor.fetchone():raise RuntimeError('Demo household namespace already exists. No records overwritten.')
    for username,role in zip(usernames,('admin','user')):
        cursor.execute("INSERT INTO users(username,password,email,role,status) VALUES(%s,%s,%s,%s,'approved')",
                       (username,hash_password(credentials[username]),username+'@example.invalid',role))
    households=[]
    for number in ('DEMO-01','DEMO-02','DEMO-EMPTY'):
        cursor.execute('INSERT INTO households(surname,house_number,address) VALUES(%s,%s,%s) RETURNING id',
                       ('Synthetic Demo Family',number,'Fictional local testing zone'))
        households.append(cursor.fetchone()['id'])
    for index in range(6):
        cursor.execute('''INSERT INTO household(firstname,middlename,surname,birthdate,gender,civil_status,
            occupation,household_id,status,registration_date,death_date,mental_health_status,current_health_status)
            VALUES(%s,'Test','Fictional Resident','2000-01-02',%s,'Single','Synthetic test role',%s,%s,
            '2026-01-01',%s,%s,%s)''',
            ('Demo '+str(index+1),'Female' if index%2 else 'Male',households[index%2],
             'Deceased' if index==5 else 'Active','2026-02-01' if index==5 else None,
             'FICTIONAL ONLY: mental health test value' if index==0 else None,
             'FICTIONAL ONLY: current health test value' if index in {0,1} else None))
    cursor.execute("INSERT INTO audit_logs(username,action_type,target_type,details) VALUES('Local synthetic seed','ADD','System',%s)",(MARKER,))
    return True


def demo_credentials(path):
    """Persist before DB commit so even an interrupted seed has recoverable credentials."""
    if path.exists():
        values=json.loads(path.read_text(encoding='utf-8'))
        if not all(isinstance(values.get(k),str) and len(values[k])>=20 for k in ('local_demo_admin','local_demo_user')):
            raise RuntimeError('Existing private demo credential file is incompatible. Preserve it and review privately.')
        return values
    values={name:secrets.token_urlsafe(24) for name in ('local_demo_admin','local_demo_user')}
    with path.open('x',encoding='utf-8') as stream:json.dump(values,stream,indent=2)
    return values
