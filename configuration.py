"""Explicit configuration; importing this module never loads dotenv or opens sockets."""
import os
from urllib.parse import parse_qsl, unquote, urlsplit
import ipaddress


PRODUCTION_QUERY_KEYS = {'sslmode', 'sslrootcert', 'channel_binding'}
ROUTING_ENVIRONMENT = ('PGHOST', 'PGHOSTADDR', 'PGPORT', 'PGDATABASE', 'PGUSER',
                       'PGSERVICE', 'PGSERVICEFILE', 'PGOPTIONS')


def trusted_origin(value, mode):
    """One origin contract for startup and recovery; never echo configuration."""
    try:
        if (mode not in {'production', 'development', 'test'} or not isinstance(value, str)
                or any(ord(c) < 33 or ord(c) == 127 for c in value)):
            raise ValueError()
        parsed = urlsplit(value)
        port = parsed.port  # urlsplit alone does not validate port syntax/range.
        local_http = (mode in {'development', 'test'} and parsed.scheme == 'http'
                      and parsed.hostname in {'localhost', '127.0.0.1'})
        if (not parsed.hostname or parsed.username is not None or parsed.password is not None
                or parsed.path not in {'', '/'} or parsed.query or parsed.fragment
                or port is not None and not 1 <= port <= 65535
                or not (parsed.scheme == 'https' or local_http)):
            raise ValueError()
    except (ValueError, TypeError):
        raise RuntimeError('Configure a trusted APP_BASE_URL origin (HTTPS in production)') from None
    return value.rstrip('/')


def settings():
    mode = os.getenv('APP_ENV', 'development')
    if mode not in {'development', 'test', 'production'}:
        raise RuntimeError('APP_ENV must be development, test, or production')
    secret = os.getenv('SECRET_KEY', '')
    if len(secret) < 32 or secret in {'your_secret_key_here', 'change-me'}:
        raise RuntimeError('Set SECRET_KEY to a random value of at least 32 characters')
    if mode=='production':
        trusted_origin(os.getenv('APP_BASE_URL',''), mode)
        # Validate presence/routing without opening a connection. Static liveness
        # cannot be used to infer that a missing database setting is acceptable.
        database_target(mode)
        if os.getenv('ENABLE_EMAIL', '0') not in {'0', '1'}:
            raise RuntimeError('ENABLE_EMAIL must be 0 or 1')
        if os.getenv('ENABLE_EMAIL') == '1' and (not os.getenv('BREVO_API_KEY', '').strip()
                or not os.getenv('GMAIL_ADDRESS', '').strip()):
            raise RuntimeError('Enabled production email requires provider and sender configuration')
    return dict(SECRET_KEY=secret, APP_ENV=mode, TESTING=mode == 'test',
                SESSION_SIGNING_SALT=('barangay-production-session-v2:'+
                    os.getenv('EXPECTED_DATABASE_HOST','')+'/'+os.getenv('EXPECTED_DATABASE_NAME',''))
                    if mode=='production' else 'cookie-session',
                SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                SESSION_COOKIE_SECURE=mode == 'production',
                MAX_CONTENT_LENGTH=1024 * 1024, SEND_EMAIL=mode == 'production' and
                os.getenv('ENABLE_EMAIL') == '1')


def database_target(mode):
    url = os.getenv('DATABASE_URL', '')
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise RuntimeError('A valid PostgreSQL DATABASE_URL is required') from None
    if parsed.scheme not in {'postgres', 'postgresql'} or not parsed.hostname:
        raise RuntimeError('A PostgreSQL DATABASE_URL is required')
    if mode == 'production':
        try:
            query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        except ValueError:
            raise RuntimeError('Production database connection options are invalid') from None
        keys = [k for k, _ in query]
        options = dict(query)
        hostname = parsed.hostname.lower().rstrip('.')
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        name = unquote(parsed.path[1:]) if parsed.path.startswith('/') else ''
        if (not parsed.username or not name or '/' in name or parsed.fragment or
                any(ord(c)<33 for c in name + hostname + unquote(parsed.username)) or
                hostname in {'localhost', 'localhost.localdomain'} or
                hostname.endswith('.localhost') or any(c in hostname for c in {'%', ',', '/', '\\'}) or
                address is not None and not address.is_global or
                name in {'barangay_dev', 'barangay_test', 'barangay_restore_verify_20261102',
                         'barangay_migration_rehearsal_20261102'} or
                port is not None and not 1 <= port <= 65535):
            raise RuntimeError('Production requires an explicit remote database and user')
        if (len(keys) != len(set(keys)) or set(keys) - PRODUCTION_QUERY_KEYS or
                options.get('sslmode', 'require') not in {'require', 'verify-ca', 'verify-full'} or
                options.get('channel_binding', 'prefer') not in {'require', 'prefer', 'disable'} or
                any(not value for value in options.values()) or
                any(os.getenv(k) for k in ROUTING_ENVIRONMENT)):
            raise RuntimeError('Production database routing overrides or unsafe TLS options are refused')
        # Independent nonsecret pins prevent a retained old DATABASE_URL from
        # selecting the previous database during the fresh-database cutover.
        if (os.getenv('EXPECTED_DATABASE_HOST', '') != hostname or
                os.getenv('EXPECTED_DATABASE_NAME', '') != name):
            raise RuntimeError('Production DATABASE_URL must match EXPECTED_DATABASE_HOST and EXPECTED_DATABASE_NAME')
    if mode != 'production':
        if parsed.query or parsed.fragment:
            raise RuntimeError('Local database URLs must not contain connection-option overrides')
        expected = 'barangay_test' if mode == 'test' else 'barangay_dev'
        try:
            port=parsed.port or 5432
        except ValueError:
            raise RuntimeError('Local PostgreSQL requires port 5432') from None
        if port!=5432:
            raise RuntimeError('Local PostgreSQL requires port 5432')
        if parsed.hostname not in {'localhost', '127.0.0.1', '::1'} or parsed.path != '/' + expected:
            raise RuntimeError('Local mode requires a loopback disposable barangay_dev/barangay_test database')
        if os.getenv('ALLOW_LOCAL_DATABASE') != '1':
            raise RuntimeError('Verify the disposable database, then set ALLOW_LOCAL_DATABASE=1')
    return url
