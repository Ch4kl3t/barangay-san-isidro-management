"""Household-head presentation and native-dialog behavior; fictional store only."""
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess

import pytest

from tests.test_defense_refinement import designate,role_store

ROOT=Path(__file__).resolve().parents[1]


def test_current_summary_uses_saved_full_name_and_preserves_surrounding_actions(client,csrf,role_store):
    role_store.members[1].update(firstname='Fictional',middlename='Middle',surname='Saved Name')
    designate(client,csrf,role_store)
    html=client.get('/view_household/1').text
    assert '<h3 class="head-card-name">Fictional Middle Saved Name</h3>' in html
    for label in ['Household Head','Resident #1','Designated Head','Change Head','View designation history',
                  'Add Member','Print / Download','Edit Household','View Details']:
        assert label in html
    assert html.index('info-grid')<html.index('id="householdHeadCard"')<html.index('<tbody')
    assert 'PRIVATE HEALTH SENTINEL' not in html
    assert 'css/household-head.css' in html.split('</head>')[0]


def test_empty_state_and_eligible_options_are_compact_and_explicit(client,role_store):
    html=client.get('/view_household/1').text
    assert 'No household head designated' in html
    assert 'Select an eligible resident to designate as the household head.' in html
    assert 'Designate Household Head' in html and not role_store.heads
    options=html.split('id="headResident"',1)[1].split('</select>',1)[0]
    assert 'value="1"' in options and 'value="2"' in options
    assert 'value="3"' not in options and 'value="4"' not in options
    assert 'name="head_assignment" value="none"' in html
    assert 'name="csrf_token"' in html and 'method="post"' in html


@pytest.mark.parametrize('operation',['designate','reassign','clear'])
def test_success_has_one_inline_notification_and_preserves_decisions(client,csrf,role_store,operation):
    if operation!='designate':
        designate(client,csrf,role_store);client.get('/view_household/1')
    result=designate(client,csrf,role_store,'2' if operation=='reassign' else '' if operation=='clear' else '1',
                     '1' if operation!='designate' else 'none','Fictional explicit decision')
    assert result.status_code==302
    html=client.get(result.location).text
    message='Household-head designation cleared.' if operation=='clear' else 'Household-head designation saved. Review relationships for this head.'
    assert html.count(message)==1 and html.count('data-feedback-inline')==1
    assert 'office-feedback success' in html and 'role="status"' in html
    assert role_store.audits[-1][-1]=='SUCCESS'
    if operation=='clear':assert role_store.active(1) is None and role_store.heads[0]['ended_at']
    elif operation=='reassign':assert role_store.active(1)['resident_id']==2 and len(role_store.heads)==2
    else:assert role_store.active(1)['resident_id']==1


def test_validation_error_is_visible_once_and_does_not_change_head(client,csrf,role_store):
    designate(client,csrf,role_store)
    client.get('/view_household/1')
    designate(client,csrf,role_store,'4','1','Foreign member test')
    html=client.get('/view_household/1').text
    assert html.count('Choose a resident from this household')==1
    assert 'office-feedback error' in html and 'data-feedback-inline' in html and 'role="alert"' in html
    assert role_store.active(1)['resident_id']==1 and len(role_store.heads)==1
    assert role_store.audits[-1][-1]=='FAILED'


def test_missing_history_name_date_and_relationships_are_preserved_without_guessing(client,csrf,role_store):
    designate(client,csrf,role_store)
    role_store.relations[(1,2)]='Sibling'
    role_store.heads[0]['assigned_at']=datetime(2026,11,5,1,30)
    designate(client,csrf,role_store,'2','1','Fictional reassignment')
    html=client.get('/view_household/1').text
    assert 'Fictional 1 Different surname 1' in html
    assert 'Nov 05, 2026 09:30:00 AM PHT' in html and 'Sibling' in html
    role_store.heads[0].update(resident_id=None,assigned_at=None)
    html=client.get('/view_household/1').text
    history=html.split('id="headHistory"',1)[1]
    assert 'Resident name unavailable' in history and 'Resident #1' in history and 'Designated Not recorded' in history
    assert 'Fictional reassignment' in history and 'Previous designation' in history and 'Sibling' in history
    assert role_store.relations[(1,2)]=='Sibling'


