"""Per-request verified own-record access. Never returns directory/health datasets."""
from flask import abort, g, jsonify, render_template, request
from database import transaction
from validation import age_on

OWN_FIELDS = ('id','firstname','middlename','surname','birthdate','gender','civil_status',
              'occupation','status','registration_date')


def resolve(cursor):
    # Recheck both current account eligibility and current record state on each read.
    cursor.execute('''SELECT l.id,l.resident_id,l.verified_at,u.role,u.status AS account_status
        FROM resident_account_links l JOIN users u ON u.id=l.account_id
        WHERE l.account_id=%s AND l.revoked_at IS NULL''',(g.identity['id'],))
    link=cursor.fetchone()
    if not link:return dict(state='unlinked',resident=None,household=None)
    result=dict(state='hold',resident=None,household=None)
    if link['role']!='user' or link['account_status']!='approved' or not link['resident_id']:return result
    cursor.execute('SELECT '+','.join(OWN_FIELDS)+',household_id FROM household WHERE id=%s',(link['resident_id'],))
    row=cursor.fetchone()
    if not row or row['status']=='Deceased':return result
    resident={k:row[k] for k in OWN_FIELDS}
    resident['age']=age_on(row['birthdate']) if row['birthdate'] else None
    home=None
    if row['household_id']:
        cursor.execute('''SELECT hh.id,hh.surname,hh.house_number,hh.address,
            COUNT(h.id) AS recorded_members,
            COUNT(h.id) FILTER(WHERE COALESCE(h.status,'Active')<>'Deceased') AS active_members
            FROM households hh LEFT JOIN household h ON h.household_id=hh.id
            WHERE hh.id=%s GROUP BY hh.id''',(row['household_id'],))
        home=cursor.fetchone()
    return dict(state='linked',resident=resident,household=home)


def view(section='overview',resident_id=None,household_id=None):
    with transaction() as cursor:context=resolve(cursor)
    # Object parameters are never authority. Deny mismatches even on legacy aliases.
    if resident_id is not None and (not context['resident'] or context['resident']['id']!=resident_id):abort(403)
    if household_id is not None and (not context['household'] or context['household']['id']!=household_id):abort(403)
    for key,entity in [('resident_id',context['resident']),('household_id',context['household'])]:
        if key in request.args and (not entity or request.args[key]!=str(entity['id'])):abort(403)
    return render_template('resident_portal.html',section=section,**context)


def aggregate_data():
    # Deliberately no arbitrary filters, IDs, named rankings or lists.
    if request.args.get('activity')=='deleted':abort(403)
    if request.args:abort(400,description='Resident statistics are barangay-wide aggregates; filters are unavailable.')
    with transaction() as cursor:
        cursor.execute('''SELECT COUNT(*) AS recorded,COUNT(*) FILTER(WHERE COALESCE(status,'Active')<>'Deceased') AS active,
            COUNT(*) FILTER(WHERE status='Deceased') AS deceased FROM household''')
        counts=dict(cursor.fetchone())
        cursor.execute('SELECT COUNT(*) AS households FROM households')
        counts.update(cursor.fetchone())
    return counts


def statistics():return render_template('resident_statistics.html',counts=aggregate_data())
def statistics_api():return jsonify(aggregate_data())
