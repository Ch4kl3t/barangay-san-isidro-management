"""Shared resident/household validation independent of Flask or database state."""
from datetime import date
from office_time import today as office_today

HEALTH_MAX = 500


def text(value, label, maximum, required=False):
    value = ' '.join((value or '').split())
    if required and not value:
        raise ValueError(label + ' is required')
    if len(value) > maximum:
        raise ValueError(f'{label} must contain at most {maximum} characters')
    return value or None


def age_on(birthdate, reference=None):
    if not birthdate:
        return None
    born = date.fromisoformat(str(birthdate))
    today = reference or office_today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def resident_age(record, reference=None):
    """A deceased resident stops aging; unknown death dates stay unknown."""
    if record.get('status')=='Deceased':
        death=record.get('death_date')
        if not death:return None
        reference=date.fromisoformat(str(death))
    value=age_on(record.get('birthdate'),reference)
    return value if value is None or value>=0 else None


def resident(form):
    data = {key: text(form.get(key), key.replace('_', ' ').title(), 255, key in {'firstname','surname'})
            for key in ('firstname','middlename','surname','occupation')}
    data['mental_health_status'] = text(form.get('mental_health_status'), 'Mental Health Status', HEALTH_MAX)
    data['current_health_status'] = text(form.get('current_health_status'), 'Current Health Status', HEALTH_MAX)
    birth = form.get('birthdate', '').strip()
    if birth:
        try:
            born = date.fromisoformat(birth)
        except ValueError:
            raise ValueError('Birthdate must be a valid date') from None
        if born > office_today() or age_on(birth) > 130:
            raise ValueError('Birthdate must be within the past 130 years')
    data['birthdate'] = birth or None
    for key, allowed in {'gender': {'Male','Female','Not recorded'},
                         'civil_status': {'Single','Married','Widowed','Separated','Not recorded'},
                         'status': {'Active','Deceased'}}.items():
        value = form.get(key, 'Active' if key == 'status' else 'Not recorded')
        if value not in allowed:
            raise ValueError('Select a valid ' + key.replace('_', ' '))
        data[key] = value
    try:
        data['household_id'] = int(form.get('household_id', ''))
        if data['household_id'] < 1:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Select a registered household') from None
    death = form.get('death_date', '').strip()
    if death:
        try:
            died = date.fromisoformat(death)
        except ValueError:
            raise ValueError('Death date must be a valid date') from None
        if data['status'] != 'Deceased' or died > office_today() or (birth and died < date.fromisoformat(birth)):
            raise ValueError('Check death date and resident status')
    data['death_date'] = death or None
    age=resident_age(data)
    data['age']=str(age) if age is not None else None
    return data


def household(form):
    return dict(surname=text(form.get('surname'), 'Household surname', 255, True),
                house_number=text(form.get('house_number'), 'House number', 100, True),
                address=text(form.get('address'), 'Address', 500, True))
