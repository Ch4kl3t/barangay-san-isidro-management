"""Focused release regressions; synthetic rows, mocked connections and Node only."""
from contextlib import contextmanager
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

import pytest

from tests.test_defense_refinement import role_store

ROOT=Path(__file__).resolve().parents[1]


class DashboardStore:
    def __init__(self,empty=False):
        self.executed=[];self.rows=[];self.empty=empty
        self.residents=[dict(id=i,firstname='Fictional',surname='Resident',gender='Female',status='Active',
                            household_id=1,registration_date=None,birthdate=None,death_date=None) for i in range(1,126)] if not empty else []
        self.homes=[dict(id=i,surname='Fictional',house_number=str(i),address='Fictional address',
                        member_count=4,active_count=4,deceased_count=0,male_members=0,female_members=4,
                        registration_date=None) for i in range(1,31)] if not empty else []
    def execute(self,query,params=()):
        self.executed.append((query,params));self.rows=[]
        if query.startswith('SELECT COUNT(*) AS total,COUNT(*) FILTER'):
            n=len(self.residents);self.rows=[dict(total=n,male=0,female=n,deceased=0)]
        elif query.startswith('SELECT EXTRACT'):
            self.rows=[] if 'FROM death_date' in query or self.empty else [dict(month=1,total=125,male=0,female=125)]
        elif query.startswith('SELECT * FROM ') and 'ORDER BY surname,firstname,id LIMIT' in query:
            self.rows=self.residents[params[-1]:params[-1]+params[-2]]
        elif query.startswith('SELECT id,surname,house_number,address,member_count'):
            self.rows=[dict(h) for h in self.homes]
        elif query.startswith('SELECT * FROM '):
            homes=self.homes
            if ' WHERE member_count=%s' in query:homes=[h for h in homes if h['member_count']==params[-3]]
            self.rows=[dict(h) for h in homes[params[-1]:params[-1]+params[-2]]]
        elif query.startswith('SELECT id,old_value'):
            self.rows=[dict(id=i,old_value=json.dumps(dict(id=i,firstname='Fictional',surname='Removed',gender='Female',status='Active',household_id=1)),created_at=datetime(2026,1,1),household_context='1') for i in range(1,26)]
    def fetchone(self):return self.rows[0] if self.rows else None
    def fetchall(self):return self.rows


@pytest.fixture
def dashboard(monkeypatch):
    store=DashboardStore()
    @contextmanager
    def transaction():yield store
    monkeypatch.setattr('dashboard_routes.transaction',transaction)
    return store


@pytest.mark.parametrize('resident_page,household_page',[(1,1),(2,1),(2,3),(13,2)])
def test_analytics_pages_are_independent_and_totals_are_not_sliced(client,dashboard,resident_page,household_page):
    data=client.get(f'/api/dashboard?gender=Female&status=Active&residents_page={resident_page}&households_page={household_page}').json
    assert data['stats']['total']==125 and data['stats']['female']==125
    assert data['monthData']['datasets'][0]['data'][0]==125
    assert len(data['household_summary'])==30 and sum(h['members'] for h in data['household_summary'])==120
    assert len(data['residents'])<=10 and len(data['households'])==10
    assert data['residents'][0]['id']==(resident_page-1)*10+1
    assert data['households'][0]['id']==(household_page-1)*10+1
    assert data['pagination']['residents']==dict(page=resident_page,pages=13,total=125,page_size=10)
    assert data['pagination']['households']==dict(page=household_page,pages=3,total=30,page_size=10)
    queries=[(q,p) for q,p in dashboard.executed if ' LIMIT %s OFFSET %s' in q]
    assert len(queries)==2 and all(p[-2]==10 for q,p in queries)
    assert 'gender=%s' in queries[0][0] and 'status=%s' in queries[0][0]
    assert queries[0][1][:2]==['Female','Active']


@pytest.mark.parametrize('value,expected',[('bad',1),('-4',1),('0',1),('1.5',1),('999999',13)])
def test_invalid_or_out_of_range_analytics_page_is_clamped(client,dashboard,value,expected):
    data=client.get('/api/dashboard?residents_page='+value+'&households_page=bad').json
    assert data['pagination']['residents']['page']==expected
    assert data['pagination']['households']['page']==1


def test_empty_tables_report_page_one_without_negative_offsets(client,dashboard):
    dashboard.residents=[];dashboard.homes=[];dashboard.empty=True
    data=client.get('/api/dashboard?residents_page=999&households_page=-1').json
    assert data['residents']==data['households']==[]
    assert all(p==dict(page=1,pages=1,total=0,page_size=10) for p in data['pagination'].values())


def test_household_comparison_and_deleted_residents_stay_paginated(client,dashboard):
    single=client.get('/api/dashboard?household_group=single').json
    assert single['households']==[] and single['pagination']['households']['total']==0
    assert len(single['household_summary'])==30
    deleted=client.get('/api/dashboard?activity=deleted&residents_page=3').json
    assert deleted['stats']['total']==25 and len(deleted['residents'])==5
    assert deleted['residents'][0]['id']==21


