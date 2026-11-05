"""Isolated fictional store: no database, provider, private files or seed import."""
import copy
from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
import re
from unittest.mock import Mock

import pytest
from flask import g

import household_roles as roles
from validation import resident_age, resident

ROOT=Path(__file__).resolve().parents[1]


class RoleStore:
    def __init__(self):
        self.enabled=True;self.rows=[];self.heads=[];self.relations={};self.audits=[]
        self.executed=[];self.fail_commit=False;self.savepoints={}
        self.homes={1:dict(id=1,surname='Example household',house_number='A-1',address='Fictional evaluation address'),
                    2:dict(id=2,surname='Another household',house_number='B-2',address='Fictional evaluation address')}
        self.members={n:dict(id=n,firstname='Fictional '+str(n),middlename='',surname='Different surname '+str(n),
            household_id=2 if n==4 else 1,birthdate=date(1945,5,7) if n==3 else date(2000,1,1),
            death_date=date(2021,2,21) if n==3 else None,status='Deceased' if n==3 else 'Active',
            age='75' if n==3 else '26',gender='Female',civil_status='Single',occupation=None,
            registration_date=None,status_recorded_at=None,created_at=None,
            mental_health_status='PRIVATE HEALTH SENTINEL',current_health_status=None) for n in range(1,5)}

    def snapshot(self):return copy.deepcopy((self.heads,self.relations,self.audits,self.members,self.homes))
    def restore(self,state):self.heads,self.relations,self.audits,self.members,self.homes=copy.deepcopy(state)
    def active(self,home):return next((h for h in self.heads if h['household_id']==home and h['ended_at'] is None),None)

    def execute(self,query,params=()):
        self.executed.append((query,params));self.rows=[]
        tag=re.search(r'/\* (\w+) \*/',query);tag=tag[1] if tag else None
        if query.startswith('SAVEPOINT '):self.savepoints[query.split()[-1]]=self.snapshot()
        elif query.startswith('ROLLBACK TO SAVEPOINT '):self.restore(self.savepoints[query.split()[-1]])
        elif tag=='roles_available':self.rows=[dict(enabled=self.enabled)]
        elif tag=='roles_current':
            head=self.active(params[0]);self.rows=[dict(head,**{k:v for k,v in self.members.get(head['resident_id'],{}).items() if k in {'firstname','middlename','surname','status'}})] if head else []
        elif tag=='roles_candidate':self.rows=[copy.deepcopy(self.members[params[0]])] if params[0] in self.members else []
        elif tag=='roles_end':
            for h in self.heads:
                if h['id']==params[0]:h['ended_at']='2026-11-04'
        elif tag=='roles_assign':
            head=dict(id=len(self.heads)+1,household_id=params[0],resident_id=params[2],resident_id_record=params[3],
                      assigned_at='2026-11-04',ended_at=None,reason=params[6])
            self.heads.append(head);self.rows=[copy.deepcopy(head)]
        elif tag=='roles_relationship_old':
            value=self.relations.get(tuple(params));self.rows=[dict(relationship=value)] if value else []
        elif tag=='roles_relationship_save':self.relations[params[:2]]=params[3]
        elif tag=='roles_relationship_clear':self.relations.pop(tuple(params),None)
        elif tag=='roles_relationships':self.rows=[dict(resident_id=i,relationship=v) for (a,i),v in self.relations.items() if a==params[0] and i in params[1]]
        elif tag=='roles_history':
            self.rows=[dict(copy.deepcopy(h),**{k:v for k,v in self.members.get(h['resident_id'],{}).items() if k in {'firstname','middlename','surname'}}) for h in reversed(self.heads) if h['household_id']==params[0]][:8]
        elif tag=='roles_relationship_history':self.rows=[dict(assignment_id=a,resident_id_record=i,relationship=v) for (a,i),v in self.relations.items() if a in params[0]]
        elif tag=='roles_choices':self.rows=[dict(h,name='Fictional head') for h in self.heads if h['ended_at'] is None]
        elif query.startswith('SELECT id FROM households WHERE id='):
            self.rows=[dict(id=params[0])] if params[0] in self.homes else []
        elif query.startswith('SELECT id FROM households WHERE LOWER'):
            self.rows=[dict(id=h['id']) for h in self.homes.values() if h['surname'].strip().lower()==params[0].lower() and h['house_number'].strip().lower()==params[1].lower() and h['id']!=params[2]]
        elif query.startswith('INSERT INTO households('):
            identifier=max(self.homes)+1;self.homes[identifier]=dict(id=identifier,surname=params[0],house_number=params[1],address=params[2]);self.rows=[dict(id=identifier)]
        elif query.startswith('UPDATE households SET '):
            self.homes[params[-1]].update(surname=params[0],house_number=params[1],address=params[2])
        elif query.startswith('SELECT * FROM households WHERE id=') or query.startswith('SELECT id,surname,house_number,address FROM households WHERE'):
            self.rows=[copy.deepcopy(self.homes[params[0]])] if params[0] in self.homes else []
        elif query.startswith('SELECT * FROM household WHERE id='):
            self.rows=[copy.deepcopy(self.members[params[0]])] if params[0] in self.members else []
        elif query.startswith('SELECT h.id'):
            self.rows=[copy.deepcopy(m) for m in self.members.values() if (m['id']==params[0] if 'WHERE h.id=' in query else m['household_id']==params[0])]
        elif query.startswith('SELECT id,firstname,middlename,surname FROM household'):
            self.rows=[copy.deepcopy(m) for m in self.members.values() if m['household_id']==params[0] and m['status']=='Active']
        elif query.startswith('SELECT COUNT(*) AS total FROM household WHERE'):
            self.rows=[dict(total=sum(m['household_id']==params[0] for m in self.members.values()))]
        elif query.startswith('SELECT id,surname,house_number,address FROM households ORDER'):
            self.rows=list(copy.deepcopy(self.homes).values())
        elif query.startswith('INSERT INTO household ('):
            names=query.split('(',1)[1].split(')',1)[0].split(',');identifier=max(self.members)+1
            self.members[identifier]=dict(zip(names,(*params,'2026-11-04','2026-11-04')),id=identifier);self.rows=[dict(id=identifier)]
        elif query.startswith('UPDATE household SET '):
            names=query.split(' SET ')[1].split(',status_recorded_at')[0].split(',')
            self.members[params[-1]].update(dict(zip([c.split('=')[0] for c in names],params)))
        elif query.startswith('DELETE FROM household WHERE id='):self.members.pop(params[0],None)
        elif query.startswith('INSERT INTO audit_logs'):self.audits.append(params)

    def fetchone(self):return self.rows[0] if self.rows else None
    def fetchall(self):return self.rows


