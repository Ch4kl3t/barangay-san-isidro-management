"""Administrator record operations; audits share the mutation transaction."""
import secrets
from flask import abort, after_this_request, flash, g, jsonify, redirect, render_template, request, session, url_for
from psycopg2 import IntegrityError
from database import transaction
from account_routes import audit
from privacy import HEALTH_FIELDS, RESIDENT_SQL, audit_value
from validation import resident, household, age_on


def submission_token(operation):
    """A browser form's stable intent, without resident/health values in the token."""
    from flask import current_app
    from itsdangerous import URLSafeTimedSerializer, BadSignature
    signer=URLSafeTimedSerializer(current_app.secret_key,salt='record-submission-v1')
    supplied=request.form.get('_submission_token','')
    if supplied:
        try:
            value=signer.loads(supplied,max_age=3600)
            if value.get('actor')==g.identity['id'] and value.get('operation')==operation:return supplied
        except BadSignature:pass
    return signer.dumps(dict(actor=g.identity['id'],operation=operation,nonce=secrets.token_urlsafe(24)))


def claim_submission(cursor,operation):
    # Existing non-browser integrations retain duplicate review. Issued browser
    # intents are replay-safe even if a client ignores disabled submit controls.
    token=request.form.get('_submission_token')
    if not token:return None,None
    from flask import current_app
    from itsdangerous import URLSafeTimedSerializer,BadSignature
    from security import token_hash
    try:value=URLSafeTimedSerializer(current_app.secret_key,salt='record-submission-v1').loads(token,max_age=3600)
    except BadSignature:abort(400,description='This form expired. Reload it before saving again.')
    if value.get('actor')!=g.identity['id'] or value.get('operation')!=operation:abort(403)
    key=token_hash(token)
    cursor.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(key,))
    cursor.execute('SELECT payload FROM resident_drafts WHERE id=%s AND user_id=%s',(key,g.identity['id']))
    row=cursor.fetchone()
    if row and row['payload'].get('saved_id'):return key,row['payload']['saved_id']
    import json
    cursor.execute("INSERT INTO resident_drafts(id,user_id,payload,expires_at) VALUES(%s,%s,%s,CURRENT_TIMESTAMP+INTERVAL '2 hours') ON CONFLICT DO NOTHING",
                   (key,g.identity['id'],json.dumps(dict(submission_operation=operation))))
    return key,None


def finish_submission(cursor,key,identifier):
    if key:cursor.execute("UPDATE resident_drafts SET payload=jsonb_set(payload,'{saved_id}',to_jsonb(%s::integer)) WHERE id=%s AND user_id=%s",(identifier,key,g.identity['id']))


def households(cursor):
    cursor.execute('SELECT id,surname,house_number,address FROM households ORDER BY surname,id')
    return cursor.fetchall()


def registration_json(endpoint):
    return request.endpoint == endpoint and request.accept_mimetypes.best == 'application/json'


def registration_complete(kind, identifier):
    if kind == 'resident':
        destination, endpoint = url_for('resident_detail', id=identifier), 'add_member'
    elif kind == 'household':
        destination, endpoint = url_for('view_household', household_id=identifier), 'add_household'
    else:
        raise ValueError('Unsupported registration confirmation')
    category = f'{kind}_registered'
    response = jsonify(ok=True, redirect=destination) if registration_json(endpoint) else redirect(destination)

    @after_this_request
    def committed_confirmation(actual_response):
        # The transaction context exits before response processing. A commit error
        # produces a different error response, so it must not leave a success flash.
        if actual_response is response and not any(existing == category
                for existing, _ in session.get('_flashes', [])):
            flash(f'{kind.title()} registered successfully.', category)
        return actual_response

    return response


