"""Paged read views with explicit public fields and administrator-only detail links."""
from flask import abort, g, redirect, render_template, request, url_for
from database import transaction
from reporting import rows_for, page_number,page_size
from privacy import RESIDENT_SQL
from validation import resident_age
import household_roles


def directory(kind):
    args=request.args.to_dict()
    if kind=='residents' and args.get('q') and not args.get('search'):
        args['search']=args['q']
    page=page_number();size=page_size()
    try:
        rows,total,basis=rows_for(kind,args,size,(page-1)*size)
    except ValueError as exc:
        abort(400,description=str(exc))
    pages=max(1,(total+size-1)//size)
    if page>pages:
        args['page']=str(pages)
        return redirect(url_for(request.endpoint,**args))
    if kind=='residents':
        for row in rows:
            try:
                row['age']=resident_age(row)
            except ValueError:
                row['age']=None
    context=dict(total=total,page=page,pages=max(1,(total+size-1)//size),page_size=size,basis=basis,keyword=args.get('search',args.get('q','')))
    if kind=='residents':
        from reporting import report_query
        query,params,_,_=report_query(kind,args)
        with transaction() as cursor:
            cursor.execute("SELECT COUNT(*) FILTER(WHERE status<>'Deceased') AS active,COUNT(*) FILTER(WHERE status='Deceased') AS deceased FROM "+query,params)
            counts=cursor.fetchone() or {}
            cursor.execute('SELECT id,surname,house_number FROM households ORDER BY surname,id')
            context['filter_households']=cursor.fetchall()
        context.update(members=rows,active_residents=counts.get('active',sum(r.get('status')!='Deceased' for r in rows)),
                       deceased_residents=counts.get('deceased',sum(r.get('status')=='Deceased' for r in rows)))
        template='view_members.html' if g.identity['role']=='admin' else 'user_view_members.html'
    elif kind=='households':
        context['households']=rows
        template='view_households.html' if g.identity['role']=='admin' else 'user_view_households.html'
    else:
        # The original audit UI includes expandable redacted snapshots and client filters.
        with transaction() as cursor:
            cursor.execute('SELECT id,user_id,username,action_type,target_type,target_id,details,old_value,new_value,household_context,status,ip_address,user_agent,created_at FROM audit_logs WHERE id=ANY(%s) ORDER BY created_at DESC,id DESC',([r['id'] for r in rows],))
            logs=cursor.fetchall()
            cursor.execute('SELECT DISTINCT user_id,username FROM audit_logs ORDER BY username')
            actors=cursor.fetchall()
        from audit_presentation import present
        logs=[present(log) for log in logs]
        context.update(logs=logs,total_logs=total,users=actors)
        template='audit_log.html'
    return render_template(template,**context)


def view_members(): return directory('residents')
def user_view_members():
    from resident_portal import view
    return view('record')
def view_households(): return directory('households')
def user_view_households():
    from resident_portal import view
    return view('household')
def audit_log(): return directory('audit')


def view_household(household_id):
    size=page_size()
    with transaction() as cursor:
        cursor.execute('SELECT * FROM households WHERE id=%s',(household_id,))
        household=cursor.fetchone()
        if not household: abort(404)
        fields=RESIDENT_SQL
        cursor.execute('SELECT '+fields+' FROM household h WHERE household_id=%s ORDER BY surname,firstname,id LIMIT %s OFFSET %s',
                       (household_id,size,(page_number()-1)*size))
        members=cursor.fetchall()
        cursor.execute('SELECT COUNT(*) AS total FROM household WHERE household_id=%s',(household_id,))
        total=cursor.fetchone()['total']
        roles=household_roles.context(cursor,household_id,members)
        if roles['roles_enabled']:
            cursor.execute("SELECT id,firstname,middlename,surname FROM household WHERE household_id=%s AND COALESCE(status,'Active')='Active' ORDER BY surname,firstname,id",(household_id,))
            roles['head_choices']=cursor.fetchall()
    pages=max(1,(total+size-1)//size)
    if page_number()>pages:
        args=request.args.to_dict();args['page']=str(pages)
        return redirect(url_for(request.endpoint,household_id=household_id,**args))
    for member in members:
        try:member['age']=resident_age(member)
        except ValueError:member['age']=None
    return render_template('view_household.html' if g.identity['role']=='admin' else 'user_view_household.html',household=household,members=members,total=total,
                           page=page_number(),pages=pages,page_size=size,**roles)


def user_view_household(household_id):
    from resident_portal import view
    return view('household',household_id=household_id)
