"""Focused regression checks for report profiles, year controls and PHT periods."""
from contextlib import contextmanager
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from flask import g, render_template

import report_outputs
import reporting


@pytest.mark.parametrize(('choice','extra','expected'),[
    ('today',{},date(2026,11,5)),
    ('this_month',{},date(2026,11,1)),
    ('last_month',{},date(2026,10,1)),
    ('specific_month',{'audit_month':'2024-02'},date(2024,2,1)),
    ('specific_year',{'audit_year':'2023'},date(2023,1,1)),
])
def test_audit_periods_use_pht_calendar_boundaries(monkeypatch,choice,extra,expected):
    monkeypatch.setattr(reporting,'office_today',lambda:date(2026,11,5))
    clauses,values=reporting.period({'audit_period':choice,**extra},"(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila')",allow_time=True)
    assert clauses==["(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila')>=%s",
                     "(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila')<(%s::date + INTERVAL '1 day')"]
    assert values[0]==expected


@pytest.mark.parametrize('args',[{'year':'26'},{'year':'20x6'},{'year':'2201'}])
def test_report_year_rejects_non_four_digit_or_out_of_range_values(args):
    with pytest.raises(ValueError):reporting.period(args,'registration_date')


def test_household_analytics_filters_share_query_scope():
    query,params,_,_=reporting.report_query('households',{
        'search':'Santos 12','household_size':'3-4','composition':'active','year':'2026'})
    assert 'member_count>=%s' in query and 'member_count<=%s' in query and 'active_count>0' in query
    assert params==['%Santos%','%12%',3,4,2026]


def _cursor(enabled=False,household=None):
    class Cursor:
        def execute(self,query,params=()):self.query=query
        def fetchone(self):
            if 'FROM households WHERE id=' in self.query:return household
            return {'enabled':enabled}
        def fetchall(self):return []
    @contextmanager
    def transaction():yield Cursor()
    return transaction


def _doc_text(stream):
    doc=Document(BytesIO(stream.getvalue()))
    return '\n'.join([p.text for p in doc.paragraphs]+[cell.text for table in doc.tables for row in table.rows for cell in row.cells])


def test_individual_resident_profile_is_a_single_record_information_sheet(app,monkeypatch):
    row=dict(id=41,full_name='Fictional Resident',birthdate='2000-01-02',age=26,gender='Female',
        civil_status='Single',occupation='Teacher',status='Active',household_name='Example',household_number='B-4',
        household_address='Fictional address',registration_date='2026-01-02',death_date=None,household_id=3)
    monkeypatch.setattr(reporting,'rows_for',lambda *args,**kwargs:([dict(row)],1,'Registration date'))
    monkeypatch.setattr(report_outputs,'transaction',_cursor())
    with app.test_request_context('/reports/print/residents'):
        g.identity={'id':1,'username':'test-admin','role':'admin','status':'approved'}
        data=report_outputs.prepare('residents',{'scope':'resident','resident_id':'41'})
        doc=_doc_text(report_outputs.document(data))
        html=render_template('report_print.html',**data)
    assert data['total']==1 and data['title']=='Individual Resident Profile'
    assert 'Fictional Resident' in doc and 'Resident ID' in doc and 'Fictional address' in doc
    assert 'Fictional Resident' in html and 'Fictional address' in html and '<table' not in html
    assert 'Mental Health Status' not in doc and 'Current Health Status' not in doc


def test_household_profile_print_and_word_include_selected_home_and_members(app,monkeypatch):
    household=dict(id=7,surname='Example Family',house_number='A-7',address='Fictional road',created_at='2026-03-01')
    members=[dict(id=71,full_name='Fictional Member One',status='Active',relationship_to_head=None)]
    def rows(kind,args,limit=None,offset=0,**kwargs):
        return ([dict(household,member_count=1,active_count=1,deceased_count=0)] if kind=='households' else members),1,'Registered date'
    monkeypatch.setattr(reporting,'rows_for',rows)
    monkeypatch.setattr(report_outputs,'transaction',_cursor(household=household))
    with app.test_request_context('/reports/print/households'):
        g.identity={'id':1,'username':'test-admin','role':'admin','status':'approved'}
        data=report_outputs.prepare('households',{'mode':'profile','household_id':'7'})
        doc=_doc_text(report_outputs.document(data))
        html=render_template('report_print.html',**data)
    assert data['title']=='Household Profile' and data['total']==1
    for text in ['Example Family','A-7','Fictional road','Fictional Member One','Not designated']:
        assert text in doc and text in html
    assert 'household_id=7' not in data['summary']


