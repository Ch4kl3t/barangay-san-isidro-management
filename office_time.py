"""Barangay calendar dates use Philippine time; audit timestamps are stored in UTC."""
from datetime import datetime, timezone, timedelta


def utc_now():
    """UTC naive for existing PostgreSQL TIMESTAMP columns; never host-local time."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def today():
    return datetime.now(timezone(timedelta(hours=8))).date()

def local_timestamp(value):
    if not value:return 'Not recorded'
    if isinstance(value,str):
        try:value=datetime.fromisoformat(value)
        except ValueError:return 'Not recorded'
    if value.tzinfo is None:value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone(timedelta(hours=8))).strftime('%b %d, %Y %I:%M:%S %p PHT')

def now_local():
    return datetime.now(timezone(timedelta(hours=8)))
