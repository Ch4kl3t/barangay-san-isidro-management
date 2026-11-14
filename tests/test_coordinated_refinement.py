"""Synthetic household eligibility, ordering and presentation regressions."""
import copy
import subprocess
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
import pytest

from tests.test_defense_refinement import role_store
from tests.test_ui_simplification import dashboard
from tests.test_profile_alignment import Tree,nodes

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('occupied',[True,False])
def test_directory_and_details_share_deletion_eligibility(client,monkeypatch,role_store,occupied):
    if not occupied:
        role_store.members={key:value for key,value in role_store.members.items() if value['household_id']!=1}
    count=sum(m['household_id']==1 for m in role_store.members.values())
    home=dict(role_store.homes[1],member_count=count)
    monkeypatch.setattr('directory_routes.rows_for',lambda *a,**k:([home],1,'Households'))
    for path in ['/view_households','/view_household/1']:
        response=client.get(path);assert response.status_code==200
        tree=Tree();tree.feed(response.text);all_nodes=list(nodes(tree.root))
        controls=[n for n in all_nodes if n['tag']=='button' and 'delete-btn' in n['attrs'].get('class','').split()]
        assert len(controls)==1
        control=controls[0]
        if occupied:
            assert 'disabled' in control['attrs'] and 'data-delete-household' not in control['attrs']
            wrapper=control['parent'];assert wrapper['attrs']['tabindex']=='0'
            assert wrapper['attrs'].get('aria-describedby')
            assert any(n['attrs'].get('role')=='tooltip' for n in nodes(wrapper))
            assert 'Move or remove all residents before deleting this household.' in response.text
        else:
            assert 'disabled' not in control['attrs']
            assert control['attrs']['data-delete-url']=='/delete_household/1'
        form=next(n for n in all_nodes if n['attrs'].get('id')=='deleteHouseholdForm')
        assert form['attrs']['method']=='POST'
        assert any(n['attrs'].get('name')=='csrf_token' for n in nodes(form))
        assert sum(n['attrs'].get('id')=='householdDeleteDialog' for n in all_nodes)==1


def test_stale_empty_ui_cannot_delete_newly_occupied_household(client,csrf,role_store):
    # A stale UI's enabled action must not determine eligibility at submission.
    before=copy.deepcopy(role_store.members)
    response=client.post('/delete_household/1',headers=csrf)
    assert response.status_code==302 and role_store.members==before and 1 in role_store.homes
    assert role_store.audits[-1][-1]=='DENIED'
    queries=[q for q,p in role_store.executed]
    parent=next(i for i,q in enumerate(queries) if q.startswith('SELECT * FROM households WHERE id='))
    children=next(i for i,q in enumerate(queries) if q.startswith('SELECT h.id') and 'FOR UPDATE' in q)
    assert 'FOR UPDATE' in queries[parent] and parent<children
    assert not any(q.startswith('DELETE FROM ') for q in queries)


def test_delete_household_rejects_csrf_invalid_id_and_nonadministrator(client,csrf,role_store,identity):
    assert client.get('/delete_household/1').status_code==405
    assert client.post('/delete_household/1').status_code==400
    assert client.post('/delete_household/999',headers=csrf).status_code==404
    identity['role']='user'
    assert client.post('/delete_household/1',headers=csrf).status_code==302
    assert role_store.members and role_store.homes


def test_empty_delete_commit_failure_rolls_back(client,csrf,role_store):
    role_store.members.pop(4);before=role_store.snapshot();role_store.fail_commit=True
    assert client.post('/delete_household/2',headers=csrf).status_code==500
    assert role_store.snapshot()==before
    with client.session_transaction() as state:
        assert not any(message=='Empty household deleted.' for category,message in state.get('_flashes',[]))


@pytest.mark.parametrize('order',['asc','desc'])
@pytest.mark.parametrize('page',[1,2,3])
def test_full_filtered_household_names_sorted_before_paging(app,client,dashboard,order,page):
    for i,home in enumerate(dashboard.homes):
        home['surname']=['Zulu','alpha','ALPHA','Bravo','Echo'][i%5]
    expected=sorted(dashboard.homes,key=lambda h:h['id'])
    expected.sort(key=lambda h:h['surname'].casefold(),reverse=order=='desc')
    data=client.get('/api/dashboard',query_string=dict(household_sort=order,households_page=page,household_size='2-4')).json
    assert [h['id'] for h in data['households']]==[h['id'] for h in expected[(page-1)*10:page*10]]
    assert data['pagination']['households']['total']==30
    assert data['stats']['total']==125
    from record_navigation import serializer
    with app.app_context():
        for home in data['households']:
            token=parse_qs(urlsplit(home['detail_url']).query)['nav'][0]
            destination=serializer().loads(token)['return_to']
            assert parse_qs(urlsplit(destination).query)['filterHouseholdSort']==[order]


