"""Per-request connection ownership, and explicit transactional use outside requests."""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app, g, has_request_context
from urllib.parse import parse_qsl, urlsplit
from configuration import database_target


def connect(mode):
    url = database_target(mode)
    if mode == 'production':
        # PgBouncer rejects statement_timeout as a startup parameter. Apply both
        # settings locally to the transaction that owns all subsequent queries;
        # no session state leaks into a pooled server connection after commit.
        sslmode = dict(parse_qsl(urlsplit(url).query)).get('sslmode', 'require')
        conn = psycopg2.connect(url, sslmode=sslmode, connect_timeout=5)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT pg_catalog.set_config('statement_timeout',%s,true),"
                               " pg_catalog.set_config('TimeZone',%s,true)", ('10000', 'UTC'))
        except BaseException:
            conn.close()
            raise
        return conn
    local_options={} if mode=='production' else dict(hostaddr='::1' if urlsplit(url).hostname=='::1' else '127.0.0.1',port=5432)
    conn=psycopg2.connect(url, sslmode='require' if mode == 'production' else 'prefer',
                         connect_timeout=5, options='-c statement_timeout=10000 -c timezone=UTC',**local_options)
    if mode!='production':
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT current_database(), host(inet_server_addr()), inet_server_port()')
                name,address,port=cursor.fetchone()
            expected='barangay_test' if mode=='test' else 'barangay_dev'
            if name!=expected or address not in {'127.0.0.1','::1'} or port!=5432:
                raise RuntimeError('Connected server does not match the independently verified disposable target')
            conn.rollback()
        except Exception:
            conn.close()
            raise
    return conn


def get_db():
    conn = connect(current_app.config['APP_ENV'])
    if has_request_context():
        g.setdefault('db_connections', []).append(conn)
    return conn, conn.cursor(cursor_factory=RealDictCursor)


def cleanup(exception=None):
    for conn in g.pop('db_connections', []):
        if not conn.closed:
            conn.rollback()
            conn.close()


@contextmanager
def transaction():
    conn, cursor = get_db()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