@pytest.mark.parametrize('query',['household_metric=unsafe','household_group=unsafe'])
def test_untrusted_comparison_never_becomes_sql(client,dashboard,query):
    assert client.get('/api/dashboard?'+query).status_code==400
    assert all('unsafe' not in q for q,p in dashboard.executed)


@pytest.mark.parametrize('query',[dict(search='Fictional',gender='Female',status='Active'),dict(search='Example',empty='nonempty')])
def test_compact_directory_filters_share_safe_queries_and_reset(client,monkeypatch,role_store,query):
    from reporting import report_query
    kind='residents' if 'gender' in query else 'households'
    sql,params,*_=report_query(kind,query)
    assert query['search'] not in sql and params
    if kind=='residents':assert 'gender=%s' in sql and 'status=%s' in sql
    else:assert 'member_count>0' in sql
    monkeypatch.setattr('directory_routes.rows_for',lambda *a,**k:([],0,'Synthetic scope'))
    path='/view_members' if kind=='residents' else '/view_households'
    html=client.get(path,query_string=query).text
    assert 'compact-directory-toolbar' in html and '>Search</button>' in html and '>Clear</a>' in html
    assert 'directory-filter-grid' not in html
    for key in ['age_min','age_max','civil_status']:assert f'name="{key}"' not in html
    assert 'value="'+query['search']+'"' in html


class Scripts(HTMLParser):
    def __init__(self):super().__init__();self.blocks=[];self.current=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='script' and not attrs.get('src') and attrs.get('type')!='application/json':self.current=[]
    def handle_data(self,data):
        if self.current is not None:self.current.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.current is not None:self.blocks.append(''.join(self.current));self.current=None


@pytest.mark.parametrize('path',['/view_members','/view_households','/analytics','/view_household/1','/login'])
def test_initial_background_and_styles_precede_body_and_scripts_parse(client,monkeypatch,role_store,tmp_path,path):
    monkeypatch.setattr('directory_routes.rows_for',lambda *a,**k:([],0,'Synthetic'))
    response=client.get(path);assert response.status_code==200
    html=response.text;head=html.split('</head>')[0]
    assert 'id="early-paint"' in head and '#0c1522' in head
    assert html.index('id="early-paint"')<html.index('js/appearance.js')
    assert 'visibility:hidden' not in head and 'opacity:0' not in head
    if path!='/login':assert 'css/appearance.css' in head and 'css/defense-refinement.css' in head
    parser=Scripts();parser.feed(html)
    code='\n'.join('{'+block+'}' for block in parser.blocks)
    script=tmp_path/'rendered-page.js';script.write_text(code,encoding='utf-8')
    check=subprocess.run(['node','--check',str(script)],text=True,capture_output=True,timeout=10)
    assert check.returncode==0,check.stderr


