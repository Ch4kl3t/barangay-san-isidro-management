"""Explicit head decisions and relationships; no inference or existing-row backfill.

The optional additive migration enables this feature. All record mutations use
one transaction lock before row locks, preventing competing head/member changes.
Relationships belong to an assignment, so reassignment never relabels a family.
"""
from flask import g
from validation import text


def available(cursor):
    cursor.execute("""/* roles_available */ SELECT
      to_regclass('public.household_head_assignments') IS NOT NULL AND
      to_regclass('public.household_member_relationships') IS NOT NULL AS enabled""")
    return (cursor.fetchone() or {}).get('enabled') is True


def serialize(cursor):
    cursor.execute('SELECT pg_advisory_xact_lock(762022)')


def current(cursor, household_id):
    cursor.execute("""/* roles_current */ SELECT a.id,a.resident_id,a.resident_id_record,
      h.firstname,h.middlename,h.surname,
      CASE WHEN h.id IS NULL THEN NULL ELSE COALESCE(h.status,'Active') END AS status
      FROM household_head_assignments a LEFT JOIN household h ON h.id=a.resident_id
      WHERE a.household_id=%s AND a.ended_at IS NULL""", (household_id,))
    return cursor.fetchone()


def expected(head):
    return str(head['id']) if head else 'none'


def assign(cursor, household_id, resident_id, previous, reason):
    """Caller holds serialize(); existing assignments and relationships survive."""
    reason=text(reason,'Reason for head designation',300)
    cursor.execute('SELECT id FROM households WHERE id=%s FOR UPDATE',(household_id,))
    if not cursor.fetchone():raise ValueError('Household is no longer available')
    old=current(cursor,household_id)
    if previous!=expected(old):raise ValueError('The household head changed. Reload and review before saving.')
    if resident_id is not None:
        cursor.execute("""/* roles_candidate */ SELECT id,household_id,COALESCE(status,'Active') AS status
          FROM household WHERE id=%s FOR UPDATE""",(resident_id,))
        member=cursor.fetchone()
        if not member or member['household_id']!=household_id:
            raise ValueError('Choose a resident from this household')
        if member['status']!='Active':raise ValueError('Choose an active resident as the new household head')
    if (old is None and resident_id is None) or (
        old is not None and resident_id is not None and old['resident_id']==resident_id):return old
    if old:
        cursor.execute('/* roles_end */ UPDATE household_head_assignments SET ended_at=CURRENT_TIMESTAMP WHERE id=%s AND ended_at IS NULL',(old['id'],))
    new=None
    if resident_id is not None:
        cursor.execute("""/* roles_assign */ INSERT INTO household_head_assignments
          (household_id,household_id_record,resident_id,resident_id_record,assigned_by,assigned_by_record,reason)
          VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id,resident_id,resident_id_record""",
          (household_id,household_id,resident_id,resident_id,g.identity['id'],g.identity['id'],reason))
        new=cursor.fetchone()
    from account_routes import audit
    audit(cursor,'UPDATE','Household',household_id,'Household head reassigned' if old else 'Household head designated',
          old={'head_resident_id':old['resident_id_record']} if old else None,
          new={'head_resident_id':resident_id,'reason':reason},context=household_id)
    return new


def guard_transfer(cursor, old, new_household_id):
    if old and old['household_id']!=new_household_id and available(cursor):
        head=current(cursor,old['household_id'])
        if head and head['resident_id']==old['id']:
            raise ValueError('Reassign or clear this household head before transferring the resident')
        # Detach live foreign-key references only on an explicit transfer. Stable
        # recorded IDs/households/reasons/relationship text stay in history.
        cursor.execute('UPDATE household_head_assignments SET resident_id=NULL WHERE resident_id=%s AND ended_at IS NOT NULL',(old['id'],))
        cursor.execute('UPDATE household_member_relationships SET resident_id=NULL WHERE resident_id=%s',(old['id'],))