def test_report_builder_removes_age_and_empty_filters_and_uses_profile_types(client,monkeypatch):
    class Cursor:
        def execute(self,*args):pass
        def fetchall(self):return []
    @contextmanager
    def fake():yield Cursor()
    monkeypatch.setattr('webapp.database.transaction',fake)
    html=client.get('/print_reports').get_data(as_text=True)
    assert 'Individual Resident Profile' in html and 'Household Profile' in html
    assert 'name="age_min"' not in html and 'name="age_max"' not in html
    assert 'name="empty"' not in html and 'Actor (exact)' not in html


def test_branding_uses_shared_favicon_and_resident_roles_are_radio_controls(client):
    with client.session_transaction() as session:session.clear()
    for path in ['/login','/forgot-password','/reset-password/fictional-token']:
        response=client.get(path)
        if response.status_code==200:
            html=response.get_data(as_text=True)
            assert 'favicon.svg' in html
            assert '>BIS<' not in html
    role_template=(Path(__file__).resolve().parents[1]/'templates'/'household_role_fields.html').read_text(encoding='utf-8')
    assert 'type="radio" name="head_role" value="member"' in role_template
    assert 'type="radio" name="head_role" value="head"' in role_template


def test_household_analytics_restores_previous_filters_and_year_suggestions():
    source=(Path(__file__).resolve().parents[1]/'templates'/'analytics.html').read_text(encoding='utf-8')
    for control in ['filterHouseholdSize','filterHouseholdOccupancy','filterHouseholdYear','filterHouseholdBasis']:
        assert f'id="{control}"' in source
    for removed in ['filterHouseholdSearch','filterHouseholdMonth','filterHeadStatus','filterComposition','householdLimit']:
        assert removed not in source
    assert 'Registration year' in source and 'householdYears.map(value=>new Option(value,value))' in source
    assert '<datalist id="residentYearSuggestions">' in source
    assert 'id="householdChartScope" hidden' not in source
    assert "document.getElementById('householdOrientation')" not in source
    assert 'i.parsed.x' in source


def test_resident_role_and_edit_form_styles_support_dark_mode():
    css=(Path(__file__).resolve().parents[1]/'static'/'css'/'admin-form-controls.css').read_text(encoding='utf-8')
    assert 'html[data-theme=dark] body.admin-workspace .resident-editor' in css
    assert 'resident-role-options label:has(input:checked)' in css
    assert 'resident-role-options input[type=radio]:focus-visible' in css
    assert 'resident-role-options label:has(input:disabled)' in css


def test_application_name_and_audit_reset_alignment_are_consistent():
    base=Path(__file__).resolve().parents[1]
    name='Barangay Household Information Management System'
    for rel in ['templates/base.html','templates/login.html','templates/system_head.html',
                'templates/user_base.html','auth_utils.py','email_config.py']:
        source=(base/rel).read_text(encoding='utf-8')
        assert name in source and 'Barangay Information System' not in source
    for rel in ['templates/user_base.html','static/css/workflow-polish.css','static/css/resident-portal.css','static/css/login-lovable.css']:
        assert 'overflow-wrap' in (base/rel).read_text(encoding='utf-8')
    workspace=(base/'templates'/'report_workspace.html').read_text(encoding='utf-8')
    style=(base/'static'/'css'/'report-builder.css').read_text(encoding='utf-8')
    script=(base/'static'/'js'/'report-center.js').read_text(encoding='utf-8')
    assert '<div class="builder-filter-actions"><button' in workspace
    assert '.builder-filter-actions #reportReset' in style
    assert "byId('reportReset').addEventListener('click',()=>{stale();initialize();" in script


def test_head_reason_default_matches_existing_schema_constraint():
    base=Path(__file__).resolve().parents[1]
    migration=(base/'migrations'/'optional'/'007_household_roles.up.sql').read_text(encoding='utf-8')
    roles_source=(base/'household_roles.py').read_text(encoding='utf-8')
    assert 'reason VARCHAR(300) NOT NULL CHECK (length(trim(reason)) BETWEEN 3 AND 300)' in migration
    assert "or 'Administrative designation'" in roles_source