def test_invalid_sort_never_reaches_database(client,dashboard):
    assert client.get('/api/dashboard?household_sort=unsafe').status_code==400
    assert not dashboard.executed


def test_compact_form_actions_and_recovery_copy(client):
    appearance=(ROOT/'static/css/appearance.css').read_text(encoding='utf-8')
    assert 'flex:1 1 180px' not in appearance
    assert '.form-actions{display:flex;flex-direction:row;' in appearance
    for filename in ['add_household.html','add_member.html','edit_member.html']:
        source=(ROOT/'templates'/filename).read_text(encoding='utf-8')
        rule=source.split('.btn-submit {',1)[1].split('}',1)[0]
        assert 'width: auto' in rule and 'min-height: 44px' in rule
    response=client.get('/forgot-password')
    assert response.status_code==200 and 'APP_BASE_URL' not in response.text
    assert 'Reset links expire after 1 hour' in response.text
    assert 'name="csrf_token"' in response.text


def test_real_household_delete_script_requires_confirmation_and_blocks_duplicates():
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const clicks={},windowEvents={},formEvents={},dialogEvents={};let focus=0;
const cancel={focus(){},addEventListener:(name,fn)=>clicks.cancel=fn};
const submit={disabled:false,textContent:'Delete Household'};
const form={dataset:{},querySelector:()=>submit,addEventListener:(name,fn)=>formEvents[name]=fn};
const message={textContent:''};
const dialog={open:false,showModal(){this.open=true;},close(){this.open=false;dialogEvents.close();},querySelector:()=>cancel,addEventListener:(name,fn)=>dialogEvents[name]=fn};
const document={getElementById:id=>({householdDeleteDialog:dialog,deleteHouseholdForm:form,householdDeleteMessage:message}[id]),addEventListener:(name,fn)=>clicks[name]=fn};
const window={addEventListener:(name,fn)=>windowEvents[name]=fn};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window,URL,location:{href:'https://example.test/view_households',origin:'https://example.test'}});
const button={disabled:false,dataset:{deleteUrl:'/delete_household/7',householdName:'Synthetic'},focus(){focus++;}};
function click(b){clicks.click({target:{closest:()=>b},preventDefault(){}});}
click({...button,disabled:true});assert.equal(dialog.open,false);
click(button);assert.equal(dialog.open,true);assert.equal(form.action,'https://example.test/delete_household/7');assert.equal(form.dataset.submitting,undefined);
clicks.cancel();assert.equal(dialog.open,false);assert.equal(focus,1);assert.equal(form.dataset.submitting,undefined);
click(button);let prevented=0;formEvents.submit({preventDefault(){prevented++;}});assert.equal(submit.disabled,true);assert.equal(prevented,0);
formEvents.submit({preventDefault(){prevented++;}});assert.equal(prevented,1);
windowEvents.pageshow();assert.equal(submit.disabled,false);assert.equal(dialog.open,false);
'''
    result=subprocess.run(['node','-e',script,str(ROOT/'static/js/household-delete.js')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_table_renderer_preserves_sorted_api_page_with_numeric_ids():
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8'),tbody={innerHTML:''};
const build=source.match(/function buildHouseholdMap\([\s\S]*?\n}/)[0];
const render=source.match(/function renderHouseholdTable\([\s\S]*?\n}/)[0];
const context={document:{getElementById:()=>tbody},dashData:{households:[
 {id:30,surname:'Zulu'}, {id:21,surname:'Echo'}, {id:1,surname:'Alpha'}
],pagination:{households:{page:1}}},analyticsRecordLink:value=>value,uiEscape:value=>String(value),fmtDate:()=>''};
vm.runInNewContext(build+'\n'+render+'\nrenderHouseholdTable();',context);
assert(tbody.innerHTML.indexOf('Zulu')<tbody.innerHTML.indexOf('Echo'));
assert(tbody.innerHTML.indexOf('Echo')<tbody.innerHTML.indexOf('Alpha'));
'''
    result=subprocess.run(['node','-e',script,str(ROOT/'templates/analytics.html')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
