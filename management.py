"""Server-filtered account lists; no passwords or recovery links are selected."""
from flask import abort,render_template,request
from database import transaction
from reporting import page_number

def page():
    args=request.args;tab=args.get('tab','users')
    if tab not in {'users','pending','activity'}:abort(400)
    page=page_number();limit=25;where=['TRUE'];params=[]
    search=args.get('search','').strip()[:200]
    if args.get('user_id'):
        from reporting import positive_id
        try:identifier=positive_id(args['user_id'])
        except ValueError:abort(400,description='Invalid account ID')
        where.append('id=%s');params.append(identifier)
    if search:where.append("CONCAT_WS(' ',id::text,username,email) ILIKE %s");params.append('%'+search+'%')
    for key,allowed in [('role',{'admin','user'}),('status',{'pending','approved','rejected','inactive'})]:
        if args.get(key):
            if args[key] not in allowed:abort(400)
            where.append(key+'=%s');params.append(args[key])
    if tab=='pending':where.append("status='pending'")
    with transaction() as c:
        c.execute("SELECT COUNT(*) AS total,COUNT(*) FILTER(WHERE status='pending') AS pending FROM users");totals=c.fetchone()
        if tab=='activity':
            conditions=[];values=[]
            if search:conditions.append('u.username ILIKE %s');values.append('%'+search+'%')
            if args.get('user_id'):conditions.append('u.id=%s');values.append(identifier)
            clause='WHERE '+' AND '.join(conditions) if conditions else ''
            c.execute('SELECT COUNT(*) AS total FROM password_resets p LEFT JOIN users u ON u.id=p.user_id '+clause,values);total=c.fetchone()['total']
            c.execute('SELECT u.username,p.created_at,p.used_at,p.used,p.expires_at,p.attempt_count AS attempts FROM password_resets p LEFT JOIN users u ON u.id=p.user_id '+clause+' ORDER BY p.created_at DESC,p.id DESC LIMIT %s OFFSET %s',values+[limit,(page-1)*limit]);history=c.fetchall();users=[];pending=[]
        else:
            clause=' WHERE '+' AND '.join(where)
            c.execute('SELECT COUNT(*) AS total FROM users'+clause,params);total=c.fetchone()['total']
            c.execute('SELECT id,username,email,role,status,signup_date FROM users'+clause+' ORDER BY username,id LIMIT %s OFFSET %s',params+[limit,(page-1)*limit]);rows=c.fetchall()
            users=rows if tab=='users' else [];pending=rows if tab=='pending' else [];history=[]
    from office_time import local_timestamp
    links={}
    if users or pending:
        with transaction() as c:
            c.execute('''SELECT l.account_id,l.id,l.resident_id,h.status AS resident_status FROM resident_account_links l
                LEFT JOIN household h ON h.id=l.resident_id WHERE l.account_id=ANY(%s) AND l.revoked_at IS NULL''',([r['id'] for r in users+pending],))
            links={r['account_id']:r for r in c.fetchall()}
    for row in users+pending:
        c_link=links.get(row['id'])
        row['link_status']=('Access on hold' if row['role']!='user' or row['status']!='approved' or not c_link['resident_id'] or c_link['resident_status']=='Deceased' else 'Verified and linked') if c_link else 'Not linked'
    for row in history:
        from datetime import datetime,timezone
        row['reset_status']='Used' if row.get('used_at') else 'Closed' if row.get('used') else 'Expired' if row.get('expires_at') and row['expires_at']<=datetime.now(timezone.utc).replace(tzinfo=None) else 'Awaiting use'
        row['created_display']=local_timestamp(row['created_at']);row['used_display']=local_timestamp(row.get('used_at'))
    return render_template('user_management.html',users=users,pending_users=pending,pending_count=totals['pending'],account_total=totals['total'],reset_history=history,page=page,pages=max(1,(total+limit-1)//limit),total=total,active_tab=tab)
