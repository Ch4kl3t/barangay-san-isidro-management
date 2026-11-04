"""Shared allowlisted report queries, date semantics, preview counts and Word output."""
from dataclasses import dataclass
from datetime import date,datetime
from io import BytesIO
from flask import abort, g, jsonify, render_template, request, send_file
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from database import transaction
from privacy import RESIDENT_SQL, audit_value
from office_time import today as office_today,local_timestamp,now_local
from validation import age_on
from search_terms import add_search

ACTIONS = {'ADD','UPDATE','DELETE','SIGNUP','LOGIN','LOGIN_DENIED','PASSWORD_RESET_REQUEST',
           'PASSWORD_RESET_SUCCESS','PASSWORD_CHANGE','LOGOUT','REPORT_GENERATE','LINK_RESIDENT','UNLINK_RESIDENT'}
TARGETS = {'Resident','Household','User','System'}


def period(args, column, allow_time=False):
    """Only source-owned column names may be passed here."""
    clauses, params = [], []
    month, year = args.get('month',''), args.get('year','')
    if month == 'year':
        month, year = '', year or str(office_today().year)
    if month:
        try:
            number = int(month)
            if not 1 <= number <= 12:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError('Month must be 1 to 12 or year') from None
        clauses.append(f'EXTRACT(MONTH FROM {column})=%s')
        params.append(number)
    if year:
        try:
            number = int(year)
            if not 1900 <= number <= 2200:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError('Year must be between 1900 and 2200') from None
        clauses.append(f'EXTRACT(YEAR FROM {column})=%s')
        params.append(number)
    start = args.get('date_from') or args.get('start') or ''
    end = args.get('date_to') or args.get('end') or ''
    try:
        parse=lambda value: datetime.fromisoformat(value) if allow_time and 'T' in value else date.fromisoformat(value)
        lower = parse(start) if start else None
        upper = parse(end) if end else None
    except ValueError:
        raise ValueError('Use valid YYYY-MM-DD dates') from None
    if any(isinstance(v,datetime) and v.tzinfo is not None for v in [lower,upper]):
        raise ValueError('Use Philippine local date/time values without timezone offsets')
    comparable=lambda value,end=False: value if isinstance(value,datetime) else datetime.combine(value,datetime.max.time() if end else datetime.min.time())
    if lower and upper and comparable(lower) > comparable(upper,True):
        raise ValueError('Start date must not be after end date')
    if lower:
        clauses.append(f'{column}>=%s')
        params.append(lower)
    if upper:
        clauses.append(f'{column}<=%s' if isinstance(upper,datetime) else f"{column}<(%s::date + INTERVAL '1 day')")
        params.append(upper)
    return clauses, params


def positive_id(value):
    try:
        number = int(value)
        if number < 1:
            raise ValueError()
        return number
    except (ValueError, TypeError):
        raise ValueError('Household must be a valid registered ID') from None