def resident_form(id=None):
    error = None
    duplicate_detected = False
    with transaction() as cursor:
        old = None
        if id is not None:
            cursor.execute('SELECT * FROM household WHERE id=%s FOR UPDATE', (id,))
            old = cursor.fetchone()
            if not old:
                abort(404)
        draft = session.get('resident_draft_id')
        # Draft contents are stored server-side, never in signed cookies or query strings.
        values = dict(old or {})
        if draft and id is None:
            cursor.execute('SELECT payload FROM resident_drafts WHERE id=%s AND user_id=%s AND expires_at>CURRENT_TIMESTAMP', (draft, g.identity['id']))
            saved = cursor.fetchone()
            if saved:
                values = saved['payload']
        if request.method == 'POST':
            values = request.form.to_dict()
            cursor.execute('DELETE FROM resident_drafts WHERE user_id=%s AND expires_at<=CURRENT_TIMESTAMP',(g.identity['id'],))
            if request.form.get('action') == 'new_household':
                import json
                draft = secrets.token_urlsafe(24)
                cursor.execute("DELETE FROM resident_drafts WHERE user_id=%s AND payload->>'submission_operation' IS NULL", (g.identity['id'],))
                cursor.execute("INSERT INTO resident_drafts(id,user_id,payload,expires_at) VALUES(%s,%s,%s,CURRENT_TIMESTAMP + INTERVAL '1 hour')",
                               (draft, g.identity['id'], json.dumps({k:v for k,v in values.items() if k not in {'csrf_token','action'}})))
                session['resident_draft_id'] = draft
                return redirect(url_for('add_household'))
            receipt,completed=claim_submission(cursor,'resident_create') if id is None else (None,None)
            if completed:return registration_complete('resident', completed)
            try:
                cursor.execute('SAVEPOINT resident_save')
                data = resident(request.form)
                cursor.execute('SELECT id FROM households WHERE id=%s FOR KEY SHARE', (data['household_id'],))
                if not cursor.fetchone():
                    raise ValueError('Select an existing household')
                cursor.execute('''SELECT id FROM household WHERE LOWER(TRIM(firstname))=LOWER(%s)
                    AND LOWER(TRIM(surname))=LOWER(%s) AND birthdate IS NOT DISTINCT FROM %s
                    AND id<>%s LIMIT 1''', (data['firstname'], data['surname'], data['birthdate'], id or 0))
                duplicate = cursor.fetchone()
                duplicate_detected = bool(duplicate)
                if duplicate and request.form.get('confirm_duplicate') != 'yes':
                    raise ValueError('A similar resident exists. Review it, then select the duplicate acknowledgement if this is a different person.')
                columns = list(data)
                if id is None:
                    cursor.execute('INSERT INTO household (' + ','.join(columns) + ',registration_date,status_recorded_at) VALUES (' +
                                   ','.join(['%s']*len(columns)) + ", (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::date,CURRENT_TIMESTAMP) RETURNING id", tuple(data.values()))
                    id = cursor.fetchone()['id']
                    action = 'ADD'
                else:
                    cursor.execute('UPDATE household SET ' + ','.join(c+'=%s' for c in columns) +
                                   ',status_recorded_at=CASE WHEN status IS DISTINCT FROM %s THEN CURRENT_TIMESTAMP ELSE status_recorded_at END WHERE id=%s',
                                   (*data.values(), data['status'], id))
                    action = 'UPDATE'
                health_changed = [name for name in HEALTH_FIELDS if (old or {}).get(name) != data.get(name)]
                summary = audit_value(data)
                if health_changed:
                    summary['health_information_changed'] = sorted(health_changed)
                audit(cursor, action, 'Resident', id, 'Resident created' if not old else
                      ('Resident transferred' if old['household_id'] != data['household_id'] else 'Resident updated'),
                      old=audit_value(old), new=summary, context=data['household_id'])
                finish_submission(cursor,receipt,id)
                if draft:
                    cursor.execute('DELETE FROM resident_drafts WHERE id=%s AND user_id=%s', (draft, g.identity['id']))
                    session.pop('resident_draft_id', None)
                if not old:
                    return registration_complete('resident', id)
                flash('Resident saved.', 'success')
                return redirect(url_for('resident_detail', id=id))
            except ValueError as exc:
                error = str(exc)
            except IntegrityError:
                cursor.execute('ROLLBACK TO SAVEPOINT resident_save')
                error = 'The household changed while saving. Select an existing household and try again.'
        if not values.get('household_id') and request.method == 'GET':
            values['household_id'] = request.args.get('household_id', '')
        # POST drafts intentionally contain only submitted fields. Keep the URL's
        # immutable ID available when re-rendering an invalid edit.
        if old:values['id']=old['id']
        choices = households(cursor)
    if error and not old and registration_json('add_member'):
        return jsonify(ok=False, message=error, duplicate=duplicate_detected), 422
    try:values['age']=age_on(values.get('birthdate'))
    except ValueError:values['age']=None
    selected=next((h for h in choices if str(h['id'])==str(values.get('household_id'))),None)
    labels=[dict(id=h['id'],name=f"{h['surname']} — House {h.get('house_number') or 'Not recorded'} — {h.get('address') or 'Not recorded'}") for h in choices]
    fixed=request.form.get('household_id_fixed','') if request.method=='POST' else request.args.get('household_id','')
    return render_template('edit_member.html' if old else 'add_member.html',member=values,prefill=values,
        households=choices,household_options=labels,error=error,household_id=fixed,
        household_name=next((h['name'] for h in labels if str(h['id'])==str(values.get('household_id'))),''),editing=bool(old),duplicate_detected=duplicate_detected)


def add_member():
    return resident_form()


def edit_member(id):
    return resident_form(id)