def test_real_pagination_script_preserves_other_page_filters_and_browser_history():
    script=(ROOT/'static/js/analytics-pagination.js').read_text(encoding='utf-8')
    harness=r'''
const vm=require('vm'),assert=require('assert');let href='https://example.invalid/analytics?filterGender=Female';
const nodes={};for(const key of ['residents','households']){
 const buttons=[-1,1].map(direction=>({dataset:{direction:String(direction)},disabled:false}));
 nodes[key+'Pagination']={buttons,status:{textContent:''},querySelector(s){return s==='[role=status]'?this.status:buttons[s.includes('"-1"')?0:1]},addEventListener(t,fn){this.click=fn}};
}
let loads=0;const history=[];
const context={URL,URLSearchParams,Number,Object,document:{getElementById:id=>nodes[id]||(id==='filterGender'?{value:'Female'}:{value:''}),querySelectorAll:()=>[]},
 location:{get href(){return href},get search(){return new URL(href).search}},history:{pushState(a,b,url){href=String(url);history.push('push')},replaceState(a,b,url){href=String(url);history.push('replace')}},loadDashboard(){loads++}};
vm.createContext(context);vm.runInContext("let activeHHTab='members',householdCard='total';"+JSON.parse(process.argv[1])+";globalThis.pages=analyticsPages;",context);
context.installAnalyticsPages();context.updateAnalyticsPages({residents:{page:1,pages:13,total:125},households:{page:1,pages:3,total:30}});
assert(nodes.residentsPagination.buttons[0].disabled);assert(nodes.residentsPagination.status.textContent.includes('125 matching'));
for(const key of ['residents','households']){const button=nodes[key+'Pagination'].buttons[1];nodes[key+'Pagination'].click({target:{closest:()=>button}})}
assert.equal(context.pages.residents,2);assert.equal(context.pages.households,2);assert.equal(loads,2);
assert.equal(new URL(href).searchParams.get('filterGender'),'Female');assert.equal(new URL(href).searchParams.get('residents_page'),'2');
href='https://example.invalid/analytics?residents_page=3&households_page=bad&filterGender=Female';context.restoreAnalyticsPages();
assert.equal(context.pages.residents,3);assert.equal(context.pages.households,1);
context.updateAnalyticsPages({residents:{page:1,pages:1,total:0},households:{page:1,pages:1,total:0}});
assert(nodes.residentsPagination.buttons[1].disabled);assert.equal(history.at(-1),'replace');
'''
    result=subprocess.run(['node','-e',harness,json.dumps(script)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_directory_search_applies_current_combined_controls_and_skips_noop_navigation():
    source=(ROOT/'static/js/directory-report-links.js').read_text(encoding='utf-8')
    apply=source[source.index(' const apply=()=>{'):source.index(" input.addEventListener('input'",source.index(' const apply=()=>{'))]
    harness=r'''
const vm=require('vm'),assert=require('assert');let href='https://example.invalid/view_members?page=4&gender=Male',moves=0;
const input={value:'Fictional',id:'member-search',selectionStart:2,selectionEnd:2,setAttribute(){}},target={value:''};
const state={URL,FormData:function(){return [['search','Fictional'],['gender','Female'],['status','Deceased'],['page_size','50']]},
 clearTimeout(){},timer:0,composing:false,key:'resident_id',form:{},target,input,status:{},invalidate(){},printPending(){},sessionStorage:{setItem(){}},Date,
 location:{get href(){return href},pathname:'/view_members',assign(path){href=new URL(path,href).href;moves++}}};
vm.createContext(state);vm.runInContext(JSON.parse(process.argv[1])+';globalThis.applySearch=apply;',state);
state.applySearch();let params=new URL(href).searchParams;
assert.equal(params.get('gender'),'Female');assert.equal(params.get('status'),'Deceased');assert.equal(params.get('search'),'Fictional');assert(!params.has('page'));
state.applySearch();assert.equal(moves,1);
target.value='17';state.applySearch();params=new URL(href).searchParams;assert.equal(params.get('resident_id'),'17');assert(!params.has('search'));assert.equal(params.get('gender'),'Female');
'''
    result=subprocess.run(['node','-e',harness,json.dumps(apply)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


class Toolbar(HTMLParser):
    def __init__(self):super().__init__();self.labels=[];self.selects={};self.inputs=[];self.links=[];self.buttons=[];self.selected=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='label':self.labels.append(attrs)
        elif tag=='input':self.inputs.append(attrs)
        elif tag=='a':self.links.append(attrs)
        elif tag=='button':self.buttons.append(attrs)
        elif tag=='select':self.selected=attrs['name'];self.selects[self.selected]=[]
        elif tag=='option' and self.selected:self.selects[self.selected].append(attrs)
    def handle_endtag(self,tag):
        if tag=='select':self.selected=None


@pytest.mark.parametrize('path,resident',[('/view_members',True),('/view_households',False)])
def test_directory_toolbar_exposes_only_intended_labeled_controls(client,monkeypatch,role_store,path,resident):
    monkeypatch.setattr('directory_routes.rows_for',lambda *a,**k:([],0,'Synthetic'))
    html=client.get(path).text
    toolbar=html.split('class="compact-directory-toolbar"',1)[1].split('</form>',1)[0]
    parser=Toolbar();parser.feed(toolbar)
    assert len([field for field in parser.inputs if field.get('type')=='search'])==1
    assert parser.buttons==[dict(type='submit')]
    assert len(parser.links)==1
    assert parser.links[0]['href']==path and parser.links[0]['class']=='directory-clear'
    assert 'directory-search-label' in toolbar and 'sr-only' not in toolbar
    if resident:
        assert {label['for'] for label in parser.labels}=={'member-search','directoryGender','directoryStatus'}
        assert {key:[option['value'] for option in options] for key,options in parser.selects.items()}==dict(gender=['','Male','Female'],status=['','Active','Deceased'])
    else:
        assert not parser.selects and {label['for'] for label in parser.labels}=={'searchBox'}
        assert 'householdMembershipFilter' not in html
        assert not any(field.get('name')=='empty' for field in parser.inputs)


def test_hidden_head_controls_and_intended_locations_remain_unchanged(client,csrf,role_store):
    role_store.enabled=False
    assert 'id="headAssignment"' not in client.get('/view_household/1').text
    assert 'id="householdRoles"' not in client.get('/add_member?household_id=1').text
    assert client.post('/households/1/head',data={'head_resident_id':'1','head_reason':'Synthetic test'},headers=csrf).status_code==409
    role_store.enabled=True
    assert 'id="headAssignment"' in client.get('/view_household/1').text
    assert 'id="householdRoles"' in client.get('/add_member?household_id=1').text
    assert 'id="householdRoles"' in client.get('/edit_member/1').text