def test_history_reason_is_escaped_and_no_extra_record_mutation_is_introduced(client,csrf,role_store):
    designate(client,csrf,role_store,reason='<script>fictional & reason</script>')
    role_store.executed=[]
    html=client.get('/view_household/1').text
    assert '&lt;script&gt;fictional &amp; reason&lt;/script&gt;' in html
    assert '<script>fictional & reason</script>' not in html
    assert not any(re.match(r'\s*(UPDATE|INSERT|DELETE|ALTER|CREATE)',query) for query,_ in role_store.executed)


def test_unrelated_feedback_retains_existing_behavior(client,role_store):
    with client.session_transaction() as session:session['_flashes']=[('success','Fictional profile saved'),('danger','Fictional unrelated error')]
    html=client.get('/view_household/1').text
    assert html.count('Fictional profile saved')==html.count('Fictional unrelated error')==1
    assert 'data-feedback-inline' not in html


def test_commit_failure_cannot_publish_head_success(client,csrf,role_store):
    role_store.fail_commit=True
    assert designate(client,csrf,role_store).status_code==500
    with client.session_transaction() as session:
        assert not any(category=='household_head_success' for category,_ in session.get('_flashes',[]))
    assert not role_store.heads


@pytest.mark.parametrize('existing,clear',[(False,False),(True,False),(True,True)])
def test_native_dialog_requires_review_before_single_submission_and_restores_focus(existing,clear):
    script=(ROOT/'static/js/household-head.js').read_text(encoding='utf-8')
    harness=r'''
const vm=require('vm'),assert=require('assert'),script=process.argv[1];let focused=null,submissions=0,created=[];
class Node {constructor(name){this.name=name;this.hidden=false;this.disabled=false;this.listeners={};this.nodes={};this.textContent='';this.dataset={};}append(...nodes){}setAttribute(k,v){this[k]=v}addEventListener(k,fn){this.listeners[k]=fn}querySelector(k){return this.nodes[k]}querySelectorAll(k){return this.nodes[k]||[]}focus(){focused=this}set innerHTML(v){throw Error('HTML injection prohibited')}showModal(){this.open=true}close(){this.open=false;this.listeners.close?.()}}
const existing=JSON.parse(process.argv[2]),clear=JSON.parse(process.argv[3]);
const card=new Node('card'),fallback=new Node('fallback'),content=new Node('content'),form=new Node('form'),actions=new Node('actions'),title=new Node('title'),description=new Node('description'),edit=new Node('edit'),review=new Node('review'),back=new Node('back'),confirm=new Node('confirm'),cancel=new Node('cancel'),button=new Node('reviewButton'),launchText=new Node('launchText');
title.textContent=existing?'Change Household Head':'Designate Household Head';description.textContent='Select an active member.';launchText.textContent=existing?'Change Head':'Designate Household Head';
const resident=new Node('resident');resident.value=clear?'':'2';resident.selectedOptions=[{dataset:{residentName:'Fictional Selected Name'},textContent:'Fallback'}];
const reason={value:'Fictional <reason> & decision'};form.dataset={headExisting:existing?'yes':'no',headHousehold:'Fictional Household'};form.elements={namedItem:key=>key==='head_resident_id'?resident:reason};form.valid=true;form.reportValidity=()=>form.valid;
form.nodes['[data-head-review-button]']=button;form.requestSubmit=()=>{const event={defaultPrevented:false,preventDefault(){this.defaultPrevented=true}};form.listeners.submit(event);if(!event.defaultPrevented)submissions++};
Object.assign(card.nodes,{'#headAssignment':fallback,'[data-head-editor]':content,'[data-head-form]':form,'[data-head-actions]':actions});fallback.nodes['[data-head-launch]']=launchText;
Object.assign(content.nodes,{'[data-head-edit-view]':edit,'[data-head-review]':review,'#headDialogTitle':title,'#headDialogDescription':description,'[data-head-confirm]':confirm,'[data-head-back]':back,'[data-head-cancel]':[cancel],'[data-review-explanation]':new Node('explanation')});
for(const key of ['household','name','id','reason'])content.nodes['[data-review-'+key+']']=new Node(key);
const document={getElementById:()=>card,createElement(tag){const node=new Node(tag);created.push(node);return node},body:{append(){}}},events={},window={addEventListener(type,fn){events[type]=fn}};
vm.runInNewContext(script,{document,window,HTMLDialogElement:Node});
const launch=created.find(n=>n.name==='button'),box=created.find(n=>n.name==='dialog');assert(fallback.hidden);
launch.onclick();assert(box.open);assert.equal(focused,resident);form.valid=false;form.requestSubmit();assert.equal(submissions,0);assert(!edit.hidden);
form.valid=true;form.requestSubmit();assert.equal(submissions,0);assert(review.hidden===false);
assert.equal(content.nodes['[data-review-reason]'].textContent,reason.value);assert.equal(content.nodes['[data-review-household]'].textContent,'Fictional Household');
assert.equal(content.nodes['[data-review-name]'].textContent,clear?'No designated head':'Fictional Selected Name');assert.equal(content.nodes['[data-review-id]'].textContent,clear?'None':'2');
assert(title.textContent.includes(clear?'Clearing':existing?'Reassignment':'Designation'));assert.equal(focused,back);
cancel.onclick();assert(!box.open);assert.equal(focused,launch);assert.equal(submissions,0);
launch.onclick();form.requestSubmit();reason.value+=' changed';confirm.onclick();assert.equal(submissions,0);assert(!edit.hidden);
form.requestSubmit();back.onclick();assert.equal(focused,resident);form.requestSubmit();confirm.onclick();confirm.onclick();assert.equal(submissions,1);assert(confirm.disabled);
events.pageshow({persisted:true});assert(!confirm.disabled);assert(!box.open);assert.equal(focused,launch);
'''
    result=subprocess.run(['node','-e',harness,script,json.dumps(existing),json.dumps(clear)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('inline',[True,False])
def test_shared_feedback_opens_no_second_dialog_for_head_feedback(inline):
    script=(ROOT/'static/js/defense-refinement.js').read_text(encoding='utf-8')
    harness=r'''
const vm=require('vm'),assert=require('assert'),inline=JSON.parse(process.argv[2]);let opens=0;const handlers={},created=[];
const feedback={classList:{contains:()=>false},querySelector:()=>({textContent:'Fictional saved message'})};
const node=tag=>({tag,textContent:'',append(){},setAttribute(){},addEventListener(){},showModal(){opens++},focus(){},set innerHTML(v){throw Error('HTML injection prohibited')}});
const document={activeElement:node('opener'),querySelector:()=>null,getElementById:()=>null,querySelectorAll(selector){
 if(selector.startsWith('.office-feedback-region'))return inline&&selector.includes(':not([data-feedback-inline])')?[]:[feedback];return [];
},createElement(tag){const element=node(tag);created.push(element);return element},body:{append(){}},addEventListener(type,fn){handlers[type]=fn}};
const window={fetch:async()=>({status:200})};vm.runInNewContext(process.argv[1],{document,window,URL,location:{href:'https://example.invalid/view_household/1'}});
assert.equal(opens,inline?0:1);
handlers.submit({target:{matches:()=>true}});assert.equal(opens,inline?0:1);
if(inline){
 const fields={designate_head:{checked:true},household_id:{value:'1'},firstname:{value:'Fictional'},middlename:{value:'Middle'},surname:{value:'Resident'},head_reason:{value:'Fictional <reason>'}};
 handlers.submit({target:{matches:()=>false,dataset:{},elements:{namedItem:key=>fields[key]},checkValidity:()=>true,action:'/add_member'},preventDefault(){},stopImmediatePropagation(){}});
 assert(created.some(el=>el.textContent==='Confirm Household Head Designation'));assert(created.some(el=>el.textContent==='Confirm Designation'));assert(created.some(el=>el.textContent.includes('Fictional Middle Resident')&&el.textContent.includes('Fictional <reason>')));
}
'''
    result=subprocess.run(['node','-e',harness,script,json.dumps(inline)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