def save_member(cursor, identifier, household_id, status, form):
    if form.get('household_roles_present')!='yes':return
    if not available(cursor):raise ValueError('Household-head information is not available. Reload the form.')
    head=current(cursor,household_id)
    if form.get('head_assignment')!=expected(head):
        raise ValueError('The household or head changed. Reload and review the relationship.')
    relation=text(form.get('relationship_to_head'),'Relationship to household head',80)
    if relation and relation.casefold()=='head':
        raise ValueError('Use the household-head designation instead of entering Head as a relationship')
    role=form.get('head_role','head' if form.get('designate_head')=='yes' else 'member')
    if role not in {'member','head'}:raise ValueError('Choose Household member or Household head')
    if role=='head':
        if status!='Active':raise ValueError('A new household head must be an active resident')
        if relation:raise ValueError('Review the relationship to the new head and leave it blank unless it is accurate')
        assign(cursor,household_id,identifier,expected(head),'')
        return
    if head and head['resident_id']==identifier:
        if form.get('head_role')=='member':
            assign(cursor,household_id,None,expected(head),'')
            head=None
        else:
            if relation:raise ValueError('The designated head does not have a relationship to themselves')
            return
    if not head or head['resident_id'] is None:
        if relation:raise ValueError('Designate a household head before recording relationships')
        return
    cursor.execute('/* roles_relationship_old */ SELECT relationship FROM household_member_relationships WHERE assignment_id=%s AND resident_id=%s',(head['id'],identifier))
    old=cursor.fetchone()
    if relation==(old or {}).get('relationship'):return
    if relation:
        cursor.execute("""/* roles_relationship_save */ INSERT INTO household_member_relationships
          (assignment_id,resident_id,resident_id_record,relationship,household_id) VALUES(%s,%s,%s,%s,%s)
          ON CONFLICT(assignment_id,resident_id_record) DO UPDATE SET relationship=EXCLUDED.relationship,
            resident_id=EXCLUDED.resident_id,household_id=EXCLUDED.household_id""",
          (head['id'],identifier,identifier,relation,household_id))
    else:
        cursor.execute('/* roles_relationship_clear */ DELETE FROM household_member_relationships WHERE assignment_id=%s AND resident_id=%s',(head['id'],identifier))
    from account_routes import audit
    audit(cursor,'UPDATE','Resident',identifier,'Relationship to designated household head updated',
          old=old,new={'relationship':relation,'head_resident_id':head['resident_id_record']},context=household_id)


def context(cursor, household_id, members=()):
    result=dict(roles_enabled=available(cursor),head=None,head_assignment='none',head_history=[])
    if not result['roles_enabled']:return result
    head=current(cursor,household_id)
    result.update(head=head,head_assignment=expected(head))
    relations={}
    if head and members:
        cursor.execute('/* roles_relationships */ SELECT resident_id,relationship FROM household_member_relationships WHERE assignment_id=%s AND resident_id=ANY(%s)',(head['id'],[m['id'] for m in members]))
        relations={r['resident_id']:r['relationship'] for r in cursor.fetchall()}
    for member in members:
        member['relationship_to_head']='Head' if head and head['resident_id']==member['id'] else relations.get(member['id'])
    cursor.execute("""/* roles_history */ SELECT a.id,a.resident_id_record,a.assigned_at,a.ended_at,a.reason,
      h.firstname,h.middlename,h.surname FROM household_head_assignments a
      LEFT JOIN household h ON h.id=a.resident_id
      WHERE a.household_id_record=%s ORDER BY a.id DESC LIMIT 8""",(household_id,))
    result['head_history']=cursor.fetchall()
    from office_time import local_timestamp
    for entry in result['head_history']:
        entry['resident_name']=' '.join(entry.get(key) or '' for key in ['firstname','middlename','surname']).strip()
        entry['assigned_display']=local_timestamp(entry.get('assigned_at'))
        entry['ended_display']=local_timestamp(entry.get('ended_at'))
    if result['head_history']:
        cursor.execute('/* roles_relationship_history */ SELECT assignment_id,resident_id_record,relationship FROM household_member_relationships WHERE assignment_id=ANY(%s) ORDER BY assignment_id,resident_id_record',([h['id'] for h in result['head_history']],))
        history_relations=cursor.fetchall()
        for entry in result['head_history']:
            entry['relationships']=[r for r in history_relations if r['assignment_id']==entry['id']]
    return result


def form_context(cursor, member):
    enabled=available(cursor)
    heads={}
    if enabled:
        cursor.execute("""/* roles_choices */ SELECT a.household_id,a.id,a.resident_id,
          CONCAT_WS(' ',h.firstname,h.middlename,h.surname) AS name FROM household_head_assignments a
          LEFT JOIN household h ON h.id=a.resident_id WHERE a.ended_at IS NULL""")
        heads={str(r['household_id']):dict(assignment=str(r['id']),resident_id=r['resident_id'],name=r['name']) for r in cursor.fetchall()}
    return dict(roles_enabled=enabled,household_heads=heads)