@pytest.fixture
def role_store(monkeypatch):
    store=RoleStore()
    @contextmanager
    def transaction():
        state=store.snapshot()
        try:
            yield store
            if store.fail_commit:raise RuntimeError('Synthetic commit failure')
        except BaseException:store.restore(state);raise
    monkeypatch.setattr('record_routes.transaction',transaction)
    monkeypatch.setattr('directory_routes.transaction',transaction)
    return store


def designate(client,csrf,store,identifier='1',previous='none',reason='Owner explicitly designated head'):
    return client.post('/households/1/head',data=dict(head_resident_id=identifier,head_assignment=previous,head_reason=reason),headers=csrf)


def test_explicit_designation_preserves_existing_people_and_accounts(client,csrf,role_store):
    before=copy.deepcopy(role_store.members)
    assert designate(client,csrf,role_store).status_code==302
    assert role_store.active(1)['resident_id']==1 and role_store.members==before
    assert len(role_store.audits)==1 and role_store.audits[0][-1]=='SUCCESS'
    writes=[q for q,p in role_store.executed if q.lstrip().startswith(('UPDATE','INSERT','DELETE'))]
    assert not any(re.search(r'\b(users|password_resets|households|household)\b',q) for q in writes)


@pytest.mark.parametrize('identifier',['3','4','999','0','-1','malformed'])
def test_deceased_foreign_missing_and_invalid_candidates_fail_without_assignment(client,csrf,role_store,identifier):
    before=copy.deepcopy(role_store.members)
    assert designate(client,csrf,role_store,identifier).status_code==302
    assert not role_store.heads and role_store.members==before
    assert role_store.audits[-1][-1]=='FAILED'


@pytest.mark.parametrize('reason',['','ab','x'*301])
def test_reason_validation_is_server_side(client,csrf,role_store,reason):
    designate(client,csrf,role_store,reason=reason)
    assert not role_store.heads and role_store.audits[-1][-1]=='FAILED'


