"""Allowlisted public resident fields and recursive audit redaction."""
HEALTH_FIELDS = {'mental_health_status', 'current_health_status'}
PRIVATE_KEYS = HEALTH_FIELDS | {'password', 'token', 'token_hash', 'csrf_token'}
RESIDENT_FIELDS = ('id', 'firstname', 'middlename', 'surname', 'age', 'birthdate',
                   'gender', 'civil_status', 'occupation', 'household_id', 'status',
                   'created_at', 'registration_date', 'status_recorded_at', 'death_date')
# Preserve the former application's legacy NULL-status interpretation consistently
# in directories/reports, without rewriting the stored record.
RESIDENT_SQL = ', '.join("COALESCE(h.status,'Active') AS status" if name=='status' else 'h.' + name for name in RESIDENT_FIELDS)


def audit_value(value):
    if isinstance(value, dict):
        return {k: audit_value(v) for k, v in value.items() if k not in PRIVATE_KEYS}
    if isinstance(value, (list, tuple)):
        return [audit_value(v) for v in value]
    return value


def public_resident(value):
    return {k: v for k, v in value.items() if k in RESIDENT_FIELDS}
