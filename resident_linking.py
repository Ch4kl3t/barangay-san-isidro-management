"""Administrator identity decisions, serialized and audited with their mutations."""
from flask import abort,flash,g,jsonify,redirect,render_template,request,url_for
from database import transaction
from account_routes import audit,protect_administrator_change
from reporting import positive_id
from office_time import local_timestamp


def active(cursor,account_id):
    cursor.execute('SELECT id,resident_id_record,verified_at,verified_by_record FROM resident_account_links WHERE account_id=%s AND revoked_at IS NULL',(account_id,))
    return cursor.fetchone()


def revoke(cursor,account_id,reason):
    link=active(cursor,account_id)
    if link:
        cursor.execute('UPDATE resident_account_links SET revoked_at=CURRENT_TIMESTAMP,revoked_by=%s,revocation_reason=%s WHERE id=%s',
                       (g.identity['id'],reason,link['id']))
        audit(cursor,'UNLINK_RESIDENT','User',account_id,'Resident access link revoked',old={'link_id':link['id'],'resident_id':link['resident_id_record']},new={'reason':reason})


def suggestions():
    term=request.args.get('q','').strip()[:100]
    if not term:return jsonify([])
    with transaction() as cursor:
        cursor.execute('''SELECT h.id,h.firstname,h.middlename,h.surname,h.birthdate,hh.surname AS household,hh.house_number
            FROM household h LEFT JOIN households hh ON hh.id=h.household_id
            WHERE COALESCE(h.status,'Active')<>'Deceased' AND
            CONCAT_WS(' ',h.id::text,h.firstname,h.middlename,h.surname,hh.surname,hh.house_number) ILIKE %s
            ORDER BY h.surname,h.firstname,h.id LIMIT 8''',('%'+term+'%',))
        rows=cursor.fetchall()
    return jsonify([dict(id=r['id'],label=f"{r['surname']}, {r['firstname']} {r['middlename'] or ''} / #{r['id']} / Born {r['birthdate'] or 'not recorded'} / {r['household'] or 'No household'} / House {r['house_number'] or 'not recorded'}") for r in rows])


def page(user_id):
    if request.method=='POST':
        operation=request.form.get('operation','link')
        if operation not in {'link','unlink','relink'}:abort(400)
        reason=request.form.get('reason','').strip()
        if not 3<=len(reason)<=300:abort(400,description='Enter a concise reason of 3 to 300 characters. Do not include health or identity-document details.')
        try:expected=positive_id(request.form.get('expected_link')) if request.form.get('expected_link') else None
        except ValueError:abort(400)
        try:
            with transaction() as cursor:
                account=protect_administrator_change(cursor,user_id)
                if not account:abort(404)
                if account['role']!='user' or account['status']!='approved':abort(409,description='Only approved ordinary accounts can be linked.')
                old=active(cursor,user_id)
                if (old['id'] if old else None)!=expected:abort(409,description='The link changed. Reload and review the current decision.')
                if operation=='link' and old:abort(409,description='An active link exists. Use explicit relinking.')
                if operation in {'unlink','relink'} and not old:abort(409,description='No active link to correct. Reload the page.')
                if operation!='unlink':
                    if request.form.get('verified')!='yes':abort(400,description='Explicitly confirm staff identity verification.')
                    try:resident_id=positive_id(request.form.get('resident_id'))
                    except ValueError:abort(400,description='Select an existing resident.')
                    cursor.execute('SELECT id,status FROM household WHERE id=%s FOR UPDATE',(resident_id,))
                    resident=cursor.fetchone()
                    if not resident or resident['status']=='Deceased':abort(409,description='This resident is unavailable for personal access.')
                    cursor.execute('SELECT id FROM resident_account_links WHERE resident_id=%s AND revoked_at IS NULL AND account_id<>%s',(resident_id,user_id))
                    if cursor.fetchone():abort(409,description='The resident already has an active account link.')
                if old:revoke(cursor,user_id,reason)
                if operation!='unlink':
                    cursor.execute('''INSERT INTO resident_account_links(account_id,resident_id,account_id_record,resident_id_record,verified_by,verified_by_record,verification_reason)
                        VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id''',(user_id,resident_id,user_id,resident_id,g.identity['id'],g.identity['id'],reason))
                    link_id=cursor.fetchone()['id']
                    audit(cursor,'LINK_RESIDENT','User',user_id,'Administrator verified resident access',new={'link_id':link_id,'resident_id':resident_id,'reason':reason})
            flash('Resident link decision saved. Account approval and privileges are unchanged.','success')
            return redirect(url_for('resident_link',user_id=user_id))
        except Exception as exc:
            from psycopg2 import IntegrityError
            if isinstance(exc,IntegrityError):abort(409,description='A conflicting resident link was saved. Reload and review.')
            raise
    with transaction() as cursor:
        cursor.execute('SELECT id,username,email,role,status FROM users WHERE id=%s',(user_id,))
        account=cursor.fetchone()
        if not account:abort(404)
        link=active(cursor,user_id)
        cursor.execute('''SELECT id,resident_id_record,verified_by_record,verified_at,verification_reason,revoked_at,revocation_reason
            FROM resident_account_links WHERE account_id_record=%s ORDER BY id DESC LIMIT 25''',(user_id,))
        history=cursor.fetchall()
    for item in history:item['time']=local_timestamp(item['verified_at']);item['ended']=local_timestamp(item['revoked_at'])
    return render_template('resident_link.html',account=account,link=link,history=history)