def test_reassignment_retains_original_decision_and_does_not_copy_relationships(client,csrf,role_store):
    designate(client,csrf,role_store)
    role_store.relations[(1,2)]='Spouse'
    designate(client,csrf,role_store,'2','1','Explicit change of household head')
    assert len(role_store.heads)==2 and role_store.heads[0]['ended_at'] is not None
    assert role_store.active(1)['resident_id']==2 and role_store.relations[(1,2)]=='Spouse'
    html=client.get('/view_household/1').text
    assert 'Designation history' in html and 'Spouse' in html
    current_members=[copy.deepcopy(m) for m in role_store.members.values() if m['household_id']==1]
    roles.context(role_store,1,current_members)
    assert all(m.get('relationship_to_head')!='Spouse' for m in current_members)
    assert 'PRIVATE HEALTH SENTINEL' not in html


def test_stale_decision_cannot_replace_a_more_recent_head(client,csrf,role_store):
    designate(client,csrf,role_store)
    designate(client,csrf,role_store,'2','none')
    assert len(role_store.heads)==1 and role_store.active(1)['resident_id']==1
    assert role_store.audits[-1][-1]=='FAILED'


def test_deceased_head_is_retained_until_explicit_reassignment(client,csrf,role_store):
    designate(client,csrf,role_store)
    role_store.members[1].update(status='Deceased',death_date=date(2020,1,1))
    html=client.get('/view_household/1').text
    assert 'Deceased — reassignment needed' in html and role_store.active(1)['resident_id']==1
    designate(client,csrf,role_store,'2','1','Previous head is deceased')
    assert role_store.members[1]['status']=='Deceased' and role_store.heads[0]['ended_at'] is not None


def test_clear_head_preserves_history_and_relationships(client,csrf,role_store):
    designate(client,csrf,role_store);role_store.relations[(1,2)]='Sibling'
    designate(client,csrf,role_store,'','1','No replacement confirmed yet')
    assert role_store.active(1) is None and role_store.heads[0]['ended_at'] is not None
    assert role_store.relations[(1,2)]=='Sibling'


def test_missing_optional_schema_preserves_existing_views_and_blocks_new_writes(client,csrf,role_store):
    role_store.enabled=False
    assert client.get('/view_household/1').status_code==200
    assert 'id="headAssignment"' not in client.get('/view_household/1').text
    assert designate(client,csrf,role_store).status_code==409
    assert not role_store.heads


def test_new_head_route_requires_post_csrf_and_live_administrator(client,csrf,identity,role_store):
    assert client.get('/households/1/head').status_code==405
    assert client.post('/households/1/head',data={}).status_code==400
    identity['role']='user'
    with client.session_transaction() as session:session['role']='user'
    assert designate(client,csrf,role_store).status_code==302
    assert not role_store.heads


def test_head_transfer_and_deletion_require_controlled_reassignment(client,csrf,role_store):
    designate(client,csrf,role_store)
    assert client.post('/delete_member/1',headers=csrf).status_code==409
    data=dict(firstname='Fictional',surname='Member',household_id='2',status='Active',gender='Female',civil_status='Single')
    response=client.post('/edit_member/1',data=data,headers=csrf)
    assert response.status_code==200 and 'before transferring' in response.text
    assert role_store.members[1]['household_id']==1


def test_explicit_member_relationship_uses_current_assignment(app,identity,role_store):
    with app.test_request_context('/'):
        g.identity=identity
        roles.assign(role_store,1,1,'none','Administrator designation')
        roles.save_member(role_store,2,1,'Active',dict(household_roles_present='yes',head_assignment='1',relationship_to_head='Non-relative'))
        assert role_store.relations[(1,2)]=='Non-relative'
        members=[copy.deepcopy(role_store.members[1]),copy.deepcopy(role_store.members[2])]
        roles.context(role_store,1,members)
        assert [m['relationship_to_head'] for m in members]==['Head','Non-relative']
        roles.save_member(role_store,2,1,'Active',dict(household_roles_present='yes',head_assignment='1',relationship_to_head=''))
        assert (1,2) not in role_store.relations


@pytest.mark.parametrize('changes',[dict(head_assignment='none'),dict(relationship_to_head='Head'),
    dict(designate_head='yes',relationship_to_head='Spouse'),dict(relationship_to_head='x'*81)])
