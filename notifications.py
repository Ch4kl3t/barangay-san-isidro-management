"""Recipient-specific alerts created in the same transaction as the audited change."""
from flask import abort,flash,g,jsonify,redirect,render_template,request,url_for
from database import transaction
from office_time import local_timestamp

def event_policy(action,target,target_id,details,old,new):
    if target=='User' and action in {'SIGNUP','LINK_RESIDENT','UNLINK_RESIDENT'}:return None
    if target=='User' and action in {'ADD','UPDATE','DELETE'}:return 'accounts','Staff account #'+str(target_id)+' access changed','/audit-log?target_type=User'
    if target=='Resident' and details=='Resident removed with household':return None
    if target=='Resident' and (action=='DELETE' or action=='UPDATE' and (details=='Resident transferred' or (old or {}).get('status')!=(new or {}).get('status'))):
        return 'residents','Resident #'+str(target_id)+' '+('deleted' if action=='DELETE' else 'transferred or status changed'),'/view_members' if action=='DELETE' else '/resident/'+str(int(target_id))
    if target=='Household' and (action=='DELETE' or action=='UPDATE' and any((old or {}).get(k)!=(new or {}).get(k) for k in ['surname','house_number','address'])):
        return 'households','Household #'+str(target_id)+' '+('deleted' if action=='DELETE' else 'details changed'),'/view_households' if action=='DELETE' else '/view_household/'+str(int(target_id))

def create_for_audit(cursor,action,target,target_id,details,old,new,actor_id):
    event=event_policy(action,target,target_id,details,old,new)
    if not event:return
    category,summary,destination=event
    cursor.execute("""INSERT INTO notification_events(audit_id,category,summary,destination)
        VALUES(currval(pg_get_serial_sequence('audit_logs','id')),%s,%s,%s)
        ON CONFLICT(audit_id) DO NOTHING""",(category,summary,destination))
    cursor.execute("""INSERT INTO notification_recipients(event_id,recipient_id)
        SELECT e.id,u.id FROM notification_events e CROSS JOIN users u
        WHERE e.audit_id=currval(pg_get_serial_sequence('audit_logs','id'))
        AND u.role='admin' AND u.status='approved' AND u.id IS DISTINCT FROM %s
        ON CONFLICT DO NOTHING""",(actor_id,))

def selected(limit=20):
    view=request.args.get('view','all');category=request.args.get('category','')
    if view not in {'all','unread'} or category not in {'','accounts','residents','households'}:abort(400)
    try:page=max(1,int(request.args.get('page',1)))
    except ValueError:abort(400)
    where='r.recipient_id=%s';params=[g.identity['id']]
    if view=='unread':where+=' AND r.read_at IS NULL'
    if category:where+=' AND e.category=%s';params.append(category)
    with transaction() as c:
        c.execute('SELECT COUNT(*) AS total FROM notification_recipients WHERE recipient_id=%s AND read_at IS NULL',(g.identity['id'],));unread=c.fetchone()['total']
        c.execute('SELECT COUNT(*) AS total FROM notification_events e JOIN notification_recipients r ON r.event_id=e.id WHERE '+where,params);total=c.fetchone()['total']
        c.execute('SELECT e.id,e.category,e.summary,e.created_at,r.read_at FROM notification_events e JOIN notification_recipients r ON r.event_id=e.id WHERE '+where+' ORDER BY e.created_at DESC,e.id DESC LIMIT %s OFFSET %s',params+[limit,(page-1)*limit]);items=c.fetchall()
    for item in items:item['time']=local_timestamp(item.pop('created_at'));item['unread']=item.pop('read_at') is None
    return dict(items=items,unread=unread,total=total,page=page,pages=max(1,(total+limit-1)//limit),view=view,category=category)

def api():return jsonify(selected(8))
def page():return render_template('notifications.html',**selected())

def mark(event_id):
    with transaction() as c:
        c.execute('UPDATE notification_recipients SET read_at=COALESCE(read_at,CURRENT_TIMESTAMP) WHERE event_id=%s AND recipient_id=%s RETURNING event_id',(event_id,g.identity['id']))
        if not c.fetchone():abort(404)
    return jsonify(success=True)

def open_event(event_id):
    with transaction() as c:
        c.execute('SELECT e.destination,a.target_id FROM notification_events e JOIN notification_recipients r ON r.event_id=e.id JOIN audit_logs a ON a.id=e.audit_id WHERE e.id=%s AND r.recipient_id=%s',(event_id,g.identity['id']));event=c.fetchone()
        if not event:abort(404)
        destination=event['destination']
        if destination.startswith(('/user-management','/register-user','/signup','/user_home','/user_profile','/user_view',
                                   '/my-record','/my-household','/barangay-statistics','/api/resident-link')):
            flash('This historical notification refers to a retired account workflow. Its event is preserved; no account action was taken.','info')
            destination='/notifications'
        for prefix,table in [('/resident/','household'),('/view_household/','households')]:
            if destination.startswith(prefix):
                ident=destination[len(prefix):]
                if not ident.isdigit():abort(404)
                c.execute('SELECT id FROM '+table+' WHERE id=%s',(int(ident),))
                if not c.fetchone():flash('This record is no longer available. The notification remains a record of its event.','info');destination='/view_members' if table=='household' else '/view_households'
    if not destination.startswith(('/notifications','/profile','/audit-log','/view_members','/view_households','/resident/','/view_household/')):abort(404)
    return redirect(destination)