def report_query(kind, args, health_columns=()):
    from privacy import HEALTH_FIELDS
    health_columns = set(health_columns)
    if health_columns:
        if (kind != 'residents' or not health_columns <= HEALTH_FIELDS or not g.get('identity') or
            g.identity.get('role') != 'admin' or g.identity.get('status') != 'approved'):
            abort(403)
    clauses, params = [], []
    if kind == 'residents':
        if args.get('scope','all_matching') not in {'all_matching','resident','household'}:
            raise ValueError('Invalid resident scope; no wider report was generated')
        base = '''SELECT ''' + RESIDENT_SQL + ''.join(', h.'+key for key in sorted(health_columns)) + ''',
            TRIM(CONCAT_WS(' ',h.surname,h.firstname,h.middlename)) AS full_name,
            hh.surname AS household_name,hh.house_number AS household_number,hh.address AS household_address
            FROM household h LEFT JOIN households hh ON h.household_id=hh.id'''
        report_type = args.get('report_type', 'all')
        if report_type not in {'all','registered','deceased'}:
            raise ValueError('Invalid resident report type')
        if report_type == 'deceased':
            clauses.append("status='Deceased'")
        date_basis=args.get('date_basis','death' if report_type=='deceased' else 'registered')
        if date_basis not in {'registered','death'}:raise ValueError('Invalid resident date basis')
        column = 'death_date' if date_basis=='death' else 'registration_date'
        if date_basis=='death' and report_type!='deceased':clauses.append("status='Deceased'")
        if args.get('scope')=='resident' and not args.get('resident_id'):raise ValueError('Choose a resident ID for individual scope')
        if args.get('scope')=='household' and not args.get('household_id'):raise ValueError('Choose a household ID for member scope')
        if args.get('resident_id'):
            clauses.append('id=%s');params.append(positive_id(args['resident_id']))
        if args.get('household_id'):
            clauses.append('household_id=%s')
            params.append(positive_id(args['household_id']))
        if args.get('gender'):
            if args['gender'] not in {'Male','Female','Not recorded'}:
                raise ValueError('Invalid gender')
            clauses.append('gender=%s')
            params.append(args['gender'])
        if args.get('status'):
            if args['status'] not in {'Active','Deceased'}:
                raise ValueError('Invalid resident status')
            clauses.append('status=%s')
            params.append(args['status'])
        for search_key in ['search','search_extra']:
            if args.get(search_key):
                add_search(clauses,params,"CONCAT_WS(' ',id::text,firstname,middlename,surname,household_name)",args[search_key])
        if args.get('civil_status'):
            if args['civil_status'] not in {'Single','Married','Widowed','Separated','Not recorded'}:raise ValueError('Invalid civil status')
            clauses.append('civil_status=%s');params.append(args['civil_status'])
        ages=[]
        for key,op in [('age_min','>='),('age_max','<=')]:
            if args.get(key) not in {None,''}:
                try:number=int(args[key]);assert 0<=number<=130
                except (ValueError,TypeError,AssertionError):raise ValueError('Age must be an integer from 0 to 130') from None
                clauses.append("DATE_PART('year',AGE(%s::date,birthdate))"+op+'%s');params.extend([office_today(),number]);ages.append(number)
        if len(ages)==2 and ages[0]>ages[1]:raise ValueError('Minimum age must not exceed maximum age')
        order = 'surname,firstname,id'
        basis = 'Reported death date; unknown dates excluded only when a period is selected' if date_basis=='death' else 'Registered date; unknown legacy dates excluded only when a period is selected'
    elif kind == 'households':
        base = '''SELECT hh.id,hh.surname,hh.house_number,hh.address,hh.created_at AS registration_date,
            COUNT(h.id) AS member_count,
            COUNT(h.id) FILTER(WHERE COALESCE(h.status,'Active')<>'Deceased') AS active_count,
            COUNT(h.id) FILTER(WHERE h.status='Deceased') AS deceased_count,
            COUNT(h.id) FILTER(WHERE h.gender='Male') AS male_members,
            COUNT(h.id) FILTER(WHERE h.gender='Female') AS female_members
            FROM households hh LEFT JOIN household h ON h.household_id=hh.id
            GROUP BY hh.id'''
        column, order, basis = "(registration_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila')",'surname,id','Household-created date in Philippine time; historical provenance may be unknown'
        if args.get('household_id'):
            clauses.append('id=%s')
            params.append(positive_id(args['household_id']))
        if args.get('search') or args.get('q'):
            add_search(clauses,params,"CONCAT_WS(' ',id::text,surname,house_number,address)",args.get('search') or args.get('q'))
        if args.get('search_extra'):
            add_search(clauses,params,"CONCAT_WS(' ',id::text,surname,house_number,address)",args['search_extra'])
        if args.get('empty'):
            if args['empty'] not in {'empty','nonempty'}:raise ValueError('Invalid household membership selection')
            clauses.append('member_count=0' if args['empty']=='empty' else 'member_count>0')
        member_clauses=[];member_params=[]
        for key,allowed in [('gender',{'Male','Female','Not recorded'}),('status',{'Active','Deceased'})]:
            if args.get(key):
                if args[key] not in allowed:raise ValueError('Invalid '+key)
                member_clauses.append(('COALESCE(m.status,\'Active\')' if key=='status' else 'm.gender')+'=%s');member_params.append(args[key])
        if member_clauses:
            clauses.append('EXISTS (SELECT 1 FROM household m WHERE m.household_id=report.id AND '+' AND '.join(member_clauses)+')');params.extend(member_params)
    elif kind == 'audit':
        # Never return snapshots through standard previews/exports.
        base = 'SELECT id,username,action_type,target_type,target_id,details,status,created_at FROM audit_logs'
        column, order, basis = "(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila')",'created_at DESC,id DESC','Audit event time in Philippine time (PHT, UTC+8)'
        for key, allowed in [('action_type',ACTIONS),('target_type',TARGETS)]:
            if args.get(key):
                if args[key] not in allowed:
                    raise ValueError('Unsupported audit filter')
                clauses.append(key+'=%s')
                params.append(args[key])
        if args.get('username'):
            clauses.append('username=%s')
            params.append(args['username'][:255])
        if args.get('search'):
            add_search(clauses,params,"CONCAT_WS(' ',id::text,username,action_type,target_type,target_id,details,status)",args['search'])
        if args.get('search_extra'):
            add_search(clauses,params,"CONCAT_WS(' ',id::text,username,action_type,target_type,target_id,details,status)",args['search_extra'])
        if args.get('outcome'):
            if args['outcome'] not in {'SUCCESS','FAILED','DENIED','PENDING'}:raise ValueError('Unsupported recorded outcome')
            clauses.append('status=%s');params.append(args['outcome'])
    else:
        raise ValueError('Invalid report')
    dates, values = period(args, column,allow_time=kind=='audit')
    clauses.extend(dates)
    params.extend(values)
    query = '('+base+') AS report'
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    return query, params, order, basis


def rows_for(kind, args, limit=None, offset=0, *, health_columns=()):
    query, params, order, basis = report_query(kind,args,health_columns)
    with transaction() as cursor:
        cursor.execute('SELECT COUNT(*) AS total FROM '+query, params)
        total = cursor.fetchone()['total']
        sql = 'SELECT * FROM '+query+' ORDER BY '+order
        if limit is not None:
            sql += ' LIMIT %s OFFSET %s'
            params = [*params,limit,offset]
        cursor.execute(sql, params)
        raw = cursor.fetchall()
        rows = audit_value(raw)
        # Only the explicit, authorized output projection restores selected health.
        for row, source in zip(rows, raw):
            for key in health_columns:
                row[key] = source.get(key)
        if kind=='audit':
            for row in rows:row['created_at_display']=local_timestamp(row.get('created_at'))
        if kind=='residents':
            for row in rows:
                try:row['age']=age_on(row.get('birthdate'))
                except ValueError:row['age']=None
    return rows,total,basis


def page_number():
    try:
        return max(1,min(int(request.args.get('page',1)),100000))
    except ValueError:
        abort(400, description='Invalid page')

def page_size():
    try:value=int(request.args.get('page_size',50))
    except ValueError:abort(400,description='Invalid page size')
    if value not in {25,50,100}:abort(400,description='Choose 25, 50 or 100 rows')
    return value


def preview(kind):
    from report_outputs import preview as output
    return output(kind)


def docx_report(kind,args):
    from report_outputs import docx_report as output
    return output(kind,args)


def download(kind):
    from report_outputs import download as output
    return output(kind)