def test_invalid_or_conflicting_relationships_are_refused(app,identity,role_store,changes):
    with app.test_request_context('/'):
        g.identity=identity;roles.assign(role_store,1,1,'none','Administrator designation')
        form=dict(household_roles_present='yes',head_assignment='1');form.update(changes)
        with pytest.raises(ValueError):roles.save_member(role_store,2,1,'Active',form)
        assert not role_store.relations and len(role_store.heads)==1


def test_late_relationship_error_rolls_back_resident_insert_but_records_actual_failure(client,csrf,role_store):
    before=copy.deepcopy(role_store.members)
    response=client.post('/add_member',data=dict(firstname='Fictional',surname='New',household_id='1',
        gender='Female',civil_status='Single',status='Active',household_roles_present='yes',
        head_assignment='none',relationship_to_head='Sibling'),headers={**csrf,'Accept':'application/json'})
    assert response.status_code==422 and not response.json['ok']
    assert role_store.members==before and role_store.audits[-1][-1]=='FAILED'
    with client.session_transaction() as session:assert not any(c=='resident_registered' for c,m in session.get('_flashes',[]))


def test_commit_failure_cannot_leave_update_success_feedback(client,csrf,role_store):
    role_store.fail_commit=True
    response=client.post('/edit_member/2',data=dict(firstname='Fictional',surname='Changed',household_id='1',gender='Female',civil_status='Single',status='Active'),headers=csrf)
    assert response.status_code==500 and role_store.members[2]['surname']=='Different surname 2'
    with client.session_transaction() as session:assert not any(c=='success' for c,m in session.get('_flashes',[]))


def test_compact_household_keeps_actions_and_omits_secondary_health_columns(client,role_store):
    html=client.get('/view_household/1').text
    for value in ['Add Member','Edit Household','Print / Download','Relationship to head','View Details','head_assignment']:
        assert value in html
    for value in ['<th>Occupation</th>','<th>Birthdate</th>','Mental Health Status','PRIVATE HEALTH SENTINEL']:
        assert value not in html
    assert not any('mental_health_status' in q for q,p in role_store.executed)
    detail=client.get('/resident/3').text
    assert 'PRIVATE HEALTH SENTINEL' in detail and 'At death' in html
    assert 'age at death' in detail.lower()


@pytest.mark.parametrize('status,death,expected',[('Active',None,81),('Deceased','2021-02-21',75),('Deceased',None,None)])
def test_age_uses_known_death_date_and_never_guesses(status,death,expected):
    assert resident_age(dict(birthdate='1945-05-07',status=status,death_date=death),date(2026,11,4))==expected


def test_resident_validation_ignores_submitted_age_and_computes_age_at_death():
    data=resident(dict(firstname='Fictional',surname='Member',household_id='1',status='Deceased',birthdate='1945-05-07',death_date='2021-02-21',age='999'))
    assert data['age']=='75'
    assert resident_age(dict(status='Deceased',birthdate=None,death_date='2021-02-21')) is None


def test_combined_filters_share_age_semantics_with_reports():
    from reporting import report_query
    query,params,order,basis=report_query('residents',dict(status='Deceased',gender='Female',age_min='60',age_max='90',household_id='1',civil_status='Widowed',search='Fictional'))
    assert "CASE WHEN status='Deceased' THEN death_date ELSE %s::date END" in query
    assert all(term in query for term in ['gender=%s','status=%s','civil_status=%s','household_id=%s'])
    assert order=='surname,firstname,id' and 'Fictional' not in query and 60 in params and 90 in params


def test_additive_migration_is_separate_and_never_changes_original_rows():
    up=(ROOT/'migrations/optional/007_household_roles.up.sql').read_text()
    down=(ROOT/'migrations/optional/007_household_roles.down.sql').read_text()
    assert 'household_head_current' in up and 'WHERE ended_at IS NULL' in up
    assert 'ON DELETE SET NULL' in up and 'resident_id_record' in up
    assert not re.search(r'^\s*(UPDATE|INSERT|DELETE|DROP|TRUNCATE)\b',up,re.M|re.I)
    assert 'UNIQUE(id,household_id)' in up and up.count('FOREIGN KEY(resident_id,household_id)')==2
    assert down.index('IF EXISTS')<down.index('DROP TABLE') and 'Rollback refused' in down
    assert 'CREATE TABLE public.household_member_relationships' in up


