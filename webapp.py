"""Existing URL contracts composed from focused services. Imports perform no I/O."""
from flask import Flask, abort, g, jsonify, render_template, request, session, url_for
from flask.sessions import SecureCookieSessionInterface
from werkzeug.exceptions import HTTPException
import account_routes
import dashboard_routes
import database
import directory_routes
import record_routes
import reporting
import security
from configuration import settings
from auth_utils import require_role
import safe_logging
import report_outputs


def create_app(overrides=None):
    safe_logging.configure()
    app = Flask(__name__)
    app.config.update(settings())
    if overrides:
        app.config.update(overrides)
    # A fresh database can reuse account ID1. Bind production signatures to the
    # pinned database so a cookie from the old dataset cannot become that admin.
    app.session_interface=SecureCookieSessionInterface()
    app.session_interface.salt=app.config['SESSION_SIGNING_SALT']
    app.teardown_appcontext(database.cleanup)
    app.before_request(security.protect_request)
    def presentation_headers(response):
        response=security.response_headers(response)
        # Only these public, versioned icons are cacheable; private pages remain no-store.
        if (request.endpoint=='static' and response.status_code in {200,304}
                and (request.view_args or {}).get('filename') in {
                    'icons/favicon.svg','icons/favicon-32.png','icons/favicon.ico'}):
            response.headers['Cache-Control']='public, max-age=86400'
        return response
    app.after_request(presentation_headers)
    app.jinja_env.globals['csrf_token'] = security.csrf_token
    app.jinja_env.globals['submission_token'] = record_routes.submission_token

    def route(path, endpoint, handler, roles=(), methods=('GET',)):
        app.add_url_rule(path, endpoint,
                         require_role(*roles)(handler) if roles else handler,
                         methods=list(methods))

    for path, name in [('/login','login'),
                       ('/forgot-password','forgot_password'),('/reset-password/<token>','reset_password')]:
        route(path,name,getattr(account_routes,name),methods=('GET','POST'))
    route('/logout','logout',account_routes.logout,methods=('POST',))
    for path,name in [('/update_profile','update_profile'),('/change_password','change_password')]:
        route(path,name,getattr(account_routes,name),('admin',),('POST',))
    for path,name in [('/view_members','view_members'),('/view_households','view_households'),
                      ('/audit-log','audit_log'),('/view_household/<int:household_id>','view_household')]:
        route(path,name,getattr(directory_routes,name),('admin',))
    for path,name,methods in [('/add_member','add_member',('GET','POST')),
                              ('/edit_member/<int:id>','edit_member',('GET','POST')),
                              ('/resident/<int:id>','resident_detail',('GET',)),
                              ('/delete_member/<int:id>','delete_member',('POST',)),
                              ('/add_household','add_household',('GET','POST')),
                              ('/edit_household/<int:id>','edit_household',('GET','POST')),
                              ('/delete_household/<int:id>','delete_household',('POST',))]:
        route(path,name,getattr(record_routes,name),('admin',),methods)
    route('/analytics','analytics',dashboard_routes.analytics,('admin',))
    route('/api/dashboard','api_dashboard',dashboard_routes.api_dashboard,('admin',))
    route('/households/<int:household_id>/head','set_household_head',record_routes.set_household_head,('admin',),('POST',))
    for kind,path,name in [('residents','/print_all_members','print_all_members'),
                           ('households','/print_households_report','print_households_report'),
                           ('audit','/print_audit_logs_report','print_audit_logs_report')]:
        route(path,name,lambda kind=kind: reporting.download(kind),('admin',))
        route('/api/preview/'+kind,'api_preview_'+kind,lambda kind=kind: reporting.preview(kind),('admin',))
        route('/reports/print/'+kind,'print_view_'+kind,lambda kind=kind: report_outputs.print_view(kind),('admin',))

    @app.context_processor
    def view_helpers():
        def page_url(page):
            args = request.args.to_dict()
            args['page'] = page
            return url_for(request.endpoint, **(request.view_args or {}), **args)
        def report_url(kind='residents',**scope):
            args={k:v for k,v in request.args.items() if k in report_outputs.FILTER_KEYS|{'search','q'}}
            if args.get('q'):args['search']=args.pop('q')
            if scope.get('scope')=='resident':args={}
            args.update(scope);args['kind']=kind;args['return_to']=request.full_path.rstrip('?')
            if kind=='households':args.setdefault('mode','summary')
            if kind=='residents':args.setdefault('scope','all_matching')
            return url_for('report_builder',kind=kind,context=report_context.issue(args),return_to=request.full_path.rstrip('?'))
        from record_navigation import resident_url
        return dict(page_url=page_url,audit_actions=sorted(reporting.ACTIONS),report_url=report_url,resident_url=resident_url)

    @app.route('/health')
    def health():
        return jsonify(status='ok')

    def office_home():
        with database.transaction() as cursor:
            cursor.execute("""SELECT COUNT(*) FILTER(WHERE COALESCE(status,'Active')<>'Deceased') AS active,
                COUNT(*) FILTER(WHERE status='Deceased') AS deceased,
                COUNT(*) FILTER(WHERE gender='Male' AND COALESCE(status,'Active')<>'Deceased') AS male,
                COUNT(*) FILTER(WHERE gender='Female' AND COALESCE(status,'Active')<>'Deceased') AS female FROM household""")
            totals=cursor.fetchone()
            cursor.execute('SELECT COUNT(*) AS total FROM households')
            totals['households']=cursor.fetchone()['total']
            from recent_activity import summaries
            recent=summaries(cursor)
        return render_template('index.html',
            total_residents=totals['active'],active_residents=totals['active'],total_deceased=totals['deceased'],
            total_males=totals.get('male',0),total_females=totals.get('female',0),total_households=totals['households'],recent_activity=recent)
    route('/','home',office_home,('admin',))
    def profile():
        with database.transaction() as cursor:
            cursor.execute('SELECT username,email,signup_date FROM users WHERE id=%s',(g.identity['id'],))
            row=cursor.fetchone()
            cursor.execute("SELECT MAX(created_at) AS last_login FROM audit_logs WHERE user_id=%s AND action_type='LOGIN' AND status='SUCCESS'",(str(g.identity['id']),))
            last_login=(cursor.fetchone() or {}).get('last_login')
        from office_time import local_timestamp
        return render_template('profile.html',
            user_data=row,user_email=row.get('email'),join_date=row.get('signup_date') or 'Not recorded',
            joined_display=local_timestamp(row.get('signup_date')),last_login_display=local_timestamp(last_login))
    route('/profile','profile',profile,('admin',))

    import notifications,report_context
    route('/notifications','notifications',notifications.page,('admin',))
    route('/api/notifications','api_notifications',notifications.api,('admin',))
    route('/api/notifications/<int:event_id>/read','notification_read',notifications.mark,('admin',),('POST',))
    route('/notifications/open/<int:event_id>','notification_open',notifications.open_event,('admin',))
    route('/api/report-suggestions','report_suggestions',report_context.suggestions,('admin',))
    route('/api/report-years','report_years',report_context.years,('admin',))

    @app.route('/reports/builder',endpoint='report_builder')
    @app.route('/reports/options')
    @app.route('/print_reports')
    @require_role('admin')
    def print_reports():
        with database.transaction() as cursor:
            choices=record_routes.households(cursor)
            cursor.execute("SELECT username,created_at,new_value FROM audit_logs WHERE action_type='REPORT_GENERATE' ORDER BY created_at DESC,id DESC LIMIT 12")
            history=cursor.fetchall()
        for item in history:
            item.update(report_outputs.history_entry(item))
        from office_time import today
        initial=request.args.to_dict();locked={}
        if request.path=='/reports/builder':
            kind=initial.get('kind','residents')
            if not initial.get('context'):abort(400,description='Open Report Builder from the records page to preserve its scope.')
            verified=report_context.enforce(kind,{'context':initial['context']})
            locked={k:v for k,v in verified.items() if k in report_outputs.FILTER_KEYS|{'search'} and v}
            locked['kind']=kind
            initial=report_context.enforce(kind,initial)
        elif request.path=='/reports/options':
            if initial.get('kind','residents') not in report_outputs.COLUMNS:abort(400)
            initial.setdefault('kind','residents')
            if initial['kind']=='households':initial.setdefault('mode','summary')
            if initial['kind']=='residents':initial.setdefault('scope','all_matching')
            locked={k:v for k,v in initial.items() if k in report_outputs.FILTER_KEYS|{'kind','search'} and v}
            initial['context']=report_context.issue(locked)
        selected_resident=None
        if initial.get('scope')=='resident' and initial.get('resident_id'):
            try:selected_id=reporting.positive_id(initial['resident_id'])
            except ValueError:abort(400,description='Choose a valid resident.')
            with database.transaction() as cursor:
                cursor.execute("SELECT h.id,TRIM(CONCAT_WS(' ',h.surname,h.firstname,h.middlename)) AS full_name,hh.house_number FROM household h LEFT JOIN households hh ON hh.id=h.household_id WHERE h.id=%s",(selected_id,))
                selected_resident=cursor.fetchone()
            if not selected_resident:abort(404,description='Resident is no longer available. Return to the directory and review the current records.')
        return render_template('report_workspace.html' if request.path=='/reports/options' else 'print_reports.html',households=choices,current_year=today().year,report_columns=report_outputs.COLUMNS,required_columns={k:list(v) for k,v in report_outputs.REQUIRED.items()},default_columns=report_outputs.DEFAULTS,history=history,return_to=report_outputs.safe_return(initial.get('return_to','/view_members')),report_initial=initial,report_locked=locked,selected_resident=selected_resident)

    @app.route('/print_household_members/<int:household_id>')
    @require_role('admin')
    def print_household_members(household_id):
        from flask import redirect
        bounds=dict(kind='households',mode='members',household_id=str(household_id))
        return redirect(url_for('report_builder',kind='households',context=report_context.issue(bounds),return_to=url_for('view_household',household_id=household_id)))

    def search(kind):
        term=request.args.get('q','').strip()[:200]
        if not term:
            return jsonify([])
        rows,_,_=reporting.rows_for(kind,{'search':term},10)
        if kind=='residents':
            return jsonify([dict(id=r['id'], name=r['full_name'],household_name=r['household_name'],
                                 occupation=r['occupation'],type='resident') for r in rows])
        return jsonify([dict(id=r['id'],name=r['surname'],house_number=r['house_number'],
                             subtext=f"House {r['house_number']} | Members {r['member_count']}",type='household') for r in rows])
    route('/search_members','search_members',lambda:search('residents'),('admin',))
    route('/search_households','search_households',lambda:search('households'),('admin',))

    @app.route('/api/search_residents')
    @require_role('admin')
    def api_search_residents():
        term=request.args.get('q','').strip()[:200]
        if not term:return jsonify([])
        residents,_,_=reporting.rows_for('residents',{'search':term},10)
        households,_,_=reporting.rows_for('households',{'search':term},10)
        admin=g.identity['role']=='admin'
        results=[]
        for row in residents:
            results.append(dict(id=row['id'],name=row['full_name'],type='Resident',
                details='Household: '+(row.get('household_name') or 'Not recorded'),status=row.get('status') or 'Active',
                url=url_for('resident_detail',id=row['id']) if admin else
                    (url_for('user_view_household',household_id=row['household_id']) if row.get('household_id') else url_for('user_view_members'))))
        for row in households:
            results.append(dict(id=row['id'],name=row.get('surname'),type='Household',status='Read only',
                details=f"House {row.get('house_number') or 'Not recorded'} | Members {row.get('member_count',0)}",
                url=url_for('view_household' if admin else 'user_view_household',household_id=row['id'])))
        return jsonify(results)

    @app.errorhandler(Exception)
    def failure(exc):
        if isinstance(exc,HTTPException):
            status=exc.code
            message=exc.description
        else:
            status=500
            # Exception arguments/SQL parameters may contain private data. Never log them.
            app.logger.error('Request failed: %s at endpoint %s',type(exc).__name__,request.endpoint)
            message='The request could not be completed. Contact the administrator before retrying.'
        if request.path.startswith('/api/'):
            return jsonify(error=message),status
        return render_template('request_error.html',message=message,status=status),status

    return app