def resident_detail(id):
    # This existing GET-only administrator URL is a view, never an editing form.
    with transaction() as cursor:
        cursor.execute('SELECT '+RESIDENT_SQL+',h.mental_health_status,h.current_health_status FROM household h WHERE h.id=%s',(id,))
        member=cursor.fetchone()
        if not member:abort(404)
        cursor.execute('SELECT id,surname,house_number,address FROM households WHERE id=%s',(member['household_id'],))
        home=cursor.fetchone()
    try:member['age']=age_on(member.get('birthdate'))
    except ValueError:member['age']=None
    from record_navigation import return_destination
    return render_template('resident_detail.html',member=member,household=home,return_to=return_destination(id))


def household_form(id=None):
    error = None
    with transaction() as cursor:
        values = {}
        if id:
            cursor.execute('SELECT * FROM households WHERE id=%s', (id,))
            values = cursor.fetchone()
            if not values:
                abort(404)
        old = dict(values)
        if request.method == 'POST':
            values = request.form.to_dict()
            receipt,completed=claim_submission(cursor,'household_create') if id is None else (None,None)
            if completed:return registration_complete('household', completed)
            try:
                cursor.execute('SAVEPOINT household_save')
                data = household(values)
                cursor.execute('SELECT id FROM households WHERE LOWER(TRIM(surname))=LOWER(%s) AND LOWER(TRIM(house_number))=LOWER(%s) AND id<>%s', (data['surname'],data['house_number'],id or 0))
                if cursor.fetchone():
                    raise ValueError('This surname and house number are already registered')
                if id:
                    cursor.execute('UPDATE households SET surname=%s,house_number=%s,address=%s WHERE id=%s', (*data.values(),id))
                else:
                    cursor.execute('INSERT INTO households(surname,house_number,address) VALUES(%s,%s,%s) RETURNING id', tuple(data.values()))
                    id = cursor.fetchone()['id']
                audit(cursor, 'UPDATE' if old else 'ADD', 'Household', id, 'Household saved', old=old,new=data,context=id)
                finish_submission(cursor,receipt,id)
                draft = session.get('resident_draft_id')
                if draft and not old:
                    cursor.execute("UPDATE resident_drafts SET payload=jsonb_set(payload,'{household_id}',to_jsonb(%s::text)) WHERE id=%s AND user_id=%s AND expires_at>CURRENT_TIMESTAMP", (str(id),draft,g.identity['id']))
                    return redirect(url_for('add_member'))
                if not old:
                    return registration_complete('household', id)
                flash('Household saved.', 'success')
                return redirect(url_for('view_household', household_id=id))
            except ValueError as exc:
                error = str(exc)
            except IntegrityError:
                cursor.execute('ROLLBACK TO SAVEPOINT household_save')
                error = 'This surname and house number are already registered. Review the existing household.'
    if error and not old and registration_json('add_household'):
        return jsonify(ok=False, message=error), 422
    return render_template('add_household.html',values=values,error=error,editing=bool(old),
                           from_member='true' if session.get('resident_draft_id') else 'false')


def add_household():
    return household_form()


def edit_household(id):
    return household_form(id)


def delete_member(id):
    with transaction() as cursor:
        cursor.execute('SELECT ' + RESIDENT_SQL + ' FROM household h WHERE id=%s FOR UPDATE', (id,))
        old = cursor.fetchone()
        if not old:
            abort(404)
        cursor.execute('SELECT surname,house_number,address FROM households WHERE id=%s', (old['household_id'],))
        identity = cursor.fetchone()
        snapshot = dict(old, household_identity=identity)
        cursor.execute('DELETE FROM household WHERE id=%s', (id,))
        audit(cursor, 'DELETE', 'Resident', id, 'Resident permanently deleted', old=snapshot,context=old['household_id'])
    flash('Resident deleted.', 'success')
    return redirect(url_for('view_members'))


def delete_household(id):
    with transaction() as cursor:
        cursor.execute('SELECT * FROM households WHERE id=%s FOR UPDATE', (id,))
        old = cursor.fetchone()
        if not old:
            abort(404)
        cursor.execute('SELECT ' + RESIDENT_SQL + ' FROM household h WHERE household_id=%s FOR UPDATE', (id,))
        members = cursor.fetchall()
        for member in members:
            audit(cursor, 'DELETE', 'Resident', member['id'], 'Resident removed with household',
                  old=dict(member,household_identity=old), context=id)
        cursor.execute('DELETE FROM household WHERE household_id=%s', (id,))
        cursor.execute('DELETE FROM households WHERE id=%s', (id,))
        audit(cursor, 'DELETE', 'Household', id, 'Household deleted', old=old,
              new={'removed_residents':len(members)},context=id)
    flash(f'Household and {len(members)} resident(s) deleted.', 'success')
    return redirect(url_for('view_households'))