def test_feedback_script_uses_native_focus_dialog_and_never_evaluates_server_html():
    script=(ROOT/'static/js/defense-refinement.js').read_text()
    assert 'showModal()' in script and "box.addEventListener('close'" in script
    assert 'innerHTML' not in script and 'response.status===401' in script
    assert 'event.preventDefault();event.stopImmediatePropagation()' in script and 'form.requestSubmit' in script


def test_registration_can_designate_first_head_atomically(client,csrf,role_store):
    response=client.post('/add_member',data=dict(firstname='Fictional',surname='Unrelated',household_id='1',
        gender='Female',civil_status='Single',status='Active',household_roles_present='yes',
        head_assignment='none',designate_head='yes',head_reason='First explicit designation'),headers=csrf)
    assert response.status_code==302
    assert role_store.active(1)['resident_id']==5 and role_store.members[5]['surname']=='Unrelated'
    assert not any(q.startswith('UPDATE users') for q,p in role_store.executed)


def test_household_creation_needs_no_existing_resident_and_does_not_guess_a_head(client,csrf,role_store):
    before=copy.deepcopy(role_store.members)
    response=client.post('/add_household',data=dict(surname='New fictional home',house_number='C-3',address='Fictional address'),headers=csrf)
    assert response.status_code==302 and response.location.endswith('/view_household/3')
    assert role_store.homes[3]['surname']=='New fictional home' and role_store.members==before
    assert role_store.active(3) is None and role_store.audits[-1][-1]=='SUCCESS'


def test_duplicate_household_returns_failure_and_preserves_existing_data(client,csrf,role_store):
    before=copy.deepcopy(role_store.homes)
    response=client.post('/add_household',data=dict(surname='Example household',house_number='A-1',address='New fictional address'),headers={**csrf,'Accept':'application/json'})
    assert response.status_code==422 and response.json['ok'] is False
    assert role_store.homes==before and role_store.audits[-1][-1]=='FAILED'


def test_household_edit_keeps_members_and_head_unchanged(client,csrf,role_store):
    designate(client,csrf,role_store);before=copy.deepcopy(role_store.members)
    response=client.post('/edit_household/1',data=dict(surname='Updated fictional household',house_number='A-1',address='Changed fictional address'),headers=csrf)
    assert response.status_code==302 and role_store.members==before
    assert role_store.active(1)['resident_id']==1


def test_directory_filter_controls_are_server_rendered_and_preserve_active_values(client,monkeypatch,role_store):
    row=copy.deepcopy(role_store.members[2]);row.update(full_name='Fictional member',household_name='Example household',household_number='A-1')
    monkeypatch.setattr('directory_routes.rows_for',lambda *a,**k:([row],1,'Test basis'))
    # Counts/household options are separate queries; render no health projection.
    original=role_store.execute
    def execute(query,params=()):
        original(query,params)
        if query.startswith('SELECT COUNT(*) FILTER'):role_store.rows=[dict(active=1,deceased=0)]
        elif query.startswith('SELECT id,surname,house_number FROM households'):role_store.rows=list(role_store.homes.values())
    role_store.execute=execute
    html=client.get('/view_members?status=Active&gender=Female&age_min=20&age_max=40&household_id=1&civil_status=Single&search=Fictional').text
    assert 'Resident directory search and filters' in html and '1 matching' in html
    for name in ['status','gender']:
        assert 'name="'+name+'"' in html
    for name in ['age_min','age_max','household_id','civil_status']:
        toolbar=html.split('aria-label="Resident directory search and filters"',1)[1].split('</form>',1)[0]
        assert 'name="'+name+'"' not in toolbar
    assert '>Clear</a>' in html
    assert 'PRIVATE HEALTH SENTINEL' not in html and 'data-label' not in html  # Added progressively by JS.
    assert not any('mental_health_status' in q for q,p in role_store.executed)


def test_out_of_range_page_redirects_without_losing_combined_filters(client,monkeypatch):
    monkeypatch.setattr('directory_routes.rows_for',lambda *a,**k:([],121,'Test basis'))
    response=client.get('/view_members?page=99&gender=Female&status=Active&age_min=20')
    assert response.status_code==302
    from urllib.parse import urlsplit,parse_qs
    assert parse_qs(urlsplit(response.location).query)==dict(page=['3'],gender=['Female'],status=['Active'],age_min=['20'])


