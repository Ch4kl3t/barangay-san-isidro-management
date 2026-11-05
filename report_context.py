"""Signed contextual report bounds shared by suggestions, preview and outputs."""
from flask import current_app,abort,g,request
from itsdangerous import URLSafeTimedSerializer,BadSignature

def serializer():return URLSafeTimedSerializer(current_app.secret_key,salt='contextual-report-v1')
def issue(args):
    from report_outputs import FILTER_KEYS
    bounds={k:str(args[k]) for k in FILTER_KEYS|{'kind','search'} if args.get(k)}
    if args.get('return_to'):
        from record_navigation import safe_destination
        bounds['return_to']=safe_destination(args['return_to'])
    if bounds.get('kind')=='households':bounds.setdefault('mode','summary')
    if bounds.get('kind')=='residents':bounds.setdefault('scope','all_matching')
    bounds['actor']=g.identity['id']
    return serializer().dumps(bounds)
def enforce(kind,args):
    args=dict(args);token=args.get('context')
    if not token:return args
    try:bound=serializer().loads(token,max_age=7200)
    except BadSignature:abort(400,description='Print context expired. Close and reopen Print Options.')
    if bound.pop('actor',None)!=g.identity['id']:abort(403)
    if bound.get('kind')!=kind:abort(400,description='Context is bound to a different report')
    if bound.get('search') and args.get('search') and args['search']!=bound['search']:args['search_extra']=args['search']
    args.update({k:v for k,v in bound.items() if k!='kind'})
    return args

def suggestions():
    from reporting import rows_for
    from database import transaction
    from flask import jsonify
    kind=request.args.get('kind','residents');args=enforce(kind,request.args)
    term=args.get('q','').strip()[:200]
    if not term:return jsonify(items=[])
    from report_outputs import validate_filters
    try:validate_filters(kind,args)
    except ValueError as exc:return jsonify(error=str(exc)),400
    if kind=='audit':
        from reporting import report_query
        from search_terms import add_search
        query,params,_,_=report_query('audit',args)
        clauses=[];actor_params=[]
        add_search(clauses,actor_params,'username',term)
        if not clauses:return jsonify(items=[])
        with transaction() as c:
            c.execute('SELECT DISTINCT username FROM (SELECT username FROM '+query+') AS actors WHERE '+' AND '.join(clauses)+' ORDER BY username LIMIT 8',[*params,*actor_params]);rows=c.fetchall()
        return jsonify(items=[dict(id=r['username'],label=r['username']) for r in rows])
    effective='residents' if kind=='households' and args.get('mode')=='members' else kind
    if effective not in {'residents','households'}:abort(400)
    from report_outputs import FILTER_KEYS
    query={k:v for k,v in args.items() if k in FILTER_KEYS|{'search'}}
    if query.get('search'):query['search_extra']=term
    else:query['search']=term
    rows,_,_=rows_for(effective,query,8)
    items=[]
    for r in rows:
        label=(r['full_name']+' · #'+str(r['id'])+' · House '+str(r.get('household_number') or 'Not recorded')) if effective=='residents' else (str(r['surname'])+' · House '+str(r.get('house_number') or 'Not recorded')+' · '+str(r.get('address') or '')[:70])
        items.append(dict(id=r['id'],label=label,type=effective))
    return jsonify(items=items)

def years():
    from database import transaction
    from flask import jsonify
    kind=request.args.get('kind','residents')
    if kind=='residents':table='household h';field='death_date' if request.args.get('date_basis')=='death' else 'registration_date';expr='h.'+field
    elif kind=='households':table='households';field='created_at';expr="(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila')"
    elif kind=='audit':table='audit_logs';field='created_at';expr="(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila')"
    else:abort(400)
    with transaction() as cursor:
        cursor.execute('SELECT DISTINCT EXTRACT(YEAR FROM '+expr+')::int AS year FROM '+table+' WHERE '+field+' IS NOT NULL ORDER BY year')
        values=[str(row['year']) for row in cursor.fetchall() if row.get('year') is not None]
    return jsonify(years=values)
