"""Aggregated statistics keyed by immutable household identity."""
from flask import abort, g, jsonify, render_template, request
from database import transaction
from reporting import report_query, period, positive_id
from privacy import audit_value
from office_time import today as office_today
from validation import resident_age


def analytics():
    return render_template('analytics.html')


def api_dashboard():
    args=request.args.to_dict()
    activity=args.get('activity','registered')
    if activity not in {'registered','deleted'}:
        abort(400,description='Invalid activity')
    if activity=='deleted' and g.identity['role']!='admin':
        abort(403)
    try:
        month_series={key:[0]*12 for key in ['total','male','female','deceased']}
        daily_series={key:[0]*31 for key in ['total','male','female','deceased']}
        if args.get('household'):
            args['household_id']=str(positive_id(args['household']))
        query,params,_,basis=report_query('residents',args)
        with transaction() as cursor:
            if activity=='deleted':
                # New mutations emit exactly one Resident DELETE per removed resident.
                # Legacy Household DELETE snapshots also contained members; expand only those
                # whose IDs have no corresponding Resident DELETE event at that deletion time.
                cursor.execute('''SELECT id,old_value,created_at,household_context FROM audit_logs
                    WHERE action_type='DELETE' AND target_type IN ('Resident','Household') ORDER BY id''')
                import json
                from datetime import date
                logs=cursor.fetchall(); residents=[]; seen=set()
                def snapshot(log):
                    try: return json.loads(log['old_value'] or '{}')
                    except (ValueError,TypeError): return {}
                events=[]
                for log in logs:
                    snap=snapshot(log)
                    if isinstance(snap,dict) and isinstance(snap.get('members'),list):
                        home=snap.get('household')
                        home=home if isinstance(home,dict) else {}
                        for member in snap['members']:
                            if isinstance(member,dict) and member.get('firstname') is not None:
                                events.append((log,dict(member,household_identity=home)))
                    elif isinstance(snap,dict) and snap.get('firstname') is not None:
                        events.append((log,snap))
                for log,snap in events:
                    stamp=log['created_at'];
                    from datetime import datetime,timezone,timedelta
                    # No invented deletion date for legacy rows without an event
                    # timestamp. Preserve the audit row; omit it from dated series.
                    if not isinstance(stamp,datetime):continue
                    stamp=(stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp).astimezone(timezone(timedelta(hours=8)))
                    key=(str(snap.get('id')),str(stamp)[:19])
                    if key in seen: continue
                    seen.add(key)
                    if args.get('household_id') and str(snap.get('household_id'))!=args['household_id']: continue
                    if args.get('gender') and snap.get('gender')!=args['gender']: continue
                    if args.get('status') and snap.get('status')!=args['status']: continue
                    # Reuse period parsing/validation, compare against the deletion event date.
                    period(args,'created_at')
                    month=args.get('month'); year=args.get('year')
                    if month=='year': month=None;year=year or str(office_today().year)
                    if month and stamp.month!=int(month): continue
                    if year and stamp.year!=int(year): continue
                    if args.get('date_from') and stamp.date()<date.fromisoformat(args['date_from']): continue
                    if args.get('date_to') and stamp.date()>date.fromisoformat(args['date_to']): continue
                    home=snap.get('household_identity')
                    home=home if isinstance(home,dict) else {}
                    residents.append(dict(id=snap.get('id'),firstname=snap.get('firstname'),surname=snap.get('surname'),
                        gender=snap.get('gender'),status=snap.get('status'),household_id=snap.get('household_id'),
                        household=home.get('surname','Not recorded'),deleted_at=stamp.isoformat()))
                stats=dict(total=len(residents),male=sum(r['gender']=='Male' for r in residents),
                           female=sum(r['gender']=='Female' for r in residents),deceased=sum(r['status']=='Deceased' for r in residents))
                monthly=[sum(r['deleted_at'][5:7]==str(m).zfill(2) for r in residents) for m in range(1,13)]
                for row in residents:
                    event=date.fromisoformat(row['deleted_at'][:10]);m=event.month-1;d=event.day-1
                    for key,match in [('total',True),('male',row['gender']=='Male'),('female',row['gender']=='Female'),('deceased',row['status']=='Deceased')]:
                        if match:month_series[key][m]+=1;daily_series[key][d]+=1
                    row['registration_date']=row['deleted_at']
                residents=residents[:50]
                basis='Deletion event timestamp; unknown legacy events cannot be reconstructed without an audit snapshot'
            else:
                cursor.execute("SELECT COUNT(*) AS total,COUNT(*) FILTER(WHERE gender='Male') AS male,COUNT(*) FILTER(WHERE gender='Female') AS female,COUNT(*) FILTER(WHERE status='Deceased') AS deceased FROM "+query,params)
                stats=cursor.fetchone()
                event_column='death_date' if args.get('date_basis')=='death' or args.get('report_type')=='deceased' else 'registration_date'
                death_query,death_params,_,_=report_query('residents',{**args,'date_basis':'death'})
                for unit,target,length in [('MONTH',month_series,12),('DAY',daily_series,31)]:
                    cursor.execute('SELECT EXTRACT('+unit+' FROM '+event_column+")::int AS month,COUNT(*) AS total,COUNT(*) FILTER(WHERE gender='Male') AS male,COUNT(*) FILTER(WHERE gender='Female') AS female FROM "+query+' GROUP BY month',params)
                    for row in cursor.fetchall():
                        index=row.get('month')
                        if index and 1<=index<=length:
                            for key in ['total','male','female']:target[key][index-1]=row.get(key,0)
                    cursor.execute('SELECT EXTRACT('+unit+" FROM death_date)::int AS month,COUNT(*) AS total FROM "+death_query+' GROUP BY month',death_params)
                    for row in cursor.fetchall():
                        index=row.get('month')
                        if index and 1<=index<=length:target['deceased'][index-1]=row['total']
                monthly=month_series['total']
                cursor.execute('SELECT * FROM '+query+' ORDER BY surname,firstname,id LIMIT 50',params)
                residents=cursor.fetchall()
                for resident in residents:
                    try:resident['age']=resident_age(resident)
                    except ValueError:resident['age']=None
            hhargs={k:v for k,v in args.items() if k in {'household_id'}}
            hhargs['month']=args.get('household_month','')
            hhargs['year']=args.get('household_year','')
            hhargs['date_from']=args.get('household_from','')
            hhargs['date_to']=args.get('household_to','')
            # Resident filters do not imply household registration filters.
            hhargs.pop('status',None);hhargs.pop('gender',None)
            hquery,hparams,_,_=report_query('households',hhargs)
            cursor.execute('SELECT * FROM '+hquery+' ORDER BY surname,id',hparams)
            households=cursor.fetchall()
        for row in residents:
            if activity!='deleted' and g.identity['role']=='admin':
                from urllib.parse import urlencode
                from record_navigation import resident_url
                navigation={field:args[key] for key,field in [('gender','filterGender'),('status','filterStatus'),('month','filterMonth'),('year','filterYear'),('household','filterHousehold'),('household_month','filterHouseholdMonth'),('household_year','filterHouseholdYear')] if args.get(key)}
                if args.get('date_basis')=='death':navigation['filterEvent']='death'
                row['detail_url']=resident_url(row['id'],return_to='/analytics'+('?' + urlencode(navigation) if navigation else ''))
            row['household']=row.get('household_name',row.get('household'))
            row['date_of_death']=row.get('death_date')
            for field in ['registration_date','birthdate','death_date','date_of_death','status_recorded_at']:
                if hasattr(row.get(field),'isoformat'):row[field]=row[field].isoformat()
        for row in households:
            from flask import url_for
            row['detail_url']=url_for('view_household',household_id=row['id'])
            row.update(household_name=row.get('surname'),members=row.get('member_count',0),active=row.get('active_count',0),
                       deceased=row.get('deceased_count',0),male=row.get('male_members',0),female=row.get('female_members',0))
            if hasattr(row.get('registration_date'),'isoformat'):row['registration_date']=row['registration_date'].isoformat()
        def series(data,labels):
            return dict(labels=labels,datasets=[dict(stat=key,data=values[:len(labels)]) for key,values in data.items()])
        import calendar
        labels=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        month_value=args.get('month')
        days=(29 if int(month_value)==2 and not args.get('year') else calendar.monthrange(int(args.get('year') or office_today().year),int(month_value))[1]) if month_value and month_value!='year' else 31
        stats['active']=stats['total']-stats['deceased']
        return jsonify(stats=stats,residents=audit_value(residents),households=audit_value(households),date_basis=basis,
                       residents_sample=stats['total']>50,monthly=monthly,activity=activity,
                       monthData=series(month_series,labels),dailyData=series(daily_series,[str(i) for i in range(1,days+1)]))
    except ValueError as exc:
        return jsonify(error=str(exc)),400