def test_not_recorded_filters_include_legacy_null_without_rewriting_rows():
    from reporting import report_query
    query,params,*_=report_query('residents',dict(gender='Not recorded',civil_status='Not recorded'))
    assert "COALESCE(gender,'Not recorded')=%s" in query
    assert "COALESCE(civil_status,'Not recorded')=%s" in query
    assert params==['Not recorded','Not recorded']


def test_preview_print_and_word_use_the_same_filters_and_export_all_matches(client,monkeypatch):
    from io import BytesIO
    from docx import Document
    calls=[]
    def rows(kind,args,limit=None,offset=0,**kwargs):
        calls.append((kind,dict(args),limit))
        result=[dict(id=i,full_name=f'Fictional Export {i:03}',status='Active',gender='Female') for i in range(1,126)]
        return result[:limit] if limit else result,125,'Synthetic test basis'
    monkeypatch.setattr('reporting.rows_for',rows)
    record=Mock();monkeypatch.setattr('report_outputs.record_generation',record)
    filters='?columns=id,full_name&status=Active&gender=Female&age_min=18&civil_status=Single'
    preview=client.get('/api/preview/residents'+filters)
    assert preview.status_code==200 and preview.json['total']==125 and len(preview.json['items'])==100
    printed=client.get('/reports/print/residents'+filters)
    assert printed.status_code==200 and 'Fictional Export 125' in printed.text
    word=client.get('/print_all_members'+filters)
    assert word.status_code==200
    document=Document(BytesIO(word.data))
    assert 'Fictional Export 125' in '\n'.join(c.text for table in document.tables for row in table.rows for c in row.cells)
    assert [c[2] for c in calls]==[100,None,None]
    for kind,args,limit in calls:
        assert args['status']=='Active' and args['gender']=='Female' and args['age_min']=='18' and args['civil_status']=='Single'
    assert record.call_count==2 and all(call.args[0]['total']==125 for call in record.call_args_list)


def test_browser_age_calculation_matches_backend_for_deceased_and_unknown_dates():
    import subprocess
    source=(ROOT/'static/js/ui_bridge.js').read_text()
    function=source[source.index('function updateAge(){'):source.index('for(const field of [birth,document.querySelector')]
    runner="""const vm=require('vm'); const code=JSON.parse(process.argv[1]);
    for(const deathValue of ['2021-02-21','']) {
      const birth={value:'1945-05-07',validity:{valid:true}},age={value:''};
      const status={value:'Deceased'},death={value:deathValue,validity:{valid:true}};
      const document={querySelector:s=>s.includes('status')?status:death};
      vm.runInNewContext(code+';updateAge();',{birth,age,document,Intl,Date});
      if(age.value!==(deathValue?75:''))throw Error('Age mismatch');
    }"""
    result=subprocess.run(['node','-e',runner,json.dumps(function)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_unavailable_head_can_be_explicitly_cleared_without_erasing_history(client,csrf,role_store):
    designate(client,csrf,role_store)
    role_store.heads[0]['resident_id']=None
    html=client.get('/view_household/1').text
    assert 'Resident no longer available' in html
    response=designate(client,csrf,role_store,'','1','Explicitly clear unavailable head')
    assert response.status_code==302 and role_store.active(1) is None
    assert role_store.heads[0]['resident_id_record']==1
    assert role_store.heads[0]['ended_at'] is not None
    assert role_store.audits[-1][-1]=='SUCCESS'


def test_household_detail_out_of_range_page_keeps_selected_page_size(client,role_store):
    response=client.get('/view_household/1?page=99&page_size=25')
    assert response.status_code==302
    from urllib.parse import urlsplit,parse_qs
    assert urlsplit(response.location).path=='/view_household/1'
    assert parse_qs(urlsplit(response.location).query)==dict(page=['1'],page_size=['25'])


def test_optional_rollback_locks_before_checking_for_preserved_decisions():
    source=(ROOT/'migrations/optional/007_household_roles.down.sql').read_text()
    assert source.index('LOCK TABLE ')<source.index('DO $guard$')<source.index('DROP TABLE ')
    assert 'IN ACCESS EXCLUSIVE MODE' in source
